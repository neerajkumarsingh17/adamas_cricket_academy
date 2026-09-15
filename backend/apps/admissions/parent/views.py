from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admissions.document.services import confirm_upload
from apps.admissions.student.models import Student
from apps.admissions.student.serializers import StudentSerializer
from apps.admissions.student.services import composite_profile
from apps.core.models import DocumentType
from apps.people.models import Guardian, StudentGuardian

from .models import ParentPortalAccess
from .serializers import ParentDocumentUploadSerializer, ParentPortalAccessSerializer


def _own_children_queryset(user):
    if user.person_id is None:
        return Student.objects.none()
    child_ids = StudentGuardian.objects.filter(guardian__person=user.person).values_list(
        "student_id", flat=True
    )
    return Student.objects.filter(id__in=child_ids).select_related("person", "programme")


class ParentChildrenListView(APIView):
    """GET /parents/me/children — docs/02-api-spec.md."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm_for("students", "view"):
            self.permission_denied(request)
        children = _own_children_queryset(request.user)
        return Response(StudentSerializer(children, many=True).data)


class ParentChildDetailView(APIView):
    """GET /parents/me/children/{id} — docs/02-api-spec.md: "Read-only
    profile." Object-level authorisation via `_own_children_queryset`
    (docs/03-rbac.md rule 3): a parent naming another parent's child's id
    gets 404, not 403 — it's simply not in this queryset.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        if not request.user.has_perm_for("students", "view"):
            self.permission_denied(request)
        student = get_object_or_404(_own_children_queryset(request.user), pk=student_id)
        return Response(composite_profile(student))


class ParentDocumentUploadView(APIView):
    """POST /parents/me/documents — docs/02-api-spec.md: "Upload for their
    own child" (`documents/add`, scope own).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.has_perm_for("documents", "add"):
            self.permission_denied(request)
        serializer = ParentDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = get_object_or_404(
            _own_children_queryset(request.user), pk=serializer.validated_data["student"]
        )
        document_type = get_object_or_404(
            DocumentType, pk=serializer.validated_data["document_type"]
        )
        document = confirm_upload(
            document_type=document_type,
            owner_type="student",
            owner_id=student.id,
            s3_key=serializer.validated_data["s3_key"],
            original_filename=serializer.validated_data["filename"],
            mime_type=serializer.validated_data["mime"],
        )
        from apps.admissions.document.serializers import DocumentSerializer

        return Response(DocumentSerializer(document).data, status=201)


class ParentPortalSettingsView(APIView):
    """Not itself in docs/02-api-spec.md's endpoint table, but M05 Parent
    Management (docs/00-project-structure.md) *is* "portal access +
    contact preferences and notification settings" — `ParentPortalAccess`
    would otherwise have no API surface at all. GET creates the settings
    row on first access (defaults) rather than 404ing a parent who has
    never opened this screen before.
    """

    permission_classes = [IsAuthenticated]

    def _guardian(self, request) -> Guardian:
        return get_object_or_404(Guardian, person=request.user.person)

    def get(self, request):
        guardian = self._guardian(request)
        settings_row, _ = ParentPortalAccess.objects.get_or_create(guardian=guardian)
        return Response(ParentPortalAccessSerializer(settings_row).data)

    def patch(self, request):
        guardian = self._guardian(request)
        settings_row, _ = ParentPortalAccess.objects.get_or_create(guardian=guardian)
        serializer = ParentPortalAccessSerializer(settings_row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
