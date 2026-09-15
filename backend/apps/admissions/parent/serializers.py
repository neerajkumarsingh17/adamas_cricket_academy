from rest_framework import serializers

from .models import ParentPortalAccess


class ParentPortalAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentPortalAccess
        fields = [
            "id",
            "is_portal_enabled",
            "preferred_language",
            "sms_opt_in",
            "whatsapp_opt_in",
            "email_opt_in",
            "push_opt_in",
        ]
        read_only_fields = ["id", "is_portal_enabled"]


class ParentDocumentUploadSerializer(serializers.Serializer):
    student = serializers.UUIDField()
    document_type = serializers.UUIDField()
    s3_key = serializers.CharField()
    filename = serializers.CharField()
    mime = serializers.CharField()
