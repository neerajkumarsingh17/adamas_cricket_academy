import datetime

from django.core.exceptions import ValidationError
from django.db import models

from apps.admissions.admission.models import Admission
from apps.core.models import AuditedModel


class PaymentMode(models.TextChoices):
    UPI = "upi", "UPI"
    CASH = "cash", "Cash"
    CHEQUE = "cheque", "Cheque"
    ONLINE_TRANSFER = "online_transfer", "Online transfer"


class AdmissionPayment(AuditedModel):
    """The one payment record a direct admission's fee step produces.
    `receipt_no` is minted once, from core.services.numbering's RCP series
    — an Idempotency-Key on the record-payment endpoint (Prompt D) is what
    stops a double-click minting two of these for the same admission.
    """

    admission = models.OneToOneField(
        Admission, on_delete=models.PROTECT, related_name="payment"
    )
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices)
    receipt_no = models.CharField(max_length=20, unique=True)
    payment_date = models.DateField()
    recorded_by = models.ForeignKey("iam.User", on_delete=models.PROTECT, related_name="+")
    verified_by = models.ForeignKey(
        "iam.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_note = models.TextField(blank=True)
    # The client's Idempotency-Key header, echoed back so a replayed
    # request (same key) can return this same row instead of minting a
    # second receipt_no — see services.record_direct_payment.
    idempotency_key = models.CharField(max_length=255, blank=True, db_index=True)

    def clean(self):
        if self.payment_date and self.payment_date > datetime.date.today():
            raise ValidationError({"payment_date": "Cannot be in the future."})

    def __str__(self) -> str:
        return self.receipt_no
