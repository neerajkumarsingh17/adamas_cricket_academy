import factory
from factory.django import DjangoModelFactory

from apps.engagement.communication.models import (
    NotificationChannel,
    NotificationLog,
    NotificationTemplate,
)


class NotificationTemplateFactory(DjangoModelFactory):
    class Meta:
        model = NotificationTemplate

    code = factory.Sequence(lambda n: f"template_{n}")
    channel = NotificationChannel.SMS
    body = "Hello {{ name }}, your enquiry {{ enquiry_no }} was received."
    is_active = True


class NotificationLogFactory(DjangoModelFactory):
    class Meta:
        model = NotificationLog

    template = factory.SubFactory(NotificationTemplateFactory)
    channel = NotificationChannel.SMS
    recipient = factory.Sequence(lambda n: f"+9198000{n:05d}")
    rendered_body = "Hello, your enquiry was received."
