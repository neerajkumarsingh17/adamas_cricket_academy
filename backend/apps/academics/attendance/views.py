import datetime

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.response import Response

from apps.academics.batch.models import Batch, Coach, TrainingSession
from apps.academics.batch.serializers import TrainingSessionSerializer
from apps.core.models import TrainingType
from apps.core.views import ModuleScopedViewSet

from . import services
from .filters import AttendanceCorrectionFilter
from .models import Attendance, AttendanceCorrection
from .serializers import (
    AttendanceCorrectionSerializer,
    AttendanceMarkResultSerializer,
    AttendanceMarkSerializer,
    AttendanceSerializer,
    CancelSessionSerializer,
    MonthlyReportSerializer,
    RequestCorrectionSerializer,
    RosterResponseSerializer,
    TrainingSessionUpdateSerializer,
)


def _coach_for(request) -> Coach | None:
    """Resolves the caller's own Coach profile, if any. The *only* role
    that ever reaches a filter_to_own() below with scope="own" on
    `attendance` is Coach (seed_roles.py's MATRIX row: Student/Parent's
    own bare-"O" grant is unchanged and still falls through to
    queryset.none(), same as before this change) — this is what actually
    restricts roster/marking/cancel/corrections/reports to sessions a
    Coach is assigned to, per docs/03-rbac.md rule 3 ("own" scope enforced
    at the queryset level).
    """
    return Coach.objects.filter(staff__person=request.user.person).first()


class _NoDirectWriteMixin:
    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)


class AttendanceViewSet(_NoDirectWriteMixin, ModuleScopedViewSet):
    """List/retrieve + the correction-request action. Marking itself
    happens via apps.academics.batch's sessions/{id}/attendance/ bulk
    endpoint (SessionAttendanceViewSet below), not a direct POST here.
    """

    module = "attendance"
    serializer_class = AttendanceSerializer
    queryset = Attendance.objects.select_related("session__batch", "student__person").all()

    def filter_to_own(self, queryset):
        coach = _coach_for(self.request)
        if coach is None:
            return queryset.none()
        return queryset.filter(session__coach=coach)

    @extend_schema(request=RequestCorrectionSerializer, responses=AttendanceCorrectionSerializer)
    @action(detail=True, methods=["post"], verb="add")
    def corrections(self, request, pk=None):
        attendance = self.get_object()
        serializer = RequestCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        correction = services.request_correction(
            attendance,
            to_status=serializer.validated_data["to_status"],
            reason=serializer.validated_data["reason"],
            user=request.user,
        )
        return Response(AttendanceCorrectionSerializer(correction).data, status=201)


class AttendanceCorrectionViewSet(_NoDirectWriteMixin, ModuleScopedViewSet):
    module = "attendance"
    serializer_class = AttendanceCorrectionSerializer
    queryset = AttendanceCorrection.objects.select_related(
        "attendance__student__person",
        "requested_by__person",
        "approved_by__person",
    ).all()
    filterset_class = AttendanceCorrectionFilter

    def filter_to_own(self, queryset):
        coach = _coach_for(self.request)
        if coach is None:
            return queryset.none()
        return queryset.filter(attendance__session__coach=coach)

    @extend_schema(request=None, responses=AttendanceCorrectionSerializer)
    @action(detail=True, methods=["post"], verb="approve")
    def approve(self, request, pk=None):
        correction = self.get_object()
        correction = services.approve_correction(correction, user=request.user)
        return Response(AttendanceCorrectionSerializer(correction).data)

    @extend_schema(request=None, responses=AttendanceCorrectionSerializer)
    @action(detail=True, methods=["post"], verb="approve")
    def reject(self, request, pk=None):
        correction = self.get_object()
        correction = services.reject_correction(correction, user=request.user)
        return Response(AttendanceCorrectionSerializer(correction).data)


class SessionAttendanceViewSet(ModuleScopedViewSet):
    """Operates on TrainingSession (apps.academics.batch), not Attendance
    — registered here rather than in apps.academics.batch because every
    action needs Attendance data/logic, and the dependency direction
    (docs/00-project-structure.md: attendance hangs off batch, never the
    reverse) only allows this app to import that one, not the other way
    around.

    Wired by explicit path()+as_view() in urls.py, not router.register —
    same mechanism apps.admissions.admission.views.
    AdmissionPaymentVerificationViewSet uses — so these routes sit
    alongside, not in conflict with, apps.academics.batch's own
    router-registered `sessions/` list/detail routes.

    No @action decorators here: confirmed by direct inspection that a
    ViewSet bound via an explicit `.as_view({...})` call (bypassing the
    router) never reads @action's own `verb=` kwarg — only the router's
    own URL-generation does. `verb` for each action below is instead
    passed directly at the `.as_view({...}, verb="...")` call site in
    urls.py.

    `serializer_class` is required even though every action below builds
    its own Response by hand — without one, drf-spectacular can't
    introspect this ViewSet at all and silently drops every action from
    the generated OpenAPI schema (confirmed: `npm run generate:api` failed
    with "should either include a serializer_class..." until this was
    added), which would have left the frontend with untyped/missing
    request-response shapes.
    """

    module = "attendance"
    # delete_session is narrowed to batch_admin — same "split the row"
    # precedent as BatchViewSet's own create/update/destroy
    # (docs/03-rbac.md), since a hard delete is a bigger authority than
    # marking/cancelling your own sessions (attendance's own-scope Coach
    # grant). update_details stays on the broader `attendance` module so
    # a Coach can still reschedule/report on their own sessions, same
    # scope as cancel() just above.
    action_modules = {"delete_session": "batch_admin"}
    queryset = TrainingSession.objects.select_related("batch").all()
    serializer_class = TrainingSessionSerializer

    def filter_to_own(self, queryset):
        coach = _coach_for(self.request)
        if coach is None:
            return queryset.none()
        return queryset.filter(coach=coach)

    @extend_schema(responses=RosterResponseSerializer)
    def roster(self, request, pk=None):
        session = self.get_object()
        return Response(services.roster(session))

    @extend_schema(
        request=AttendanceMarkSerializer(many=True),
        responses=AttendanceMarkResultSerializer(many=True),
    )
    def attendance(self, request, pk=None):
        session = self.get_object()
        serializer = AttendanceMarkSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        results = services.mark_bulk(session, serializer.validated_data, request.user)
        return Response(results)

    @extend_schema(request=CancelSessionSerializer, responses=TrainingSessionSerializer)
    def cancel(self, request, pk=None):
        session = self.get_object()
        serializer = CancelSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_session(session, reason=serializer.validated_data["reason"])
        return Response(TrainingSessionSerializer(session).data)

    @extend_schema(request=None, responses=TrainingSessionSerializer)
    def mark_conducted(self, request, pk=None):
        session = self.get_object()
        session = services.mark_session_conducted(session)
        return Response(TrainingSessionSerializer(session).data)

    @extend_schema(request=TrainingSessionUpdateSerializer, responses=TrainingSessionSerializer)
    def update_details(self, request, pk=None):
        session = self.get_object()
        serializer = TrainingSessionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "coach" in data:
            data["coach"] = get_object_or_404(Coach, pk=data["coach"])
        if "training_type" in data:
            training_type_id = data["training_type"]
            data["training_type"] = (
                get_object_or_404(TrainingType, pk=training_type_id) if training_type_id else None
            )
        session = services.update_session_details(session, data)
        return Response(TrainingSessionSerializer(session).data)

    @extend_schema(request=None, responses=None)
    def delete_session(self, request, pk=None):
        session = self.get_object()
        services.delete_session(session)
        return Response(status=204)


class BatchReportViewSet(ModuleScopedViewSet):
    """GET /batches/{id}/attendance-report/?month=YYYY-MM. Operates on
    Batch, not Attendance — registered here rather than in
    apps.academics.batch for the same reason as SessionAttendanceViewSet
    above (needs Attendance data, dependency direction only allows this
    app to import that one). Same explicit-path()+verb= wiring as that
    class, same reasoning.
    """

    module = "attendance"
    queryset = Batch.objects.all()
    serializer_class = MonthlyReportSerializer

    def filter_to_own(self, queryset):
        coach = _coach_for(self.request)
        if coach is None:
            return queryset.none()
        return queryset.filter(coach=coach)

    @extend_schema(responses=MonthlyReportSerializer)
    def attendance_report(self, request, pk=None):
        batch = self.get_object()
        month_param = request.query_params.get("month")
        if not month_param:
            raise ValidationError({"month": "Required, as YYYY-MM."})
        try:
            month = datetime.date.fromisoformat(f"{month_param}-01")
        except ValueError:
            raise ValidationError({"month": "Must be YYYY-MM."}) from None
        return Response(services.monthly_report(batch, month))
