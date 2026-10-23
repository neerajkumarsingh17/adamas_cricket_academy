import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.admissions.admission.models import Admission
from apps.core.models import AuditedModel, PaymentType
from apps.people.models import Person


class PaymentMode(models.TextChoices):
    UPI = "upi", "UPI"
    CASH = "cash", "Cash"
    CHEQUE = "cheque", "Cheque"
    ONLINE_TRANSFER = "online_transfer", "Online transfer"
    # Collected through the configured online payment gateway (desk
    # checkout or a payment link) — see apps.finance.payment.gateways.
    # The gateway's own payment id goes in reference_no.
    GATEWAY = "gateway", "Online (payment gateway)"


class AdmissionPayment(AuditedModel):
    """The one payment record a direct admission's fee step produces.
    `receipt_no` is minted once, from core.services.numbering's RCP series
    — an Idempotency-Key on the record-payment endpoint (Prompt D) is what
    stops a double-click minting two of these for the same admission.
    """

    admission = models.OneToOneField(Admission, on_delete=models.PROTECT, related_name="payment")
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
    # The gateway's payment id for an online payment; blank for cash.
    reference_no = models.CharField(max_length=100, blank=True)

    def clean(self):
        if self.payment_date and self.payment_date > datetime.date.today():
            raise ValidationError({"payment_date": "Cannot be in the future."})

    def __str__(self) -> str:
        return self.receipt_no


class OnlinePaymentKind(models.TextChoices):
    CHECKOUT = "checkout", "Paid at the desk"
    LINK = "link", "Payment link"


class OnlinePaymentStatus(models.TextChoices):
    CREATED = "created", "Awaiting payment"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class OnlinePayment(AuditedModel):
    """One attempt to collect a payment through the online payment gateway
    (settings.PAYMENT_GATEWAY) — a checkout opened at the desk, or a
    payment link sent to the payer. It is for exactly one of:

    - a direct admission's fee (`admission`) — once paid, the
      AdmissionPayment row above is created and verified;
    - a ledger payment (`person` + `payment_type` [+ `billing_period`]),
      e.g. a monthly coaching fee — once paid, a Payment row below is
      created and linked as `payment`.

    Several attempts can exist for the same thing (a closed window, a
    resent link); at most one is ever recorded. The gateway is the source
    of truth for whether money moved: `status` here is only ever advanced
    from what the gateway reports (signed checkout response, webhook, or a
    status fetch), never set by a user.
    """

    admission = models.ForeignKey(
        Admission,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="online_payments",
    )
    # Ledger payments: the Payment row to create once paid.
    person = models.ForeignKey(
        Person, on_delete=models.PROTECT, null=True, blank=True, related_name="online_payments"
    )
    payment_type = models.ForeignKey(
        PaymentType, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    billing_period = models.DateField(null=True, blank=True)
    payment = models.ForeignKey(
        "Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    kind = models.CharField(max_length=10, choices=OnlinePaymentKind.choices)
    # Which gateway this attempt went through ("razorpay", ...) — kept per
    # row so switching settings.PAYMENT_GATEWAY later never orphans an
    # attempt that is still open on the old one.
    gateway = models.CharField(max_length=20)
    # The gateway's own id for the checkout/link (e.g. order_... / plink_...).
    gateway_id = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=OnlinePaymentStatus.choices,
        default=OnlinePaymentStatus.CREATED,
        db_index=True,
    )
    short_url = models.URLField(blank=True)
    sent_to = models.CharField(max_length=16, blank=True)
    gateway_payment_id = models.CharField(max_length=64, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    # Something a person has to look at — e.g. the parent paid online
    # after the desk had already recorded a cash payment.
    note = models.TextField(blank=True)
    created_by = models.ForeignKey("iam.User", on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["gateway", "gateway_id"], name="unique_online_payment_gateway_id"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(admission__isnull=False, person__isnull=True)
                    | models.Q(
                        admission__isnull=True,
                        person__isnull=False,
                        payment_type__isnull=False,
                    )
                ),
                name="online_payment_for_admission_or_ledger",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.gateway}:{self.gateway_id}"


class PaymentLedgerStatus(models.TextChoices):
    CONFIRMED = "confirmed", "Confirmed"
    SETTLED = "settled", "Settled"
    VOID = "void", "Void"


class Payment(AuditedModel):
    """The unified payment ledger: every payment a Person makes, of every
    PaymentType (admission fee, monthly coaching fee, and any future
    category — master data, never a new table). Deliberately separate
    from AdmissionPayment above: that model is a `OneToOneField` gating
    the direct-admission wizard's own state machine
    (apps.admissions.admission.state's `_guard_payment_verified`,
    `hasattr(admission, "payment")`) and can't hold more than one row, so
    it can't represent recurring monthly rows — it is left untouched, and
    apps.finance.payment.services.admission_fee_paid() mirrors its one
    verified row into this ledger so the admission fee still appears
    here too.

    Two-stage paper trail: `confirmation_no` is minted the moment a
    payment is recorded (status defaults to CONFIRMED — "issued
    immediately when a payment is received"); `invoice_no` is minted
    later, only once settlement is confirmed (services.mark_settled).

    Scoped to Person, not Student (CLAUDE.md rule 1: one Person, one
    profile) — payment history then stays continuous across a
    withdrawal/re-admission instead of fragmenting across two Student
    rows for the same human.
    """

    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="payments")
    payment_type = models.ForeignKey(PaymentType, on_delete=models.PROTECT, related_name="+")
    # First of the billed month (e.g. 2026-01-01 for "January 2026").
    # Required only when payment_type.is_recurring — see clean(). A
    # DateField rather than separate month/year ints keeps range queries
    # ("is this person paid up for Jan 2026?") and the uniqueness
    # constraint below simple.
    billing_period = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices)
    # External reference — UTR, cheque number, gateway transaction id.
    # Unlike confirmation_no/invoice_no this is caller-supplied, not minted.
    reference_no = models.CharField(max_length=100, blank=True)
    payment_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=PaymentLedgerStatus.choices,
        default=PaymentLedgerStatus.CONFIRMED,
        db_index=True,
    )

    # Stage 1 — minted at creation by services.record_payment.
    confirmation_no = models.CharField(max_length=20, unique=True)
    confirmed_at = models.DateTimeField(auto_now_add=True)

    # Stage 2 — minted only once settlement is confirmed, by services.mark_settled.
    invoice_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    invoiced_at = models.DateTimeField(null=True, blank=True)

    recorded_by = models.ForeignKey("iam.User", on_delete=models.PROTECT, related_name="+")
    settled_by = models.ForeignKey(
        "iam.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    void_reason = models.TextField(blank=True)
    # The client's Idempotency-Key header, echoed back so a replayed
    # request (same key) can return this same row instead of minting a
    # second confirmation_no — see services.record_payment.
    idempotency_key = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        constraints = [
            # Only bites recurring types (billing_period set) — one row
            # per person+type+month, so the same month can't be paid/
            # logged twice. A one-off type's billing_period stays null
            # and is untouched by this (Postgres partial unique index,
            # same technique as apps.admissions.document's
            # owner_content_type+owner_object_id index).
            models.UniqueConstraint(
                fields=["person", "payment_type", "billing_period"],
                condition=models.Q(billing_period__isnull=False),
                name="unique_person_payment_type_period",
            ),
        ]

    def clean(self):
        errors: dict[str, str] = {}
        if self.payment_date and self.payment_date > datetime.date.today():
            errors["payment_date"] = "Cannot be in the future."
        if self.payment_type_id and self.payment_type.is_recurring and not self.billing_period:
            errors["billing_period"] = "Required for a recurring payment type."
        if self.billing_period and self.billing_period.day != 1:
            errors["billing_period"] = "Must be the first of the month."
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        period = f" ({self.billing_period:%B %Y})" if self.billing_period else ""
        return f"{self.confirmation_no}{period}"
