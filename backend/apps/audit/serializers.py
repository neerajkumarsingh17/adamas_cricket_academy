from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_login_id = serializers.CharField(source="actor.login_id", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_login_id",
            "action",
            "model_label",
            "object_id",
            "changes",
            "ip_address",
            "user_agent",
            "request_id",
            "created_at",
        ]
        read_only_fields = fields


class AuditExportResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    row_count = serializers.IntegerField()
