import pytest

from apps.engagement.communication.models import NotificationLog, NotificationStatus
from apps.engagement.communication.services import NoActiveTemplate, send

from .factories import NotificationTemplateFactory


@pytest.mark.django_db
def test_send_renders_the_template_and_queues_a_log():
    template = NotificationTemplateFactory(
        code="enquiry_ack", body="Hi {{ name }}, thanks for enquiring ({{ enquiry_no }})."
    )

    log = send(
        code="enquiry_ack",
        recipient="+919876543210",
        context={"name": "Arjun", "enquiry_no": "ENQ/2627/00001"},
    )

    assert log.template_id == template.id
    assert log.rendered_body == "Hi Arjun, thanks for enquiring (ENQ/2627/00001)."
    # CELERY_TASK_ALWAYS_EAGER (settings/test.py) means .delay() already ran
    # synchronously by the time send() returns.
    log.refresh_from_db()
    assert log.status == NotificationStatus.SENT
    assert log.sent_at is not None


@pytest.mark.django_db
def test_send_with_unknown_code_raises_rather_than_dropping_silently():
    with pytest.raises(NoActiveTemplate):
        send(code="does_not_exist", recipient="+919876543210")


@pytest.mark.django_db
def test_send_with_inactive_template_is_not_found():
    NotificationTemplateFactory(code="disabled_template", is_active=False)

    with pytest.raises(NoActiveTemplate):
        send(code="disabled_template", recipient="+919876543210")


@pytest.mark.django_db
def test_failed_backend_records_the_error_not_a_silent_drop(settings):
    settings.NOTIFICATION_BACKEND = "msg91"  # not implemented
    NotificationTemplateFactory(code="via_unimplemented_backend", body="x")

    log = send(code="via_unimplemented_backend", recipient="+919876543210")

    log.refresh_from_db()
    assert log.status == NotificationStatus.FAILED
    assert "msg91" in log.error


@pytest.mark.django_db
def test_notification_log_str_includes_channel_and_recipient():
    template = NotificationTemplateFactory()
    log = NotificationLog.objects.create(
        template=template, channel=template.channel, recipient="+919876543210", rendered_body="x"
    )
    assert "+919876543210" in str(log)
