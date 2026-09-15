from rest_framework import serializers

from .models import AdmissionPayment


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
