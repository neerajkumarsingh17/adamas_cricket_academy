from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.admissions.student.models import Student
from apps.core.pagination import DefaultCursorPagination
from apps.core.views import ModuleScopedViewSet

from . import services
from .filters import BatchEnrollmentFilter, TrainingSessionFilter
from .models import Batch, BatchEnrollment, Coach, TrainingSession
from .serializers import (
    BatchEnrollmentSerializer,
    BatchSerializer,
    BatchWriteSerializer,
    CoachSerializer,
    EnrolSerializer,
    TrainingSessionSerializer,
    TransferSerializer,
)


class _NoDirectWriteMixin:
    """create/update/destroy are disabled — each of these three resources
    is written through its own dedicated action (enrol/transfer), not a
    raw field-level PUT/PATCH/POST, same convention as
    apps.admissions.document.views.DocumentViewSet.
    """

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)


class BatchViewSet(ModuleScopedViewSet):
    """GET /batches/ — "list with seats used vs capacity", annotated on
    the queryset rather than computed per-row in the serializer, so it's
    one query, not N+1.

    Unlike BatchEnrollmentViewSet/TrainingSessionViewSet, this ViewSet's
    create/update/partial_update/destroy are real — gated on the
    `batch_admin` module (narrower than `batch`'s own broad
    view/enrol/transfer roles) via action_modules, per
    apps.core.management.commands.seed_roles.py's MATRIX comment.
    """

    module = "batch"
    action_modules = {
        "create": "batch_admin",
        "update": "batch_admin",
        "partial_update": "batch_admin",
        "destroy": "batch_admin",
    }
    serializer_class = BatchSerializer
    queryset = (
        Batch.objects.select_related("age_category", "coach__staff__person", "venue")
        .annotate(enrolled_count=Count("enrollments", filter=Q(enrollments__is_active=True)))
        .all()
    )

    def filter_to_own(self, queryset):
        # No self-service "my batch" screen this pass.
        return queryset.none()

    @extend_schema(request=BatchWriteSerializer, responses=BatchSerializer)
    def create(self, request, *args, **kwargs):
        serializer = BatchWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()
        return Response(BatchSerializer(self.get_queryset().get(pk=batch.pk)).data, status=201)

    @extend_schema(request=BatchWriteSerializer, responses=BatchSerializer)
    def update(self, request, *args, **kwargs):
        batch = self.get_object()
        services.assert_batch_editable(batch)
        serializer = BatchWriteSerializer(
            batch, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BatchSerializer(self.get_queryset().get(pk=batch.pk)).data)

    @extend_schema(request=BatchWriteSerializer, responses=BatchSerializer)
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(request=None, responses=None)
    def destroy(self, request, *args, **kwargs):
        batch = self.get_object()
        services.delete_batch(batch)
        return Response(status=204)

    @extend_schema(request=EnrolSerializer, responses=BatchEnrollmentSerializer)
    @action(detail=True, methods=["post"], verb="add")
    def enrol(self, request, pk=None):
        batch = self.get_object()
        serializer = EnrolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = get_object_or_404(Student, pk=serializer.validated_data["student"])
        enrollment = services.enrol(
            student, batch, from_date=serializer.validated_data["from_date"]
        )
        return Response(BatchEnrollmentSerializer(enrollment).data, status=201)


class BatchEnrollmentViewSet(_NoDirectWriteMixin, ModuleScopedViewSet):
    module = "batch"
    serializer_class = BatchEnrollmentSerializer
    queryset = BatchEnrollment.objects.select_related("student__person", "batch").all()
    filterset_class = BatchEnrollmentFilter

    def filter_to_own(self, queryset):
        return queryset.none()

    @extend_schema(request=TransferSerializer, responses=BatchEnrollmentSerializer)
    @action(detail=True, methods=["post"], verb="edit")
    def transfer(self, request, pk=None):
        enrollment = self.get_object()
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_batch = get_object_or_404(Batch, pk=serializer.validated_data["to_batch"])
        new_enrollment = services.transfer(
            enrollment, to_batch, effective_date=serializer.validated_data["effective_date"]
        )
        return Response(BatchEnrollmentSerializer(new_enrollment).data, status=201)


class UpcomingSessionPagination(DefaultCursorPagination):
    """Soonest session first, not "most recently created" — the default
    `-created_at` ordering would put whatever generate_sessions() (or a
    manual create) happened to insert last at the top, which for a
    schedule listing is the wrong axis entirely. `id` breaks ties between
    sessions sharing the same date/start_time (distinct batches), which
    CursorPagination requires for a stable cursor.
    """

    ordering = ["date", "start_time", "id"]


class TrainingSessionViewSet(_NoDirectWriteMixin, ModuleScopedViewSet):
    """List/retrieve only here — roster, bulk attendance-marking and
    cancel all need Attendance data, so they're registered from
    apps.academics.attendance instead (see that app's views.py
    SessionAttendanceViewSet for why).
    """

    module = "batch"
    serializer_class = TrainingSessionSerializer
    pagination_class = UpcomingSessionPagination
    queryset = TrainingSession.objects.select_related(
        "batch", "coach__staff__person", "training_type"
    ).all()
    filterset_class = TrainingSessionFilter

    def filter_to_own(self, queryset):
        return queryset.none()


class CoachViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /coaches/ — populates the Batch create/edit form's coach
    picker; no such listing existed before (Coach was only ever readable
    nested inside a Batch). Read-only and ungated beyond IsAuthenticated,
    same reasoning as apps.core.views.ProgrammeViewSet/AgeCategoryViewSet/
    VenueViewSet: reference data nearly every role needs, and
    CoachSerializer exposes nothing here it doesn't already expose nested
    inside every Batch under the already-broad `batch:view`.

    Filtered on Staff.is_active (still employed), not Coach.is_available
    (a scheduling flag) — excluding an unavailable coach would make it
    impossible to edit a batch whose assigned coach is just temporarily
    off the roster.
    """

    queryset = Coach.objects.select_related("staff__person").filter(staff__is_active=True)
    serializer_class = CoachSerializer
    permission_classes = [IsAuthenticated]
