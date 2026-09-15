from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admissions.trial.models import TrialRegistration
from apps.core.models import Programme
from apps.core.views import ModuleScopedViewSet

from . import services
from .filters import AdmissionFilter
from .models import Admission, AdmissionStep
from .serializers import (
    AdmissionChecklistItemSerializer,
    AdmissionIntakeWriteSerializer,
    AdmissionSerializer,
    AdmissionWriteSerializer,
    AdvanceSerializer,
    CancelAdmissionSerializer,
    ConsentDecisionsWriteSerializer,
    FeeLinesWriteSerializer,
    OpenAdmissionSerializer,
    RecordDirectPaymentSerializer,
    RecordPaymentSerializer,
    RejectAdmissionSerializer,
    VerifyPaymentSerializer,
)

_INTAKE_FIELD_NAMES = set(AdmissionIntakeWriteSerializer().fields)


def _raise_as_drf_validation_error(exc: DjangoValidationError):
    errors = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise ValidationError(errors) from exc


class AdmissionViewSet(ModuleScopedViewSet):
    """docs/02-api-spec.md lists GET/POST (open) and GET/PATCH (detail) on
    the base resource, then everything else as dedicated sub-actions.
    `PATCH` on the base detail route isn't documented at all (only
    `/advance`, `/record-payment`, `/approve`, `/reject`) — disabled
    explicitly rather than left as an accidental back door around the
    state machine (CLAUDE.md rule 5: "Never set a status field directly").
    """

    module = "admission"
    queryset = Admission.objects.select_related("person", "programme", "trial_registration").all()
    filterset_class = AdmissionFilter
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "partial_update":
            return AdmissionWriteSerializer
        return AdmissionSerializer

    def filter_to_own(self, queryset):
        return queryset.none()

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        """The wizard's autosave-on-blur target — a body can mix
        `residential` (an `Admission` field) with any `AdmissionIntake`
        field in the same PATCH; each is routed to the model it actually
        belongs to. `intake.clean()` re-validates the *whole* merged
        intake after applying the patch, not just the touched fields, so
        a patch that leaves it in an inconsistent state (e.g. switching
        to residential without clearing days_per_week in the same call)
        is refused with a real error rather than silently accepted.
        """
        admission = self.get_object()
        intake = getattr(admission, "intake", None)

        intake_data = {k: v for k, v in request.data.items() if k in _INTAKE_FIELD_NAMES}
        if intake_data:
            if intake is None:
                raise ValidationError({"detail": "This admission has no intake to update."})
            intake_serializer = AdmissionIntakeWriteSerializer(
                intake, data=intake_data, partial=True
            )
            intake_serializer.is_valid(raise_exception=True)
            for field, value in intake_serializer.validated_data.items():
                setattr(intake, field, value)
            try:
                intake.clean()
            except DjangoValidationError as exc:
                _raise_as_drf_validation_error(exc)
            intake.save()

        admission_data = {k: v for k, v in request.data.items() if k == "residential"}
        if admission_data:
            admission_serializer = AdmissionWriteSerializer(
                admission, data=admission_data, partial=True
            )
            admission_serializer.is_valid(raise_exception=True)
            admission_serializer.save()

        return Response(AdmissionSerializer(admission, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        serializer = OpenAdmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trial_registration = get_object_or_404(
            TrialRegistration, pk=serializer.validated_data["trial_registration"]
        )
        programme = get_object_or_404(Programme, pk=serializer.validated_data["programme"])
        admission = services.open_admission(
            trial_registration=trial_registration,
            programme=programme,
            residential=serializer.validated_data["residential"],
        )
        return Response(AdmissionSerializer(admission).data, status=201)

    @action(detail=False, methods=["post"], url_path="direct", verb="add")
    def direct(self, request):
        """POST /admissions/direct/ — the fee-first wizard's entry point:
        a bare DRAFT `Admission` plus its `AdmissionIntake`, in one step.
        No Person, no Programme yet — approve() resolves those.

        Replaces the pre-existing trial-waiver direct-admission POST that
        used to live at this exact path (`services.open_direct_admission`,
        `DirectAdmissionSerializer`) — that flow's other endpoints
        (`/enable-portal`, `/mine`) are untouched for now, but this create
        path is gone; a cleanup pass to remove the now-unreachable code
        is a good follow-up once the new wizard is confirmed working.
        """
        serializer = AdmissionIntakeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            admission = services.open_direct_admission_intake(
                intake_data=serializer.validated_data
            )
        except DjangoValidationError as exc:
            _raise_as_drf_validation_error(exc)
        return Response(
            AdmissionSerializer(admission, context={"request": request}).data, status=201
        )

    @action(detail=False, methods=["get"], url_path="mine", verb="view")
    def mine(self, request):
        """GET /admissions/mine — self-service: the candidate's own
        in-progress direct admission (product decision: step 2.1's portal
        upload). Deliberately bypasses `filter_to_own`/`get_queryset()` —
        this viewset's own `filter_to_own` returns nothing at all (staff
        only), and a person-scoped lookup here needs no other row of
        theirs to ever be reachable through it, so a dedicated query is
        clearer than trying to make the shared one support both.
        """
        if request.user.person_id is None:
            return Response(status=404)
        admission = (
            Admission.objects.select_related("person", "programme", "trial_registration")
            .filter(person_id=request.user.person_id)
            .exclude(step__in=[AdmissionStep.APPROVED, AdmissionStep.REJECTED])
            .order_by("-created_at")
            .first()
        )
        if admission is None:
            return Response(status=404)
        return Response(AdmissionSerializer(admission).data)

    @action(detail=True, methods=["post"], url_path="enable-portal", verb="edit")
    def enable_portal(self, request, pk=None):
        """POST /admissions/{id}/enable-portal — step 2.1: Administration
        confirms payment is in, then switches on the candidate's own
        portal login and moves the admission on to document collection in
        one action.
        """
        admission = self.get_object()
        admission = services.enable_portal_access(admission, user=request.user)
        return Response(AdmissionSerializer(admission).data)

    @action(detail=True, methods=["get"], verb="view")
    def checklist(self, request, pk=None):
        admission = self.get_object()
        return Response(
            AdmissionChecklistItemSerializer(admission.checklist_items.all(), many=True).data
        )

    @action(detail=True, methods=["post"], verb="edit")
    def advance(self, request, pk=None):
        admission = self.get_object()
        serializer = AdvanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.advance(
            admission,
            to_step=serializer.validated_data["to_step"],
            user=request.user,
            reason=serializer.validated_data["reason"],
        )
        return Response(AdmissionSerializer(admission).data)

    @action(detail=True, methods=["post"], verb="approve")
    def reject(self, request, pk=None):
        admission = self.get_object()
        serializer = RejectAdmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reject_admission(
            admission, user=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(AdmissionSerializer(admission).data)

    @action(detail=True, methods=["put"], verb="edit")
    def fees(self, request, pk=None):
        """PUT /admissions/{id}/fees/ — replaces the fee lines wholesale,
        the fee-first wizard's Step 2 fee fieldset.
        """
        admission = self.get_object()
        serializer = FeeLinesWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.set_fee_lines(admission, lines=serializer.validated_data["lines"])
        except DjangoValidationError as exc:
            _raise_as_drf_validation_error(exc)
        return Response(AdmissionSerializer(admission, context={"request": request}).data)

    @action(detail=True, methods=["post"], verb="edit")
    def consents(self, request, pk=None):
        """POST /admissions/{id}/consents/ — bulk upsert, the fee-first
        wizard's Step 2 consent fieldset.
        """
        admission = self.get_object()
        serializer = ConsentDecisionsWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.record_consents(
            admission,
            decisions=serializer.validated_data["decisions"],
            declared_by_name=serializer.validated_data["declared_by_name"],
            granted_ip=request.META.get("REMOTE_ADDR"),
        )
        return Response(AdmissionSerializer(admission, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="submit-documents", verb="add")
    def submit_documents(self, request, pk=None):
        """POST /admissions/{id}/submit-documents/ — the desk (or the
        candidate, once portal access exists) declares the AT_ADMISSION
        documents ready for review. Uploading itself happens beforehand,
        through the existing presign/confirm flow.
        """
        admission = self.get_object()
        services.submit_direct_documents(admission, user=request.user)
        return Response(AdmissionSerializer(admission, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="cancel", verb="edit")
    def cancel(self, request, pk=None):
        admission = self.get_object()
        serializer = CancelAdmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_admission(
            admission, user=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(AdmissionSerializer(admission, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="direct/bootstrap", verb="view")
    def bootstrap(self, request):
        """GET /admissions/direct/bootstrap/ — every piece of master data
        the wizard needs, in one round trip. The form renders nothing
        from a hardcoded list — change a fee head in the database and the
        form changes.
        """
        from apps.core.models import (
            AgeCategory,
            ConsentType,
            DocumentRequiredStage,
            DocumentType,
            FeeHead,
            Season,
        )
        from apps.core.serializers import (
            AgeCategorySerializer,
            ConsentTypeSerializer,
            DocumentTypeSerializer,
            FeeHeadSerializer,
            SeasonSerializer,
        )

        season = Season.objects.filter(is_active=True).order_by("-start_date").first()
        document_types = DocumentType.objects.exclude(required_stage="")
        by_stage = {
            stage: DocumentTypeSerializer(
                document_types.filter(required_stage=stage), many=True
            ).data
            for stage, _ in DocumentRequiredStage.choices
        }
        return Response(
            {
                "season": SeasonSerializer(season).data if season else None,
                "age_categories": AgeCategorySerializer(
                    AgeCategory.objects.filter(is_active=True), many=True
                ).data,
                "fee_heads": FeeHeadSerializer(
                    FeeHead.objects.filter(is_active=True), many=True
                ).data,
                "consent_types": ConsentTypeSerializer(
                    ConsentType.objects.filter(is_active=True), many=True
                ).data,
                "document_types_by_stage": by_stage,
            }
        )

    @action(detail=True, methods=["get"], url_path="print", verb="view")
    def print_form(self, request, pk=None):
        """GET /admissions/{id}/print/ — the filled form as PDF, for the
        desk's own paper trail."""
        from django.http import HttpResponse

        from .pdf import render_direct_admission_form

        admission = self.get_object()
        pdf_bytes = render_direct_admission_form(admission)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{admission.application_no}.pdf"'
        return response


# docs/04-state-machines.md section 1 explicitly permits Accounts on
# fee_pending -> fee_cleared, but docs/03-rbac.md's own matrix gives
# Accounts only "V" (view) on the enquiry/admission row — the same
# "RBAC data doesn't cover this, code must" situation as
# apps.admissions.student.state.StudentStatusMachine's medical_hold/
# fee_hold transitions. A plain APIView, not a ModuleScopedViewSet action,
# because that base class's check_permissions() gates *every* action on
# one module+verb pair uniformly — there's no per-action escape hatch, and
# adding one here would make the auto-discovered permission-matrix test
# assert something docs/03-rbac.md's row doesn't say.
ACCOUNTS_ROLE = "accounts"


class AdmissionRecordPaymentView(APIView):
    """POST /admissions/{id}/record-payment — docs/02-api-spec.md.

    Dispatches on whether the admission has an `AdmissionIntake`: the
    fee-first wizard's own record-payment (real `admission`/`add` RBAC,
    a receipt-numbered `AdmissionPayment` row) versus the pre-existing
    trial-chain fee stub below, untouched.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        admission = get_object_or_404(Admission, pk=pk)

        if hasattr(admission, "intake"):
            if not request.user.has_perm_for("admission", "add"):
                self.permission_denied(request)
            direct_serializer = RecordDirectPaymentSerializer(data=request.data)
            direct_serializer.is_valid(raise_exception=True)
            try:
                services.record_direct_payment(
                    admission,
                    **direct_serializer.validated_data,
                    user=request.user,
                    idempotency_key=request.headers.get("Idempotency-Key", ""),
                )
            except DjangoValidationError as exc:
                _raise_as_drf_validation_error(exc)
            return Response(AdmissionSerializer(admission, context={"request": request}).data)

        held_roles = {role.code for role in request.user.current_roles()}
        if not (request.user.has_perm_for("admission", "edit") or ACCOUNTS_ROLE in held_roles):
            self.permission_denied(request)

        legacy_serializer = RecordPaymentSerializer(data=request.data)
        legacy_serializer.is_valid(raise_exception=True)
        services.record_payment(admission, **legacy_serializer.validated_data, user=request.user)
        return Response(AdmissionSerializer(admission).data)


class AdmissionPaymentVerificationViewSet(ModuleScopedViewSet):
    """POST /admissions/{id}/verify-payment/ — its own `payment` module
    (Accounts/Administration, per docs/03-rbac.md's new row) rather than
    riding on `admission`/edit the way the trial-chain's fee-clearance
    carve-out above does; the whole point was to replace that hardcoded
    role check with real RBAC data for the new chain (CLAUDE.md rule 3).
    """

    module = "payment"
    queryset = Admission.objects.all()
    serializer_class = VerifyPaymentSerializer

    def filter_to_own(self, queryset):
        return queryset.none()

    @action(detail=True, methods=["post"], url_path="verify-payment", verb="approve")
    def verify(self, request, pk=None):
        admission = self.get_object()
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.verify_direct_payment(
            admission, user=request.user, **serializer.validated_data
        )
        return Response(AdmissionSerializer(admission, context={"request": request}).data)


class AdmissionDocumentVerificationViewSet(ModuleScopedViewSet):
    """POST /admissions/{id}/verify-documents/ — `documents`/`approve`,
    the same permission Administration already holds for verifying any
    other uploaded document (docs/03-rbac.md), rather than requiring the
    stricter `admission`/`approve` (Academy Head) this early in the chain.
    """

    module = "documents"
    queryset = Admission.objects.all()
    serializer_class = AdmissionSerializer

    def filter_to_own(self, queryset):
        return queryset.none()

    @action(detail=True, methods=["post"], url_path="verify-documents", verb="approve")
    def verify(self, request, pk=None):
        admission = self.get_object()
        services.verify_direct_documents(admission, user=request.user)
        return Response(AdmissionSerializer(admission, context={"request": request}).data)
