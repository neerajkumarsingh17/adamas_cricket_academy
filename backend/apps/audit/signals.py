"""CLAUDE.md rule 4: "Audit is automatic... Never write manual audit calls."

Connected with `sender=None` (every model, not one at a time) and an
`isinstance(instance, AuditedModel)` guard, so a new module that inherits
`AuditedModel` is covered the moment it's written — no per-app wiring step
to forget. `AuditLog` itself is a plain `models.Model`, not `AuditedModel`,
so this can never recurse into auditing its own writes.
"""

import datetime
import decimal
import uuid
from typing import Any

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.core.models import AuditedModel

from .middleware import get_current_request
from .models import AuditAction, AuditLog

_SKIP_FIELDS = {"created_at", "updated_at"}


def _json_safe(value: Any) -> Any:
    # datetime.datetime is itself a subclass of datetime.date, but
    # datetime.time is a distinct class the first branch would silently
    # miss — TrialSlot.reporting_time (and any other bare TimeField) needs
    # its own check, not just DateField/DateTimeField.
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (decimal.Decimal, uuid.UUID)):
        return str(value)
    return value


def _field_values(instance) -> dict[str, Any]:
    """`field.attname` (not `field.name`) so a ForeignKey yields its raw
    `*_id` value, never the related object — diffing the id costs no extra
    query; diffing the object would run one per field per save.
    """
    return {
        field.attname: _json_safe(getattr(instance, field.attname))
        for field in instance._meta.concrete_fields
        if field.attname not in _SKIP_FIELDS
    }


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _write(instance, action: str, changes: dict) -> None:
    request = get_current_request()
    actor = None
    ip_address = None
    user_agent = ""
    request_id = ""

    if request is not None:
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            actor = user
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        request_id = getattr(request, "request_id", "")

    AuditLog.objects.create(
        actor=actor,
        action=action,
        model_label=f"{instance._meta.app_label}.{type(instance).__name__}",
        object_id=str(instance.pk),
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )


@receiver(pre_save)
def capture_before(sender, instance, **kwargs):
    if not isinstance(instance, AuditedModel):
        return
    instance._audit_before = None
    if instance.pk is not None:
        row = (
            sender.objects.filter(pk=instance.pk)
            .values(*[f.attname for f in instance._meta.concrete_fields])
            .first()
        )
        # `.values()` returns raw Python types (UUID, Decimal, date, ...),
        # same as `_field_values()` does for the "after" side below — both
        # sides need `_json_safe` or a changed UUID/Decimal/date field's
        # "from" value fails JSONField serialization at write time.
        if row is not None:
            instance._audit_before = {field: _json_safe(value) for field, value in row.items()}


@receiver(post_save)
def write_create_or_update(sender, instance, created, **kwargs):
    if not isinstance(instance, AuditedModel):
        return

    after = _field_values(instance)

    if created:
        changes = {field: {"from": None, "to": value} for field, value in after.items()}
        _write(instance, AuditAction.CREATE, changes)
        return

    before = getattr(instance, "_audit_before", None)
    if before is None:
        # Updated a row this process never saw created (e.g. loaded via
        # .update(), which bypasses save()/signals entirely) — nothing to
        # diff against, so there is nothing honest to write.
        return

    changes = {
        field: {"from": before.get(field), "to": value}
        for field, value in after.items()
        if before.get(field) != value
    }
    if not changes:
        return
    _write(instance, AuditAction.UPDATE, changes)


@receiver(post_delete)
def write_delete(sender, instance, **kwargs):
    if not isinstance(instance, AuditedModel):
        return
    changes = {
        field: {"from": value, "to": None} for field, value in _field_values(instance).items()
    }
    _write(instance, AuditAction.DELETE, changes)
