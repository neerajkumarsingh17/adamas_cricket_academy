from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import AuditedModel, DocumentType


class DocumentStatus(models.TextChoices):
    """docs/04-state-machines.md section 4."""

    PENDING = "pending", "Pending"
    SUBMITTED = "submitted", "Submitted"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"


class Document(AuditedModel):
    """docs/01-data-model.md section 4. Owner is generic — Person, Student,
    Staff or Admission can all hold documents (docs/01-data-model.md §1:
    `Person.photograph`; §5: `AdmissionChecklistItem.document`).

    Upload flow is presigned S3 (CLAUDE.md: never proxy a file through the
    API server) — `s3_key` etc. are just columns here, no upload logic.
    """

    document_type = models.ForeignKey(
        DocumentType, on_delete=models.PROTECT, related_name="documents"
    )

    owner_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    owner_object_id = models.UUIDField()
    owner = GenericForeignKey("owner_content_type", "owner_object_id")

    s3_key = models.CharField(max_length=500, unique=True)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()

    status = models.CharField(
        max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.PENDING
    )
    verified_by = models.ForeignKey(
        "iam.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    expires_on = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["owner_content_type", "owner_object_id"])]

    def __str__(self) -> str:
        return f"{self.document_type}: {self.original_filename}"


class DocumentVersion(AuditedModel):
    """Named in the docs/01-data-model.md section 4 heading
    ("Document / DocumentType / DocumentVersion") but never given a field
    spec anywhere in the docs, and docs/04-state-machines.md section 4's
    lifecycle table shows re-uploads transitioning the *same* `Document`
    row in place (`rejected -> submitted`, `expired -> submitted`), with no
    mention of retained history.

    This is a best-effort inference, not a transcription: a snapshot of
    `Document`'s own storage fields, one row per prior upload, so a
    verifier can see what was rejected. Flagged for confirmation — delete
    this model if re-uploads are meant to simply overwrite `Document`
    with no history kept.
    """

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_no = models.PositiveSmallIntegerField()
    s3_key = models.CharField(max_length=500)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    uploaded_by = models.ForeignKey(
        "iam.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_no"], name="unique_document_version_no"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document} v{self.version_no}"
