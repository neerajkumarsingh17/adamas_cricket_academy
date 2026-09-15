from typing import cast

from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.response import Response

from apps.admissions.admission.models import Admission
from apps.admissions.student.models import Student
from apps.core.models import DocumentType
from apps.core.views import ModuleScopedViewSet
from apps.iam.models import User
from apps.people.models import Person, Staff, StudentGuardian

from . import services
from .filters import DocumentFilter
from .models import Document
from .serializers import (
    ConfirmRequestSerializer,
    DocumentSerializer,
    DownloadUrlSerializer,
    PresignRequestSerializer,
    PresignResponseSerializer,
    RejectDocumentSerializer,
)


class DocumentViewSet(ModuleScopedViewSet):
    """docs/02-api-spec.md's Documents section has no plain `POST
    /documents` — creation only ever happens through `/presign` +
    `/confirm` (docs/07-storage.md: files never pass through the API
    server), so `create` is disabled here too.
    """

    module = "documents"
    serializer_class = DocumentSerializer
    queryset = Document.objects.select_related(
        "document_type", "verified_by", "owner_content_type"
    ).prefetch_related(
        # DocumentSerializer.get_owner_label/get_admission_id read
        # `obj.owner` (a GenericForeignKey, which select_related can't
        # touch) and, for every owner type but Person, `.person` off of
        # it too — GenericPrefetch resolves both in one batched query per
        # possible owner model instead of two queries per row. `intake` is
        # included for Admission so the pre-approval (person=None)
        # fallback in get_owner_label doesn't add a query per row either.
        GenericPrefetch(
            "owner",
            [
                Person.objects.all(),
                Staff.objects.select_related("person"),
                Student.objects.select_related("person"),
                Admission.objects.select_related("person", "intake"),
            ],
        )
    ).all()
    filterset_class = DocumentFilter
    http_method_names = ["get", "post", "patch", "head", "options"]

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def filter_to_own(self, queryset):
        """docs/03-rbac.md: `documents` grants `student` a plain `O` and
        `parent` an `OA` — a parent additionally uploads (`confirm_upload`
        checks the same ownership, see below) but both only ever *see*
        documents belonging to themselves or their own children.
        """
        from django.contrib.contenttypes.models import ContentType

        from apps.admissions.student.models import Student
        from apps.people.models import Person

        user = cast(User, self.request.user)
        if user.person_id is None:
            return queryset.none()

        own_student_ids = set(
            Student.objects.filter(person=user.person).values_list("id", flat=True)
        )
        own_student_ids |= set(
            StudentGuardian.objects.filter(guardian__person=user.person).values_list(
                "student_id", flat=True
            )
        )

        return queryset.filter(
            Q(
                owner_content_type=ContentType.objects.get_for_model(Person),
                owner_object_id=user.person_id,
            )
            | Q(
                owner_content_type=ContentType.objects.get_for_model(Student),
                owner_object_id__in=own_student_ids,
            )
        )

    @action(detail=False, methods=["post"], verb="add")
    def presign(self, request):
        serializer = PresignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _check_owner_scope(
            request, serializer.validated_data["owner_type"], serializer.validated_data["owner_id"]
        )
        document_type = _get_document_type(serializer.validated_data["document_type"])
        result = services.presign_upload(
            document_type=document_type,
            owner_type=serializer.validated_data["owner_type"],
            owner_id=serializer.validated_data["owner_id"],
            filename=serializer.validated_data["filename"],
            mime_type=serializer.validated_data["mime"],
        )
        return Response(
            PresignResponseSerializer(
                {"upload_url": result["upload_url"], "s3_key": result["s3_key"]}
            ).data
        )

    @action(detail=False, methods=["post"], verb="add")
    def confirm(self, request):
        serializer = ConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _check_owner_scope(
            request, serializer.validated_data["owner_type"], serializer.validated_data["owner_id"]
        )
        document_type = _get_document_type(serializer.validated_data["document_type"])
        document = services.confirm_upload(
            document_type=document_type,
            owner_type=serializer.validated_data["owner_type"],
            owner_id=serializer.validated_data["owner_id"],
            s3_key=serializer.validated_data["s3_key"],
            original_filename=serializer.validated_data["filename"],
            mime_type=serializer.validated_data["mime"],
        )
        return Response(DocumentSerializer(document).data, status=201)

    @action(detail=True, methods=["patch"], verb="approve")
    def verify(self, request, pk=None):
        document = self.get_object()
        services.verify(document, verified_by=request.user, user=request.user)
        return Response(DocumentSerializer(document).data)

    @action(detail=True, methods=["patch"], verb="approve")
    def reject(self, request, pk=None):
        document = self.get_object()
        serializer = RejectDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reject(
            document, reason=serializer.validated_data["rejection_reason"], user=request.user
        )
        return Response(DocumentSerializer(document).data)

    @action(detail=True, methods=["get"], verb="view")
    def download(self, request, pk=None):
        """docs/07-storage.md: "Generate it on demand, in the detail
        endpoint, after the permission check, with a 5-minute expiry" and
        "Never store a presigned URL in the database or return one in a
        list endpoint" — this is exactly, and only, that one place.
        """
        document = self.get_object()
        url = services._presigned_get_url(document.s3_key)
        return Response(DownloadUrlSerializer({"download_url": url}).data)


def _get_document_type(pk) -> DocumentType:
    from django.shortcuts import get_object_or_404

    return get_object_or_404(DocumentType, pk=pk)


def _check_owner_scope(request, owner_type: str, owner_id) -> None:
    """docs/03-rbac.md rule 3 ("own" is enforced at the queryset level
    *and* checked per object) applies just as much to a write as a read —
    `presign`/`confirm` accept an arbitrary `owner_id` in the body, and
    without this a parent or student holding `documents:add` (scope=own)
    could attach a document to any Person/Student in the system, not only
    their own. `ModuleScopedViewSet.get_queryset()`'s scope filtering only
    covers list/retrieve, not custom actions with a client-supplied id —
    this is the per-object check those need instead.

    Raises PermissionDenied (403) rather than 404 here: unlike reading
    another child's record (which must not even confirm it exists), a
    write attempt telling the client "you may not do this" leaks nothing
    docs/03-rbac.md asks to hide.
    """
    user = request.user
    if user.scope_for("documents", "add") != "all":
        from apps.admissions.student.models import Student
        from apps.people.models import StudentGuardian

        if user.person_id is None:
            raise PermissionDenied("You do not have a linked profile.")

        # Direct-admission step 2.1: the candidate uploads to their own
        # in-progress `Admission` (no `Student` row yet) once Administration
        # has enabled portal access — checked against `Admission.person`
        # directly rather than folded into `allowed_ids` below, since an
        # admission id isn't a person/student id and a false-positive
        # string match across the two id spaces would be a real hole.
        if owner_type == "admission":
            if not Admission.objects.filter(pk=owner_id, person_id=user.person_id).exists():
                raise PermissionDenied(
                    "You may only upload documents for your own admission."
                )
            return

        allowed_ids = {str(user.person_id)}
        allowed_ids |= {
            str(sid)
            for sid in Student.objects.filter(person=user.person).values_list("id", flat=True)
        }
        allowed_ids |= {
            str(sid)
            for sid in StudentGuardian.objects.filter(guardian__person=user.person).values_list(
                "student_id", flat=True
            )
        }
        if owner_type not in ("person", "student") or str(owner_id) not in allowed_ids:
            raise PermissionDenied(
                "You may only upload documents for yourself or your own children."
            )
