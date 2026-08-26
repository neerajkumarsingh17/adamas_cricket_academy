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

    class Meta:
        abstract = True
