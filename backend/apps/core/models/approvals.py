from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .base import AuditedModel


class ApprovalRule(AuditedModel):
    """Which role is required to decide a given (module, action) kind of
    approval. docs/01-data-model.md section 4. `required_role` is a string
    reference to apps.iam.Role — core imports nothing from apps/
    (docs/00-project-structure.md).
    """

    module = models.SlugField(max_length=50)
    action = models.SlugField(max_length=50)
    required_role = models.ForeignKey(
        "iam.Role", on_delete=models.PROTECT, related_name="approval_rules"
    )
    threshold = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["module", "action"], name="unique_approval_rule"),
        ]

    def __str__(self) -> str:
        return f"{self.module}:{self.action} -> {self.required_role_id}"


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ApprovalRequest(AuditedModel):
    """A single decision-in-progress, generically pointing at whatever
    model raised it (Admission, TrialRegistration, Student, ...). Reused
    as-is by every future approval flow — see apps.core.services.approvals.
    """

    rule = models.ForeignKey(ApprovalRule, on_delete=models.PROTECT, related_name="requests")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    subject = GenericForeignKey("content_type", "object_id")

    requested_by = models.ForeignKey(
        "iam.User", on_delete=models.PROTECT, related_name="approval_requests_made"
    )
    status = models.CharField(
        max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    decided_by = models.ForeignKey(
        "iam.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approval_requests_decided",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self) -> str:
        return f"ApprovalRequest({self.rule_id}, {self.status})"
