from typing import cast

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admissions.admission.models import Admission
from apps.core.models import Programme
from apps.core.views import ModuleScopedViewSet
from apps.iam.models import User
from apps.people.models import Person, StudentGuardian

from . import services
from .filters import StudentFilter
from .models import Student
from .serializers import (
    ApproveAdmissionResponseSerializer,
    ChangeStatusSerializer,
    GrantLoginSerializer,
    LinkGuardianSerializer,
    ReAdmissionSerializer,
    StudentGuardianSerializer,
    StudentProfileSerializer,
    StudentProfileWriteSerializer,
    StudentSerializer,
    StudentStatusHistorySerializer,
    StudentWriteSerializer,
)


class StudentViewSet(ModuleScopedViewSet):
    module = "students"
    queryset = Student.objects.select_related("person", "programme", "admission").all()
    filterset_class = StudentFilter
    # "delete" is for the guardians_detail action's unlink call only — the
    # detail route's own destroy() below unconditionally refuses DELETE
    # regardless of this list, so a student itself still can't be deleted.
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return StudentWriteSerializer
        return StudentSerializer

    def filter_to_own(self, queryset):
        """docs/03-rbac.md rule 3: a parent sees their children, a student
        sees themself — both "own" scope holders on this module. `person`
        is nullable on `User` (e.g. the IT admin account), so a user with
        no linked Person simply has no "own" rows, not an error.
        """
        # ModuleScopedViewSet requires IsAuthenticated, so this is always a
        # real User by the time a view body runs — AnonymousUser is DRF's
        # stub type for the pre-authentication window only.
        user = cast(User, self.request.user)
        if user.person_id is None:
            return queryset.none()
        guardian_student_ids = StudentGuardian.objects.filter(
            guardian__person=user.person
        ).values_list("student_id", flat=True)
        return queryset.filter(Q(person=user.person) | Q(id__in=guardian_student_ids))

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def retrieve(self, request, *args, **kwargs):
        student = self.get_object()
        return Response(services.composite_profile(student))

    @action(detail=True, methods=["post"], verb="edit")
    def status(self, request, pk=None):
        student = self.get_object()
        serializer = ChangeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.change_status(
            student,
            to_status=serializer.validated_data["to_status"],
            reason=serializer.validated_data["reason"],
            user=request.user,
        )
        if result["pending_approval"]:
            return Response(
                {
                    "status": "approval_pending",
                    "approval_request_id": result["approval_request_id"],
                },
                status=202,
            )
        return Response(StudentSerializer(result["student"]).data)

    @action(detail=True, methods=["get"], url_path="status-history", verb="view")
    def status_history(self, request, pk=None):
        student = self.get_object()
        return Response(
            StudentStatusHistorySerializer(
                student.status_history.select_related("changed_by").order_by("-changed_at"),
                many=True,
            ).data
        )

    @action(detail=True, methods=["get", "post"], url_path="guardians", verb="edit")
    def guardians(self, request, pk=None):
        """The management counterpart to composite_profile()'s read-only
        "parent" tab — that block has always existed, but there was never
        an API-reachable way to create a StudentGuardian row, only Django
        admin. Both GET and POST are gated on `students:edit`: a parent or
        student already gets their own guardians through the composite
        profile's own read-only block (scope="own" on `students:view`),
        so this is purely the administration-facing write surface.
        """
        student = self.get_object()
        if request.method == "GET":
            guardian_rows = StudentGuardian.objects.filter(student=student).select_related(
                "guardian__person"
            )
            data = [
                {
                    "id": sg.id,
                    "guardian_id": sg.guardian_id,
                    "relationship": sg.relationship,
                    "is_primary": sg.is_primary,
                    "is_emergency_contact": sg.is_emergency_contact,
                    "person": sg.guardian.person,
                }
                for sg in guardian_rows
            ]
            return Response(StudentGuardianSerializer(data, many=True).data)

        serializer = LinkGuardianSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        new_person = None
        if "person_id" not in validated:
            new_person = {
                field: validated[field]
                for field in ("first_name", "last_name", "date_of_birth", "gender", "mobile")
            }
            new_person["email"] = validated.get("email", "")
        student_guardian = services.link_guardian(
            student,
            person_id=str(validated["person_id"]) if "person_id" in validated else None,
            new_person=new_person,
            relationship=validated["relationship"],
            is_primary=validated["is_primary"],
            is_emergency_contact=validated["is_emergency_contact"],
            grant_portal_access=validated["grant_portal_access"],
        )
        return Response(
            StudentGuardianSerializer(
                {
                    "id": student_guardian.id,
                    "guardian_id": student_guardian.guardian_id,
                    "relationship": student_guardian.relationship,
                    "is_primary": student_guardian.is_primary,
                    "is_emergency_contact": student_guardian.is_emergency_contact,
                    "person": student_guardian.guardian.person,
                }
            ).data,
            status=201,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"guardians/(?P<guardian_link_id>[^/.]+)",
        verb="edit",
    )
    def guardians_detail(self, request, pk=None, guardian_link_id=None):
        student = self.get_object()
        services.unlink_guardian(student, guardian_link_id)
        return Response(status=204)

    @action(detail=True, methods=["post"], url_path="login-access", verb="edit")
    def login_access(self, request, pk=None):
        """Deliberately not automatic at admission approval — see
        services.grant_student_login's docstring for the mobile-collision
        reason a distinct action exists at all.
        """
        student = self.get_object()
        serializer = GrantLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, created = services.grant_student_login(
            student, mobile=serializer.validated_data.get("mobile")
        )
        return Response({"user_id": user.id, "login_id": user.login_id, "created": created})

    @action(detail=False, methods=["post"], url_path="re-admission", verb="add")
    def re_admission(self, request):
        serializer = ReAdmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        person = get_object_or_404(Person, pk=serializer.validated_data["person"])
        programme = get_object_or_404(Programme, pk=serializer.validated_data["programme"])
        student = services.re_admit(
            person=person,
            programme=programme,
            requested_by=request.user,
            residential=serializer.validated_data["residential"],
        )
        return Response(StudentSerializer(student).data, status=201)

    @action(detail=False, methods=["get"], verb="export")
    def export(self, request):
        """GET /students/export — docs/02-api-spec.md: "Async. Audited
        with the filter and row count." The real async export-job pipeline
        is Phase 12's `reporting` app (docs/01-data-model.md section 4's
        `academics`... table lists `ExportJob` there, not in Phase 1) —
        this slice satisfies the one requirement Phase 1 needs from it:
        that an export write its own audit row.
        """
        from apps.audit.models import AuditAction, AuditLog

        queryset = self.filter_queryset(self.get_queryset())
        row_count = queryset.count()
        AuditLog.objects.create(
            actor=request.user,
            action=AuditAction.EXPORT,
            model_label="student.Student",
            object_id="bulk",
            changes={"filter": dict(request.query_params), "row_count": row_count},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            request_id=getattr(request, "request_id", ""),
        )
        return Response({"status": "queued", "row_count": row_count})


class AdmissionApproveView(APIView):
    """POST /admissions/{id}/approve — docs/02-api-spec.md lists this under
    "Admissions", but creating the `Student` it produces means the
    implementation has to live in `apps.admissions.student` (see
    services.py's module docstring on the dependency direction). Registered
    from this app's urls.py so the URL path still matches the spec exactly.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, admission_id):
        admission = get_object_or_404(Admission, pk=admission_id)
        # Trial-based admissions, and the fee-first direct-admission wizard
        # (has an AdmissionIntake), both need the real `approve` verb —
        # Academy Head sign-off (docs/03-rbac.md; Prompt C's spec for the
        # new chain). Only the pre-existing trial-waiver direct-admission
        # path (no intake, no trial_registration) keeps its original
        # bypass — Administration/Accounts, who already confirmed the fee
        # themselves, finish it with the `edit` verb they already hold
        # (product decision: the original direct-admission feature).
        is_old_style_direct = (
            admission.trial_registration_id is None and not hasattr(admission, "intake")
        )
        can_finalize = request.user.has_perm_for("admission", "approve") or (
            is_old_style_direct and request.user.has_perm_for("admission", "edit")
        )
        if not can_finalize:
            self.permission_denied(request)
        student = services.approve_admission(admission, user=request.user)
        return Response(ApproveAdmissionResponseSerializer({"student": student}).data, status=201)


class StudentProfileViewSet(ModuleScopedViewSet):
    """GET/PATCH /students/{id}/profile/ — the deferred half of the
    offline form (Prompt G), student/parent side. A distinct module from
    `students` on purpose: that module's own-scope grant is view-only
    (docs/03-rbac.md) — several of its `edit`-gated actions (status
    changes, guardian management, login access) are staff-only, and
    reusing that module's `edit` verb here would have handed students and
    parents access to all of those too, not just their own profile.
    """

    module = "student_profile"
    queryset = Student.objects.select_related("person", "profile").all()

    def get_serializer_class(self):
        if self.action == "profile_update":
            return StudentProfileWriteSerializer
        return StudentProfileSerializer

    def filter_to_own(self, queryset):
        # Same "self, or a child I guardian" scope as StudentViewSet's own
        # filter_to_own — duplicated rather than imported, since sharing a
        # bound method across two ModuleScopedViewSet subclasses with
        # different `module`s would blur which module a given request was
        # actually authorised under.
        user = cast(User, self.request.user)
        if user.person_id is None:
            return queryset.none()
        guardian_student_ids = StudentGuardian.objects.filter(
            guardian__person=user.person
        ).values_list("student_id", flat=True)
        return queryset.filter(Q(person=user.person) | Q(id__in=guardian_student_ids))

    @action(detail=True, methods=["get"], url_path="profile", verb="view")
    def profile(self, request, pk=None):
        student = self.get_object()
        profile = services.get_or_create_profile(student)
        return Response(StudentProfileSerializer(profile).data)

    @action(detail=True, methods=["patch"], url_path="profile", verb="edit")
    def profile_update(self, request, pk=None):
        student = self.get_object()
        serializer = StudentProfileWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        person_fields = {
            field: data.pop(field)
            for field in ("blood_group", "student_email")
            if field in data
        }
        if "student_email" in person_fields:
            person_fields["email"] = person_fields.pop("student_email")
        profile = services.update_profile(student, profile_fields=data, person_fields=person_fields)
        return Response(StudentProfileSerializer(profile).data)
