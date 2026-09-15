from django.db import models

from apps.admissions.student.models import Student
from apps.core.models import AuditedModel


class IDCardStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    REPLACED = "replaced", "Replaced"
    EXPIRED = "expired", "Expired"
    LOST = "lost", "Lost"


class IDCard(AuditedModel):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="id_cards")
    card_no = models.CharField(max_length=30, unique=True)
    issued_on = models.DateField()
    valid_until = models.DateField()
    qr_payload = models.TextField()
    status = models.CharField(
        max_length=20, choices=IDCardStatus.choices, default=IDCardStatus.ACTIVE
    )
    replaces = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replaced_by"
    )
    issued_by = models.ForeignKey(
        "iam.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self) -> str:
        return self.card_no
