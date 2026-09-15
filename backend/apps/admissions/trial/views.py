from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admissions.enquiry.models import Enquiry
from apps.core.views import ModuleScopedViewSet
from apps.people.models import Staff

from . import services
from .filters import TrialRegistrationFilter, TrialSlotFilter
from .models import TrialRegistration, TrialSlot
from .pdf import render_trial_sheet_pdf
from .serializers import (
    AttendanceSerializer,
    BulkNotifySerializer,
    DeclareResultSerializer,
    SubmitAssessmentSerializer,
    TrialRegistrationSerializer,
    TrialSlotBookSerializer,
    TrialSlotSerializer,
)


class TrialSlotViewSet(ModuleScopedViewSet):
    module = "trial"
    serializer_class = TrialSlotSerializer
    queryset = TrialSlot.objects.select_related("venue", "age_category").all()
    filterset_class = TrialSlotFilter
    http_method_names = ["get", "post", "head", "options"]

    def filter_to_own(self, queryset):
        return queryset.none()

    @action(detail=True, methods=["post"], verb="add")
    def book(self, request, pk=None):
        """POST /trials/slots/{id}/book — docs/02-api-spec.md."""
        serializer = TrialSlotBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry = get_object_or_404(Enquiry, pk=serializer.validated_data["enquiry_id"])
        registration = services.register_from_enquiry(enquiry, pk)
        return Response(TrialRegistrationSerializer(registration).data, status=201)

    @action(detail=True, methods=["get"], url_path="sheet.pdf", verb="print")
    def sheet_pdf(self, request, pk=None):
        slot = self.get_object()
        pdf_bytes = render_trial_sheet_pdf(slot)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="trial-sheet-{slot.date}.pdf"'
        return response


class EnquiryConvertToTrialView(APIView):
    """POST /enquiries/{id}/convert-to-trial — docs/02-api-spec.md lists
    this under "Enquiry", but the implementation lives in `trial` (see
    services.py's module docstring on the dependency direction). Registered
    from this app's urls.py so the URL path still matches the spec exactly.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, enquiry_id):
        if not request.user.has_perm_for("enquiry", "edit"):
            self.permission_denied(request)
        enquiry = get_object_or_404(Enquiry, pk=enquiry_id)
        slot_id = request.data.get("slot_id")
        if not slot_id:
            raise ValidationError({"slot_id": "This field is required."})
        registration = services.register_from_enquiry(enquiry, slot_id)
        return Response(TrialRegistrationSerializer(registration).data, status=201)


class TrialRegistrationViewSet(ModuleScopedViewSet):
    """Only `list`/`retrieve` are real CRUD here — docs/02-api-spec.md
    names exactly GET (list), PATCH .../attendance, POST .../assess and
    POST .../result for this resource, nothing else. The other
    ModelViewSet actions are disabled explicitly rather than left reachable
    by accident.
    """

    module = "trial"
    serializer_class = TrialRegistrationSerializer
    queryset = TrialRegistration.objects.select_related(
        "person", "enquiry", "slot", "slot__venue", "slot__age_category", "assessment", "result"
    ).all()
    filterset_class = TrialRegistrationFilter
    http_method_names = ["get", "post", "patch", "head", "options"]

    def filter_to_own(self, queryset):
        return queryset.none()

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    @action(detail=True, methods=["patch"], verb="edit")
    def attendance(self, request, pk=None):
        registration = self.get_object()
        serializer = AttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.record_attendance(registration, serializer.validated_data["attended"])
        return Response(TrialRegistrationSerializer(registration).data)

    @action(detail=True, methods=["post"], verb="add")
    def assess(self, request, pk=None):
        registration = self.get_object()
        serializer = SubmitAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.submit_assessment(
            registration,
            assessed_by=_staff_for(request.user),
            overall_remarks=serializer.validated_data["overall_remarks"],
            scores=serializer.validated_data["scores"],
        )
        registration = self.get_queryset().get(pk=registration.pk)
        return Response(TrialRegistrationSerializer(registration).data, status=201)

    @action(detail=True, methods=["post"], verb="approve")
    def result(self, request, pk=None):
        registration = self.get_object()
        serializer = DeclareResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.declare_result(
            registration,
            declared_by=request.user,
            **serializer.validated_data,
        )
        registration = self.get_queryset().get(pk=registration.pk)
        return Response(TrialRegistrationSerializer(registration).data, status=201)


def _staff_for(user):
    """The assessing coach — `TrialAssessment.assessed_by` is a Staff FK,
    not a User FK, because SOP identity for staff runs through
    `people.Staff` (docs/01-data-model.md section 1). A user with the
    `trial`/`add` permission who isn't linked to a Staff row (e.g. a system
    or admin account with no employment record) cannot submit assessments —
    that's a real gap in their account setup, not a case to paper over
    with a fabricated Staff row.
    """
    return get_object_or_404(Staff, person=user.person)


class TrialBulkNotifyView(APIView):
    """POST /trials/results/bulk-notify — docs/02-api-spec.md."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.has_perm_for("trial", "approve"):
            self.permission_denied(request)
        serializer = BulkNotifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = services.bulk_notify_results(serializer.validated_data["registration_ids"])
        return Response({"notified": count})
