"""docs/01-data-model.md section 4, Master data (plus DocumentType and
AssessmentCriterion, which the doc defines elsewhere but which
docs/02-api-spec.md groups under the same /master/ endpoints, and
docs/01 section 5 explicitly labels AssessmentCriterion "(master data)").

All editable through Django admin by Administration. Nothing on this list
may ever be hardcoded elsewhere in the codebase — code that needs "the
enquiry sources" or "the document types" queries these tables.
"""

from django.db import models

from .base import AuditedModel


class Programme(AuditedModel):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class AgeCategory(AuditedModel):
    """min_age/max_age in completed years; as_on_date_rule is the yearly
    cutoff used to compute a player's age for category purposes, stored as
    "MM-DD" (e.g. "09-01" for September 1st) rather than a fixed date,
    since the same cutoff recurs every season.
    """

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    min_age = models.PositiveSmallIntegerField()
    max_age = models.PositiveSmallIntegerField()
    as_on_date_rule = models.CharField(max_length=5, help_text='Cutoff as "MM-DD", e.g. "09-01".')
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Venue(AuditedModel):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Season(AuditedModel):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    # The direct-admission intake snapshots AgeCategory against this date
    # (core.services.age.category_for), not against AgeCategory's own
    # recurring "MM-DD" as_on_date_rule — a seat is sold against a specific
    # season's cutoff, and that has to stay fixed even if a future season
    # later moves its own cutoff to a different day.
    age_cutoff_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class EnquirySource(AuditedModel):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class TrainingType(AuditedModel):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class DocumentApplicability(models.TextChoices):
    PERSON = "person", "Person"
    STUDENT = "student", "Student"
    STAFF = "staff", "Staff"
    ADMISSION = "admission", "Admission"


class DocumentRequiredStage(models.TextChoices):
    """When a document is chased, for the direct-admission wizard's three
    document fieldsets — orthogonal to `applies_to` (which owner kind a
    type is for) and to the pre-existing `is_mandatory_default`. Blank for
    every DocumentType this doesn't apply to (person/student/staff types
    predating this feature).
    """

    AT_ADMISSION = "at_admission", "At admission"
    BEFORE_FIRST_SESSION = "before_first_session", "Before first session"
    PROFILE_COMPLETION = "profile_completion", "Profile completion"


class DocumentType(AuditedModel):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_mandatory_default = models.BooleanField(default=False)
    has_expiry = models.BooleanField(default=False)
    applies_to = models.CharField(max_length=10, choices=DocumentApplicability.choices)
    required_stage = models.CharField(
        max_length=20, choices=DocumentRequiredStage.choices, blank=True
    )

    def __str__(self) -> str:
        return self.name


class AssessmentCriterionGroup(models.TextChoices):
    BATTING = "batting", "Batting"
    BOWLING = "bowling", "Bowling"
    FIELDING = "fielding", "Fielding"
    WICKETKEEPING = "wicketkeeping", "Wicketkeeping"
    FITNESS = "fitness", "Fitness"
    GAME_AWARENESS = "game_awareness", "Game Awareness"
    DISCIPLINE = "discipline", "Discipline"
    ATTITUDE = "attitude", "Attitude"
    POTENTIAL = "potential", "Potential"


class AssessmentCriterion(AuditedModel):
    """The nine SOP §8 dimensions are seed data, not model fields — the
    Head Coach changes them without a release (docs/01-data-model.md
    section 5).
    """

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    group = models.CharField(max_length=20, choices=AssessmentCriterionGroup.choices)
    scale_min = models.DecimalField(max_digits=5, decimal_places=2)
    scale_max = models.DecimalField(max_digits=5, decimal_places=2)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class FeeApplicability(models.TextChoices):
    RESIDENTIAL = "residential", "Residential"
    NON_RESIDENTIAL = "non_residential", "Non-residential"
    BOTH = "both", "Both"


class FeeHead(AuditedModel):
    """The direct-admission wizard renders its fee-collection fieldset from
    this table, one number input per row — never a hardcoded list, so
    adding or retiring a fee head changes the form without a release.
    """

    code = models.SlugField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    is_mandatory = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    applies_to = models.CharField(
        max_length=16, choices=FeeApplicability.choices, default=FeeApplicability.BOTH
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "code"]

    def __str__(self) -> str:
        return self.label


class ConsentType(AuditedModel):
    """`version` lives here, not just as a free-floating string, so that
    `ConsentRecord.version` (copied at grant time) can be compared back
    against "what does this type currently say" — re-wording a consent's
    `body_text` next season bumps `version` and never retroactively changes
    what an already-granted record is taken to mean.
    """

    code = models.SlugField(max_length=50, unique=True)
    label = models.CharField(max_length=150)
    body_text = models.TextField()
    version = models.CharField(max_length=20)
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.label
