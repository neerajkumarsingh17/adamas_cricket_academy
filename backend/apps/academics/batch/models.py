"""docs/00-project-structure.md's academics/batch app (M08). Coach and
TrainingSession live here too, alongside Batch/BatchEnrollment — a
deliberate fold of the doc's original three-app sketch (batch/, training/,
coach/) into this one app, per the actual build instruction.
"""

from django.db import models

from apps.admissions.student.models import Student
from apps.core.models import AgeCategory, AuditedModel, TrainingType, Venue
from apps.people.models import Staff


class Coach(AuditedModel):
    """A Staff member's coaching-specific attributes. Deliberately no
    name/mobile/any identity field here (CLAUDE.md rule 2, "enter once")
    — `staff.person` already has all of that.
    """

    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name="coach")
    specialisation = models.CharField(max_length=100, blank=True)
    qualification = models.CharField(max_length=150, blank=True)
    experience_years = models.PositiveSmallIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    def __str__(self) -> str:
        return str(self.staff)


class Batch(AuditedModel):
    name = models.CharField(max_length=100)
    age_category = models.ForeignKey(AgeCategory, on_delete=models.PROTECT, related_name="batches")
    coach = models.ForeignKey(Coach, on_delete=models.PROTECT, related_name="batches")
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="batches")
    capacity = models.PositiveSmallIntegerField()
    # Comma-separated ISO weekday numbers (1=Monday .. 7=Sunday), e.g.
    # "1,3,5" — a plain CSV field per spec, not a relation or JSON column.
    weekdays = models.CharField(max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    # A residential (boarding) student on this batch pays this instead of
    # monthly_fee — apps.admissions.student.Student.residential decides
    # which of the two a given student's payment defaults to (see
    # apps.finance.payment's record-payment auto-fill). Always set,
    # same as monthly_fee — not null=True, so "residential enrolment
    # exists but nobody priced it" can't happen silently.
    residential_monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class BatchEnrollment(AuditedModel):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="batch_enrollments")
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="enrollments")
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # A database constraint, not an if-check — two active
            # enrolments for the same student means two monthly fees.
            models.UniqueConstraint(
                fields=["student"],
                condition=models.Q(is_active=True),
                name="unique_active_enrollment_per_student",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} in {self.batch}"


class TrainingSession(AuditedModel):
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="sessions")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    # May differ from batch.coach — a substitute taking this one session.
    coach = models.ForeignKey(Coach, on_delete=models.PROTECT, related_name="sessions_conducted")
    # FK to core.TrainingType (master data, already seeded with Batting/
    # Bowling/Fielding/Fitness & Conditioning/Match Practice) rather than
    # a hardcoded TextChoices field, per CLAUDE.md rule 3 — a training
    # type is exactly the kind of thing a Head Coach adds without a
    # release, same reasoning as AssessmentCriterion.
    #
    # Nullable: services.generate_sessions() creates placeholder rows for
    # a batch's regular weekly slots before anyone has decided that day's
    # lesson focus — a coach sets this when actually planning the session.
    training_type = models.ForeignKey(
        TrainingType, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    objective = models.TextField(blank=True)
    is_conducted = models.BooleanField(default=False)
    cancel_reason = models.TextField(blank=True)
    report = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["batch", "date"], name="unique_batch_date_session"),
        ]

    def __str__(self) -> str:
        return f"{self.batch} — {self.date}"
