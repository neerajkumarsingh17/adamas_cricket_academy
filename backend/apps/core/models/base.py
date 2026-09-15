import uuid

from django.db import models


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditedModel(TimeStampedModel):
    """Inherit this to get field-level diffs written to AuditLog automatically.

    This is the marker only — apps.audit's middleware does the actual diff
    capture and the write (CLAUDE.md rule 4). Adds no fields of its own.
    """

    # Not a model field (no models.Field instance -> no column/migration) —
    # a plain per-instance scratch attribute apps.audit.signals.
    # capture_before() stashes the pre-save row on, so mypy knows about it.
    _audit_before: dict | None = None

    class Meta:
        abstract = True
