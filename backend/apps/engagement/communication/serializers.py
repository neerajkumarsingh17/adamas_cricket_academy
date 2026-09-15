from rest_framework import serializers

from .models import NotificationLog, NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "code",
            "channel",
            "subject",
            "body",
            "provider_template_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "template",
            "channel",
            "recipient",
            "rendered_body",
            "status",
            "provider_message_id",
            "error",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationSendSerializer(serializers.Serializer):
    template_code = serializers.SlugField()
    recipients = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    # Shadows DRF Field's own read-only `context` property (the
    # serializer-context mapping) by name only — this is a genuine input
    # field, the template-render context, not that property.
    context = serializers.DictField(required=False, default=dict)  # type: ignore[assignment]
