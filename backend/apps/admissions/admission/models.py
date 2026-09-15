import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Sum

from apps.admissions.enquiry.models import Enquiry, PlayingRole
from apps.admissions.trial.models import PaymentStatus, TrialRegistration
from apps.core.models import AgeCategory, AuditedModel, ConsentType, DocumentType, Programme, Season
from apps.people.models import Gender, Person, Relationship


class AdmissionStep(models.TextChoices):
    """docs/04-state-machines.md section 1 — the 7 persisted states shared
    with the trial-based chain, plus the direct-admission-only states added
    for the fee-first path (see DirectAdmissionStateMachine, state.py).
    `DRAFT`, `DOCUMENTS_PENDING` and `APPROVED` are shared by both chains —
    which transitions are legal from a given value depends on which state
    machine (and therefore which `Admission.source`) is asking.
    """

    DRAFT = "draft", "Draft"
    DOCUMENTS_PENDING = "documents_pending", "Documents pending"
    DOCUMENTS_VERIFIED = "documents_verified", "Documents verified"
    FEE_PENDING = "fee_pending", "Fee pending"
    FEE_CLEARED = "fee_cleared", "Fee cleared"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    # Direct-admission-only, from here down.
    PAYMENT_RECORDED = "payment_recorded", "Payment recorded"
    PAYMENT_VERIFIED = "payment_verified", "Payment verified"
    DOCUMENTS_REJECTED = "documents_rejected", "Documents rejected"
    READY_FOR_APPROVAL = "ready_for_approval", "Ready for approval"
    CANCELLED = "cancelled", "Cancelled"


class AdmissionSource(models.TextChoices):
    ENQUIRY = "enquiry", "Enquiry"
    DIRECT = "direct", "Direct"


class PaymentMethod(models.TextChoices):
    """How a manually-recorded fee payment was actually collected. The
    Phase 1 fee stub (docs/02-api-spec.md: "{reference, amount} or
    {waiver_reason}") never named a collection method — added on explicit
    request so Accounts/Administration can record *how* money came in
    (UPI/card/cash), not just that it did. Real gateway integration
    (Razorpay/PayU, per the phase plan) is Phase 3; this stays manual.
    """

    UPI = "upi", "UPI"
    CARD = "card", "Card"
    CASH = "cash", "Cash"


class ChecklistItemStatus(models.TextChoices):
    """Mirrors document.Document.status (docs/01-data-model.md section 5)."""

    PENDING = "pending", "Pending"
    SUBMITTED = "submitted", "Submitted"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"


class Admission(AuditedModel):
    application_no = models.CharField(max_length=20, unique=True)
    source = models.CharField(
        max_length=10, choices=AdmissionSource.choices, default=AdmissionSource.ENQUIRY
    )
    # Nullable only for source=DIRECT: a direct admission has no Person at
    # all until approve_admission() resolves or creates one from its
    # AdmissionIntake — see apps.admissions.student.services. Every
    # source=ENQUIRY row still gets one immediately, same as always.
    person = models.ForeignKey(
        Person, on_delete=models.PROTECT, null=True, blank=True, related_name="admissions"
    )
    enquiry = models.ForeignKey(
        Enquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name="admissions"
    )
    trial_registration = models.ForeignKey(
        TrialRegistration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admissions",
    )
    # Nullable for the same reason as `person` — a direct admission has no
    # programme until its AdmissionIntake exists; source=ENQUIRY rows still
    # require one at open time, enforced in the service layer.
    programme = models.ForeignKey(
        Programme, on_delete=models.PROTECT, null=True, blank=True, related_name="admissions"
    )
    residential = models.BooleanField(default=False)
    step = models.CharField(
        max_length=20, choices=AdmissionStep.choices, default=AdmissionStep.DRAFT
    )

    # Renamed from `trial_waiver_reason` — there is no trial to waive on a
    # direct admission, there never was one. Required (service-layer, same
    # as before) only when source=DIRECT; this is T-607's traceability
    # record — "reputation/referral admissions are traceable, not
    # disguised" — carried forward into the new design.
    direct_admission_reason = models.TextField(blank=True)

    fee_payment_reference = models.CharField(max_length=100, blank=True)
    fee_payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    fee_payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, blank=True)
    # docs/02-api-spec.md's own payload for this stub is "{reference,
    # amount}" — `amount` was accepted by the serializer and threaded
    # through services.record_payment() from the start, but never actually
    # had a column to land in, so it was silently discarded. CLAUDE.md's
    # money convention: Decimal, name ends `_amount`. Null (not 0) when
    # nothing's been recorded yet or the fee was waived — a real payment of
    # ₹0 and "no amount recorded" are different facts worth being able to
    # tell apart.
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    approved_by = models.ForeignKey(
        "iam.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(blank=True)
    # CANCELLED is distinct from REJECTED: rejection is a documents/fee
    # gate failing a verification check; cancellation is the candidate (or
    # the desk) walking away before approval, for any reason at all.
    # A payment already recorded on a cancelled admission is never deleted.
    cancelled_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(source=AdmissionSource.ENQUIRY, enquiry__isnull=False)
                    | models.Q(
                        source=AdmissionSource.DIRECT,
                        enquiry__isnull=True,
                        trial_registration__isnull=True,
                    )
                ),
                name="admission_source_matches_enquiry_and_trial",
            ),
        ]

    def __str__(self) -> str:
        return self.application_no

    @property
    def fee_total(self) -> Decimal:
        # Never a stored column — see apps.finance.fee.models.AdmissionFeeLine's
        # docstring. Aggregate returns None on an empty queryset; a decimal
        # zero, not None, is the correct "nothing collected yet" value.
        return self.fee_lines.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    @property
    def fee_total_in_words(self) -> str:
        from apps.core.services.money import amount_in_words

        return amount_in_words(self.fee_total)


class AdmissionChecklistItem(AuditedModel):
    admission = models.ForeignKey(
        Admission, on_delete=models.CASCADE, related_name="checklist_items"
    )
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    is_mandatory = models.BooleanField(default=True)
    document = models.ForeignKey(
        "document.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checklist_items",
    )
    status = models.CharField(
        max_length=20, choices=ChecklistItemStatus.choices, default=ChecklistItemStatus.PENDING
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["admission", "document_type"], name="unique_admission_document_type"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.admission}: {self.document_type}"


_PIN_CODE_VALIDATOR = RegexValidator(
    r"^[1-9][0-9]{5}$", "Enter a valid 6-digit PIN code."
)


class AdmissionCategory(models.TextChoices):
    RESIDENTIAL = "residential", "Residential"
    NON_RESIDENTIAL = "non_residential", "Non-residential"


class DaysPerWeek(models.IntegerChoices):
    TWO = 2, "2 days a week"
    THREE = 3, "3 days a week"


class PreferredSlot(models.TextChoices):
    MORNING = "morning", "Morning"
    EVENING = "evening", "Evening"


class AdmissionIntake(AuditedModel):
    """What the desk captures before a Person exists — the 24 fields, no
    more (see the module docstring in services.py for the boundary against
    profile completion's 33 deferred fields). One-to-one with a
    source=DIRECT `Admission`; a source=ENQUIRY admission never gets one —
    its data already flowed in from the enquiry/trial chain.
    """

    admission = models.OneToOneField(Admission, on_delete=models.CASCADE, related_name="intake")

    # Seat
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="+")
    admission_category = models.CharField(max_length=16, choices=AdmissionCategory.choices)
    days_per_week = models.SmallIntegerField(choices=DaysPerWeek.choices, null=True, blank=True)
    preferred_slot = models.CharField(
        max_length=10, choices=PreferredSlot.choices, blank=True
    )

    # Student
    full_name = models.CharField(max_length=120)
    date_of_birth = models.DateField()
    # Snapshot, not computed on read — see core.services.age.category_for's
    # docstring. Never accepted as API input; set in save() below.
    age_category = models.ForeignKey(AgeCategory, on_delete=models.PROTECT, related_name="+")
    gender = models.CharField(max_length=1, choices=Gender.choices)
    playing_role = models.CharField(max_length=20, choices=PlayingRole.choices, blank=True)

    # Contact
    present_address = models.TextField()
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pin_code = models.CharField(max_length=6, validators=[_PIN_CODE_VALIDATOR])
    student_mobile = models.CharField(max_length=16, blank=True)
    guardian_name = models.CharField(max_length=120)
    guardian_relationship = models.CharField(max_length=20, choices=Relationship.choices)
    guardian_mobile = models.CharField(max_length=16)
    # Nullable only for migration safety on rows created before this field
    # existed — required by clean() below for every new/edited intake.
    # Without it, approve_admission() can't create a Person for a
    # first-time guardian (Person.date_of_birth/gender are required,
    # non-nullable) and dead-ends on "register the guardian first", which
    # defeats the whole point of a walk-in admission with no prior record.
    guardian_date_of_birth = models.DateField(null=True, blank=True)
    guardian_gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    emergency_contact = models.CharField(max_length=16)

    # Residential-only
    local_guardian_name = models.CharField(max_length=120, blank=True)
    local_guardian_mobile = models.CharField(max_length=16, blank=True)

    def clean(self):
        errors: dict[str, str] = {}
        is_residential = self.admission_category == AdmissionCategory.RESIDENTIAL

        if is_residential:
            if self.days_per_week or self.preferred_slot:
                errors["days_per_week"] = "Not applicable — this seat is residential."
            if not self.local_guardian_name or not self.local_guardian_mobile:
                errors["local_guardian_name"] = "Required for a residential seat."
        else:
            if not self.days_per_week or not self.preferred_slot:
                errors["days_per_week"] = "Required for a non-residential seat."
            if self.local_guardian_name or self.local_guardian_mobile:
                errors["local_guardian_name"] = "Not applicable — this seat is non-residential."

        if self.guardian_mobile and self.emergency_contact == self.guardian_mobile:
            errors["emergency_contact"] = (
                "Must be someone other than the guardian above."
            )
        if self.student_mobile and self.student_mobile == self.guardian_mobile:
            errors["student_mobile"] = "Must be different from the guardian's mobile."

        if not self.guardian_date_of_birth:
            errors["guardian_date_of_birth"] = "Required."
        elif self.guardian_date_of_birth >= datetime.date.today():
            errors["guardian_date_of_birth"] = "Must be in the past."
        if not self.guardian_gender:
            errors["guardian_gender"] = "Required."

        if self.date_of_birth:
            if self.date_of_birth >= datetime.date.today():
                errors["date_of_birth"] = "Must be in the past."
            else:
                from apps.core.services.age import age_in_completed_years

                as_on = self.season.age_cutoff_date if self.season_id else datetime.date.today()
                age = age_in_completed_years(self.date_of_birth, as_on or datetime.date.today())
                if not (5 <= age <= 45):
                    errors["date_of_birth"] = "Age must be between 5 and 45."

        if errors:
            raise DjangoValidationError(errors)

    def save(self, *args, **kwargs):
        # clean()'s business-rule checks are the caller's responsibility to
        # run first (the serializer, same as every other write path in
        # this codebase) — this only ever computes the one thing that must
        # never come from the caller.
        from apps.core.services.age import category_for

        self.age_category = category_for(self.date_of_birth, self.season)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Intake for {self.admission}"


class ConsentRecord(AuditedModel):
    """One row per ConsentType a guardian has decided on for this
    admission — MEDIA_USE included even when refused (`granted=False`),
    since a missing row and an explicit refusal are different facts (the
    service layer, not this model, enforces that distinction — see
    services.py's consent rules).

    `version` is copied from ConsentType.version at grant time, not looked
    up live — re-wording a consent's body_text next season must never
    retroactively change what an already-granted record is taken to mean.
    """

    admission = models.ForeignKey(
        Admission, on_delete=models.CASCADE, related_name="consent_records"
    )
    consent_type = models.ForeignKey(ConsentType, on_delete=models.PROTECT, related_name="+")
    granted = models.BooleanField()
    version = models.CharField(max_length=20)
    granted_at = models.DateTimeField()
    granted_ip = models.GenericIPAddressField(null=True, blank=True)
    declared_by_name = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["admission", "consent_type"], name="unique_admission_consent_type"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.admission}: {self.consent_type} ({'granted' if self.granted else 'refused'})"
