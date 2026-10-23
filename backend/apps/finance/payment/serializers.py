from django.core.validators import MinValueValidator
from rest_framework import serializers

from .models import AdmissionPayment, OnlinePayment, Payment


class CurrentFeeSerializer(serializers.Serializer):
    """GET /payments/current-fee/ response — an amount to pre-fill the
    record-payment form with, or null when the selected person isn't an
    active student with an active batch enrolment (a coach's salary, a
    one-off admission fee, a guardian with no billable relationship of
    their own, ...). Never authoritative: the form field it fills stays
    editable, see PaymentsPage.tsx's RecordPaymentForm.
    """

    amount = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)


class AdmissionPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionPayment
        fields = [
            "id",
            "payment_mode",
            "receipt_no",
            "reference_no",
            "payment_date",
            "verified_by",
            "verified_at",
            "verification_note",
            "created_at",
        ]
        read_only_fields = fields


class RecordPaymentSerializer(serializers.Serializer):
    """POST /payments/record/ — the fields a human actually supplies;
    everything else (confirmation_no, status, recorded_by) is set by
    services.record_payment, not accepted as input.
    """

    person = serializers.UUIDField()
    payment_type = serializers.UUIDField()
    billing_period = serializers.DateField(required=False, allow_null=True, default=None)
    # Mirrors Payment.amount's own MinValueValidator(0) (models.py) —
    # this is a plain Serializer, not a ModelSerializer, so that
    # validator isn't inherited automatically the way BatchWriteSerializer
    # picks up Batch's field validators. Without it, a negative amount
    # only ever got caught later by services.record_payment's
    # payment.full_clean() — after an Idempotency-Key check and a
    # confirmation_no already minted from the PCF sequence, which a
    # rejected payment has no business consuming.
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    payment_mode = serializers.CharField()
    reference_no = serializers.CharField(required=False, allow_blank=True, default="")
    payment_date = serializers.DateField()


class PaymentSerializer(serializers.ModelSerializer):
    payment_type_label = serializers.CharField(source="payment_type.label", read_only=True)
    # Blank for the self-service /students/me/payments/ and /parents/me/
    # children/{id}/payments/ endpoints, whose caller already knows whose
    # payment this is — but the staff-facing PaymentListView needs "which
    # person" on every row, so this is always included rather than left
    # off the read shape entirely (as it was before that view existed).
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "person",
            "person_name",
            "payment_type",
            "payment_type_label",
            "billing_period",
            "amount",
            "payment_mode",
            "reference_no",
            "payment_date",
            "status",
            "confirmation_no",
            "confirmed_at",
            "invoice_no",
            "invoiced_at",
            "void_reason",
        ]
        read_only_fields = fields

    def get_person_name(self, obj) -> str:
        return f"{obj.person.first_name} {obj.person.last_name}".strip()


class OnlinePaymentSerializer(serializers.ModelSerializer):
    """One online collection attempt — a desk checkout or a payment link —
    for a direct admission's fee or a ledger payment."""

    person_name = serializers.SerializerMethodField()
    payment_type_label = serializers.CharField(
        source="payment_type.label", read_only=True, default=None
    )

    class Meta:
        model = OnlinePayment
        fields = [
            "id",
            "kind",
            "gateway",
            "status",
            "amount",
            "person",
            "person_name",
            "payment_type",
            "payment_type_label",
            "billing_period",
            "payment",
            "short_url",
            "sent_to",
            "gateway_payment_id",
            "paid_at",
            "note",
            "created_at",
        ]
        read_only_fields = fields

    def get_person_name(self, obj: OnlinePayment) -> str | None:
        return str(obj.person) if obj.person_id else None


class OnlineCheckoutSerializer(serializers.Serializer):
    """The gateway name plus the options its checkout window opens with
    (apps.finance.payment.gateways — provider-specific, passed through)."""

    gateway = serializers.CharField()
    options = serializers.DictField()


class LedgerOnlinePaymentSerializer(serializers.Serializer):
    """POST /payments/online/checkout/ and /send-link/ — the same "what is
    being paid" fields as RecordPaymentSerializer, minus how it was paid."""

    person = serializers.UUIDField()
    payment_type = serializers.UUIDField()
    billing_period = serializers.DateField(required=False, allow_null=True, default=None)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class LedgerCheckoutResponseSerializer(serializers.Serializer):
    checkout = OnlineCheckoutSerializer()
    online_payment = OnlinePaymentSerializer()


class OnlinePaymentPayloadSerializer(serializers.Serializer):
    """What the gateway's checkout window returned, passed through
    untouched for the adapter to verify."""

    payload = serializers.DictField(child=serializers.CharField(max_length=512))


class ConfirmCheckoutSerializer(serializers.Serializer):
    """What the browser posts back after the gateway's checkout window
    reports success. `payload` is the gateway's own response, passed
    through untouched for the adapter to verify."""

    gateway_id = serializers.CharField(max_length=64)
    payload = serializers.DictField(child=serializers.CharField(max_length=512))
