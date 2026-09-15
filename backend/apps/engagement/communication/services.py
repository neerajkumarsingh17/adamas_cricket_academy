"""docs/01-data-model.md section 4: "`notifications.send(code, recipient,
context)` is the only public entry point." Dispatch is always async via
Celery (same doc) — `send()` renders and logs synchronously (so the caller
gets a `NotificationLog` id immediately, e.g. to link from an Enquiry) and
hands the actual delivery attempt to `tasks.dispatch`.
"""

import logging

from django.conf import settings
from django.template import Context, Template
from django.utils import timezone

from .models import NotificationLog, NotificationStatus, NotificationTemplate

logger = logging.getLogger(__name__)


class NoActiveTemplate(Exception):
    """No active NotificationTemplate exists for the requested code."""


def render_template(template: NotificationTemplate, context: dict) -> str:
    return Template(template.body).render(Context(context))


def send(code: str, recipient: str, context: dict | None = None) -> NotificationLog:
    """Queue a notification for `recipient` (a mobile number, email
    address, or device token depending on channel) using the named
    template. Raises NoActiveTemplate rather than silently dropping the
    message if `code` doesn't resolve — a caller that misspells a template
    code needs to find out immediately, not lose an admission notification
    silently in production.
    """
    try:
        template = NotificationTemplate.objects.get(code=code, is_active=True)
    except NotificationTemplate.DoesNotExist:
        raise NoActiveTemplate(f"No active NotificationTemplate with code={code!r}.") from None

    rendered_body = render_template(template, context or {})
    log = NotificationLog.objects.create(
        template=template,
        channel=template.channel,
        recipient=recipient,
        rendered_body=rendered_body,
        status=NotificationStatus.QUEUED,
    )

    from .tasks import dispatch

    dispatch.delay(str(log.id))
    return log


def _send_console(log: NotificationLog) -> tuple[str, str, str]:
    """NOTIFICATION_BACKEND="console" — dev/test only, matches the same
    convention as apps.iam.services.send_otp_sms. Returns
    (status, provider_message_id, error).
    """
    logger.info(
        "[console notification] %s -> %s: %s", log.channel, log.recipient, log.rendered_body
    )
    return NotificationStatus.SENT, "", ""


def dispatch_now(log_id) -> None:
    """The real send, run synchronously — `tasks.dispatch` is a thin
    Celery wrapper around this so the logic itself is directly testable
    without a broker.
    """
    log = NotificationLog.objects.select_related("template").get(pk=log_id)

    if settings.NOTIFICATION_BACKEND == "console":
        status, provider_message_id, error = _send_console(log)
    else:
        status, provider_message_id, error = (
            NotificationStatus.FAILED,
            "",
            f"No notification backend implemented for "
            f"NOTIFICATION_BACKEND={settings.NOTIFICATION_BACKEND!r}.",
        )

    log.status = status
    log.provider_message_id = provider_message_id
    log.error = error
    log.sent_at = timezone.now() if status == NotificationStatus.SENT else None
    log.save(update_fields=["status", "provider_message_id", "error", "sent_at", "updated_at"])
