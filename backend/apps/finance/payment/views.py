from typing import cast

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import PaymentType
from apps.core.pagination import DefaultCursorPagination
from apps.iam.models import User
from apps.people.models import Person, StudentGuardian

from . import services
from .filters import PaymentFilter
from .models import Payment, PaymentLedgerStatus
from .serializers import CurrentFeeSerializer, PaymentSerializer, RecordPaymentSerializer


class ReceiptNotAvailable(APIException):
    status_code = 409
    default_code = "receipt_not_available"
    default_detail = "This payment was voided — there is no valid receipt for it."


class InvoiceNotAvailable(APIException):
    status_code = 409
    default_code = "invoice_not_available"
    default_detail = "This payment hasn't been settled yet — there is no invoice for it."


def _scoped_payments_queryset(user, queryset=None):
    """`queryset` filtered to what `user` may see under `payment:view` —
    unfiltered (all-scope) for Administration/Accounts, `person ==
    user.person` or one of their linked children's for Student/Parent
    (own-scope). Shared by PaymentListView and the receipt/invoice PDF
    views below, so the same object-level check governs "can list it" and
    "can fetch this one specific payment's document" — see
    PaymentListView's own docstring for why this exists at all: has_perm_
    for() alone proves the permission exists, not its scope.
    """
    if queryset is None:
        queryset = Payment.objects.select_related("person", "payment_type").all()
    if user.scope_for("payment", "view") == "own":
        if user.person_id is None:
            return queryset.none()
        child_person_ids = StudentGuardian.objects.filter(
            guardian__person=user.person
        ).values_list("student__person_id", flat=True)
        queryset = queryset.filter(Q(person=user.person) | Q(person_id__in=child_person_ids))
    return queryset


class PaymentListView(generics.ListAPIView):
    """GET /payments/ — the staff operational queue (Administration/
    Accounts, who hold ALL-scope on `payment:view`). Deliberately separate
    from the self-service `/students/me/payments/` and
    `/parents/me/children/{id}/payments/` endpoints, which return a
    different, summary-shaped response (current month + history) rather
    than a plain browsable/filterable list.
    """

    serializer_class = PaymentSerializer
    pagination_class = DefaultCursorPagination
    filterset_class = PaymentFilter
    queryset = Payment.objects.select_related("person", "payment_type").all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ModuleScopedViewSet's IsAuthenticated-first-then-real-User
        # guarantee doesn't apply to a plain ListAPIView, but the same
        # fact holds here too: permission_classes = [IsAuthenticated]
        # means this only ever runs for a real User, not AnonymousUser.
        user = cast(User, self.request.user)
        if not user.has_perm_for("payment", "view"):
            self.permission_denied(self.request)
        # has_perm_for only proves the *permission* exists — it says
        # nothing about scope. docs/03-rbac.md's `payment` row grants
        # Student/Parent own-scope `V` only (Administration/Accounts hold
        # `VAEP` at all-scope); without _scoped_payments_queryset a
        # Student or Parent role hitting this endpoint directly got every
        # payment in the system — amounts, payment modes, UTR/cheque
        # reference numbers, confirmation/invoice numbers — not just
        # their own. Every ModuleScopedViewSet elsewhere gets this for
        # free from scope_for()+filter_to_own(); this view predates that
        # base class and never got the equivalent check.
        return _scoped_payments_queryset(user, super().get_queryset())


class PaymentRecordView(APIView):
    """POST /payments/record/ — the real, role-gated path to record a
    monthly coaching fee (or any other PaymentType): `payment:add`, held
    by Administration and Accounts (docs/03-rbac.md's `payment` row) —
    not Django-admin/superuser access, which is a separate system that
    doesn't reflect this app's own Role/RolePermission grants at all.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=RecordPaymentSerializer, responses=PaymentSerializer)
    def post(self, request):
        if not request.user.has_perm_for("payment", "add"):
            self.permission_denied(request)
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        person = get_object_or_404(Person, pk=data["person"])
        payment_type = get_object_or_404(PaymentType, pk=data["payment_type"])

        payment = services.record_payment(
            person,
            payment_type=payment_type,
            billing_period=data["billing_period"],
            amount=data["amount"],
            payment_mode=data["payment_mode"],
            reference_no=data["reference_no"],
            payment_date=data["payment_date"],
            user=request.user,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(PaymentSerializer(payment).data, status=201)


class CurrentFeeView(APIView):
    """GET /payments/current-fee/?person=<id> — the amount RecordPayment-
    Form pre-fills for a "monthly coaching fee" payment, computed from
    the person's active Student + active BatchEnrollment: `Batch.
    residential_monthly_fee` if `Student.residential`, else `Batch.
    monthly_fee`. Still just a default — the form field stays editable
    (CurrentFeeSerializer's own docstring).

    `apps.admissions.student`/`apps.academics.batch` are local imports,
    not top-level ones: docs/00-project-structure.md's dependency chain
    draws `batch` and `fee`/`payment` as siblings off `student`, not
    chained to each other, the same boundary
    apps.academics.batch.serializers.BatchEnrollmentSerializer.
    get_fee_status already crosses the other way (a local import of
    apps.finance.payment.services inside batch) for the identical reason
    — a narrow, one-off read that a top-level app dependency would
    overstate.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=CurrentFeeSerializer)
    def get(self, request):
        if not request.user.has_perm_for("payment", "add"):
            self.permission_denied(request)

        person_id = request.query_params.get("person")
        if not person_id:
            return Response(CurrentFeeSerializer({"amount": None}).data)

        from apps.academics.batch.models import BatchEnrollment
        from apps.admissions.student.models import Student, StudentStatus

        student = (
            Student.objects.filter(person_id=person_id, status=StudentStatus.ACTIVE)
            .order_by("-admission_date")
            .first()
        )
        if student is None:
            return Response(CurrentFeeSerializer({"amount": None}).data)

        enrollment = (
            BatchEnrollment.objects.filter(student=student, is_active=True)
            .select_related("batch")
            .first()
        )
        if enrollment is None:
            return Response(CurrentFeeSerializer({"amount": None}).data)

        amount = (
            enrollment.batch.residential_monthly_fee
            if student.residential
            else enrollment.batch.monthly_fee
        )
        return Response(CurrentFeeSerializer({"amount": amount}).data)


class PaymentSettleView(APIView):
    """POST /payments/{id}/settle/ — mints the invoice_no. `payment:approve`,
    same two roles as the direct-admission wizard's own payment
    verification (docs/03-rbac.md's `payment` row).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=PaymentSerializer)
    def post(self, request, pk):
        if not request.user.has_perm_for("payment", "approve"):
            self.permission_denied(request)
        payment = get_object_or_404(Payment, pk=pk)
        payment = services.mark_settled(payment, user=request.user)
        return Response(PaymentSerializer(payment).data)


class PaymentReceiptPdfView(APIView):
    """GET /payments/{id}/receipt.pdf/ — the Payment Confirmation Receipt
    (Payment's own docstring: "issued immediately when a payment is
    received"), available from the moment a payment is recorded. Same
    `payment:view` + _scoped_payments_queryset object-level check as
    PaymentListView, so a Student/Parent can only ever fetch their own
    (or their child's) receipt — get_object_or_404 against the scoped
    queryset 404s rather than 403s on someone else's payment, same as
    every other own-scope detail lookup in this codebase (e.g.
    SessionAttendanceViewSet on another coach's session).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: {"type": "string", "format": "binary"}})
    def get(self, request, pk):
        user = cast(User, request.user)
        if not user.has_perm_for("payment", "view"):
            self.permission_denied(request)
        payment = get_object_or_404(_scoped_payments_queryset(user), pk=pk)
        if payment.status == PaymentLedgerStatus.VOID:
            raise ReceiptNotAvailable()

        from .pdf import render_receipt

        pdf_bytes = render_receipt(payment)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{payment.confirmation_no}.pdf"'
        return response


class PaymentInvoicePdfView(APIView):
    """GET /payments/{id}/invoice.pdf/ — the Invoice (Payment's own
    docstring: "issued only after the payment is confirmed as settled"),
    so only ever available once status is SETTLED and invoice_no is
    minted. Same object-level check as PaymentReceiptPdfView above.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: {"type": "string", "format": "binary"}})
    def get(self, request, pk):
        user = cast(User, request.user)
        if not user.has_perm_for("payment", "view"):
            self.permission_denied(request)
        payment = get_object_or_404(_scoped_payments_queryset(user), pk=pk)
        if payment.status != PaymentLedgerStatus.SETTLED or not payment.invoice_no:
            raise InvoiceNotAvailable()

        from .pdf import render_invoice

        pdf_bytes = render_invoice(payment)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{payment.invoice_no}.pdf"'
        return response
