from django.db import models
from django.db.models.query import QuerySet


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    READ = "read", "Read"
    EXPORT = "export", "Export"
    LOGIN = "login", "Login"
    APPROVE = "approve", "Approve"


class _AppendOnlyQuerySet(QuerySet):
    """Blocks `.update()` and `.delete()` at the ORM layer.

    This is the enforcement that's actually reachable from this codebase.
    The database-grant enforcement docs/01-data-model.md section 3
    describes (`REVOKE UPDATE, DELETE`) is also applied — see migration
    0002 — but it only bites in an environment where the application
    connects as a role that does *not* own this table. In this project's
    single-role local/dev setup the connecting role created the table via
    migrations and therefore owns it, and PostgreSQL lets an owner bypass
    its own REVOKEs — so the SQL grant alone would be a false sense of
    security here. Provisioning a separate, non-owning runtime role is a
    staging/production infra task, out of this session's scope; flagging
    it rather than presenting the migration as sufficient on its own.
    """

    def update(self, **kwargs):
        raise TypeError("AuditLog rows are append-only — UPDATE is not permitted.")

    def delete(self):
        raise TypeError("AuditLog rows are append-only — DELETE is not permitted.")


class AuditLog(models.Model):
    """docs/01-data-model.md section 3. Append-only — see
    `_AppendOnlyQuerySet` above and migration 0002
    (CLAUDE.md rule 4: "Never add an UPDATE or DELETE path to AuditLog").

    Not a TimeStampedModel/AuditedModel: it must never be audited itself
    (infinite regress), and `updated_at` would imply rows can change.
    """

    id = models.BigAutoField(primary_key=True)
    actor = models.ForeignKey(
        "iam.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Null for system actions (Celery beat, migrations).",
    )
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    model_label = models.CharField(max_length=150, help_text="app_label.ModelName")
    object_id = models.CharField(max_length=64)
    changes = models.JSONField(default=dict, blank=True, help_text='{field: {"from": x, "to": y}}')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=36, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = _AppendOnlyQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["model_label", "object_id"]),
            models.Index(fields=["actor", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action}:{self.model_label}#{self.object_id} @ {self.created_at}"

    def save(self, *args, **kwargs):
        if self.pk is not None and AuditLog.objects.filter(pk=self.pk).exists():
            raise TypeError(
                "AuditLog rows are append-only — re-saving an existing row is not permitted."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("AuditLog rows are append-only — DELETE is not permitted.")
