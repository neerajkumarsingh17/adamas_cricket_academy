from django.db import models

from apps.core.models import AuditedModel, TimeStampedModel


class NotificationChannel(models.TextChoices):
    SMS = "sms", "SMS"
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"
    PUSH = "push", "Push"
    INAPP = "inapp", "In-app"


class NotificationTemplate(AuditedModel):
    """docs/01-data-model.md section 4. `body` holds `{{placeholder}}`
    tokens rendered by `services.render_template()`. Edited by staff, so
    this is audited like any other admin-managed record.
    """

    code = models.SlugField(max_length=100, unique=True)
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    provider_template_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="WhatsApp Business API needs Meta's pre-approved template id.",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.code} ({self.channel})"


class NotificationStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"


class NotificationLog(TimeStampedModel):
    """A system-written delivery record, not an admin-edited one — plain
    `TimeStampedModel` rather than `AuditedModel`. Its own `status` field
    already tells the delivery story; a parallel AuditLog diff of the same
    queued->sent transition would just be noise, unlike a real business
    record (docs/01-data-model.md section 4 doesn't mark this audited).
    """

    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.PROTECT, related_name="logs"
    )
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    recipient = models.CharField(max_length=255)
    rendered_body = models.TextField()
    status = models.CharField(
        max_length=10, choices=NotificationStatus.choices, default=NotificationStatus.QUEUED
    )
    provider_message_id = models.CharField(max_length=100, blank=True)
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["recipient", "channel"])]

    def __str__(self) -> str:
        return f"{self.channel}:{self.recipient} ({self.status})"
