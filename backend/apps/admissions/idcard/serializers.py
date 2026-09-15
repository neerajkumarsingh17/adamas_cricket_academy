from rest_framework import serializers

from .models import IDCard


class IDCardSerializer(serializers.ModelSerializer):
    student_code = serializers.CharField(source="student.student_code", read_only=True)

    class Meta:
        model = IDCard
        fields = [
            "id",
            "student",
            "student_code",
            "card_no",
            "issued_on",
            "valid_until",
            "status",
            "replaces",
            "issued_by",
        ]
        read_only_fields = fields


class IssueCardSerializer(serializers.Serializer):
    valid_until = serializers.DateField(required=False, allow_null=True)


class BatchPrintSerializer(serializers.Serializer):
    student_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class QRResolveSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    student_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    valid_until = serializers.DateField(required=False)
