from django.core.validators import MinValueValidator
from django.db import models

from apps.admissions.admission.models import Admission
from apps.core.models import AuditedModel, FeeHead


class AdmissionFeeLine(AuditedModel):
    """One row per FeeHead collected at a direct admission's desk. The
    total is never stored here or on Admission — Admission.fee_total sums
    these live, so it can never disagree with what these lines actually
    say (docs: "a stored total that disagrees with its lines is the
    classic reconciliation bug").
    """

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="fee_lines")
    fee_head = models.ForeignKey(FeeHead, on_delete=models.PROTECT, related_name="+")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["admission", "fee_head"], name="unique_admission_fee_head"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.admission}: {self.fee_head} = {self.amount}"
