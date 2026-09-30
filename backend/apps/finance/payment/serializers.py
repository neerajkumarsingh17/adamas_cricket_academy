from django.core.validators import MinValueValidator
from rest_framework import serializers

from .models import AdmissionPayment, Payment


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
