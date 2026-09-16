from django.db import models

from apps.admissions.enquiry.models import Enquiry
from apps.core.models import AgeCategory, AssessmentCriterion, AuditedModel, Venue
from apps.people.models import Person, Staff


class PaymentStatus(models.TextChoices):
    NOT_APPLICABLE = "not_applicable", "Not applicable"
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    WAIVED = "waived", "Waived"


class TrialOutcome(models.TextChoices):
    SELECTED = "selected", "Selected"
    SHORTLISTED = "shortlisted", "Shortlisted"
    WAITLISTED = "waitlisted", "Waitlisted"
    NOT_SELECTED = "not_selected", "Not selected"
    RE_TRIAL = "re_trial", "Re-trial"


class TrialSlot(AuditedModel):
    date = models.DateField()
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="trial_slots")
    reporting_time = models.TimeField()
    age_category = models.ForeignKey(
        AgeCategory, on_delete=models.PROTECT, related_name="trial_slots"
    )
    capacity = models.PositiveSmallIntegerField()
    booked_count = models.PositiveSmallIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.date} {self.reporting_time} — {self.venue} ({self.age_category})"


class TrialRegistration(AuditedModel):
    """docs/01-data-model.md section 5. `trial_id` is generated —
    core.services.numbering wiring lands with the business logic, not here.
    """

    trial_id = models.CharField(max_length=20, unique=True)
    enquiry = models.ForeignKey(
        Enquiry, on_delete=models.PROTECT, related_name="trial_registrations"
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trial_registrations",
    )
    slot = models.ForeignKey(TrialSlot, on_delete=models.PROTECT, related_name="registrations")
    trial_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.NOT_APPLICABLE
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    attended = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.trial_id


class TrialAssessment(AuditedModel):
    registration = models.OneToOneField(
        TrialRegistration, on_delete=models.CASCADE, related_name="assessment"
    )
    assessed_by = models.ForeignKey(
        Staff, on_delete=models.PROTECT, related_name="trial_assessments"
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    overall_remarks = models.TextField(blank=True)
    is_locked = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Assessment for {self.registration}"


class TrialAssessmentScore(AuditedModel):
    assessment = models.ForeignKey(TrialAssessment, on_delete=models.CASCADE, related_name="scores")
    criterion = models.ForeignKey(AssessmentCriterion, on_delete=models.PROTECT)
    score = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "criterion"], name="unique_assessment_criterion_score"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.assessment}: {self.criterion} = {self.score}"


class TrialResult(AuditedModel):
    registration = models.OneToOneField(
        TrialRegistration, on_delete=models.CASCADE, related_name="result"
    )
    # Filtered directly by TrialRegistrationFilter's outcome= param
    # (docs/02-api-spec.md's "Filters: slot, date, outcome") on every trial
    # results listing.
    outcome = models.CharField(max_length=20, choices=TrialOutcome.choices, db_index=True)
    declared_by = models.ForeignKey(
        "iam.User", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    declared_at = models.DateTimeField(null=True, blank=True)
    review_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.registration}: {self.outcome}"
