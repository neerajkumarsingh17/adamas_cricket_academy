from django.db import models

from apps.core.models import AuditedModel, EnquirySource
from apps.people.models import Gender, Person


class PlayingRole(models.TextChoices):
    BATSMAN = "batsman", "Batsman"
    BOWLER = "bowler", "Bowler"
    ALL_ROUNDER = "all_rounder", "All-rounder"
    WICKETKEEPER = "wicketkeeper", "Wicketkeeper"


class BattingStyle(models.TextChoices):
    """Not enumerated in docs/01-data-model.md (just "CharField(choices)") —
    standard cricket taxonomy, not a project-specific decision.
    """

    RIGHT_HANDED = "right_handed", "Right-handed"
    LEFT_HANDED = "left_handed", "Left-handed"


class BowlingStyle(models.TextChoices):
    """Not enumerated in docs/01-data-model.md — standard cricket taxonomy."""

    RIGHT_ARM_FAST = "right_arm_fast", "Right-arm fast"
    RIGHT_ARM_MEDIUM = "right_arm_medium", "Right-arm medium"
    RIGHT_ARM_OFFBREAK = "right_arm_offbreak", "Right-arm offbreak"
    RIGHT_ARM_LEGBREAK = "right_arm_legbreak", "Right-arm legbreak (leg spin)"
    LEFT_ARM_FAST = "left_arm_fast", "Left-arm fast"
    LEFT_ARM_MEDIUM = "left_arm_medium", "Left-arm medium"
    LEFT_ARM_ORTHODOX = "left_arm_orthodox", "Left-arm orthodox spin"
    LEFT_ARM_CHINAMAN = "left_arm_chinaman", "Left-arm chinaman (wrist spin)"
    NONE = "none", "Does not bowl"


class EnquiryStatus(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    TRIAL_SCHEDULED = "trial_scheduled", "Trial scheduled"
    CONVERTED = "converted", "Converted"
    NOT_INTERESTED = "not_interested", "Not interested"
    LOST = "lost", "Lost"


class FollowUpMode(models.TextChoices):
    CALL = "call", "Call"
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"
    VISIT = "visit", "Visit"


class Enquiry(AuditedModel):
    """docs/01-data-model.md section 5. The raw lead — `person` is null
    until `people.services.resolve_person()` is called on conversion.
    """

    enquiry_no = models.CharField(max_length=20, unique=True)
    person = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="enquiries"
    )

    student_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)

    guardian_name = models.CharField(max_length=200)
    guardian_mobile = models.CharField(max_length=15)
    guardian_email = models.EmailField(blank=True)

    address = models.CharField(max_length=255, blank=True)
    school = models.CharField(max_length=200, blank=True)
    class_grade = models.CharField(max_length=20, blank=True)

    cricket_experience = models.TextField(blank=True)
    playing_role = models.CharField(max_length=20, choices=PlayingRole.choices, blank=True)
    batting_style = models.CharField(max_length=20, choices=BattingStyle.choices, blank=True)
    bowling_style = models.CharField(max_length=20, choices=BowlingStyle.choices, blank=True)
    current_club = models.CharField(max_length=200, blank=True)
    residential_required = models.BooleanField(default=False)

    source = models.ForeignKey(EnquirySource, on_delete=models.PROTECT, related_name="enquiries")
    referred_by = models.CharField(max_length=200, blank=True)

    status = models.CharField(
        max_length=20, choices=EnquiryStatus.choices, default=EnquiryStatus.NEW
    )
    remarks = models.TextField(blank=True)

    owner = models.ForeignKey(
        "iam.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_enquiries",
    )

    def __str__(self) -> str:
        return f"{self.enquiry_no} — {self.student_name}"


class EnquiryFollowUp(AuditedModel):
    enquiry = models.ForeignKey(Enquiry, on_delete=models.CASCADE, related_name="follow_ups")
    contacted_on = models.DateTimeField()
    mode = models.CharField(max_length=10, choices=FollowUpMode.choices)
    notes = models.TextField(blank=True)
    next_action_on = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        "iam.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self) -> str:
        return f"Follow-up on {self.enquiry} ({self.contacted_on:%Y-%m-%d})"
