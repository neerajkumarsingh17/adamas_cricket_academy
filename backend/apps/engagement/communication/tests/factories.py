import factory
from factory.django import DjangoModelFactory

from apps.engagement.communication.models import NotificationChannel, NotificationTemplate


class NotificationTemplateFactory(DjangoModelFactory):
    class Meta:
        model = NotificationTemplate

    code = factory.Sequence(lambda n: f"template_{n}")
    channel = NotificationChannel.SMS
    body = "Hello {{ name }}, your enquiry {{ enquiry_no }} was received."
    is_active = True
