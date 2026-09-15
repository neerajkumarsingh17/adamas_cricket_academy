from django.db import models

from apps.admissions.admission.models import Admission
from apps.core.models import ApprovalRequest, AuditedModel, Programme
from apps.people.models import Person


class StudentStatus(models.TextChoices):
    """docs/04-state-machines.md section 2 — all 11 SOP §11 statuses.

    `enquiry` and `trial` are conceptually pre-student (held on Enquiry and
    TrialRegistration respectively) and in practice are never written to
    this field, but the doc names them as part of the same status space,
    so they're transcribed here rather than silently dropped.
    """

    ENQUIRY = "enquiry", "Enquiry"
    TRIAL = "trial", "Trial"
    SELECTED = "selected", "Selected"
    ADMISSION_PENDING = "admission_pending", "Admission pending"
    ACTIVE = "active", "Active"
    MEDICAL_HOLD = "medical_hold", "Medical hold"
    FEE_HOLD = "fee_hold", "Fee hold"
    LEAVE = "leave", "Leave"
    SUSPENDED = "suspended", "Suspended"
    WITHDRAWN = "withdrawn", "Withdrawn"
    COMPLETED = "completed", "Completed"


class Student(AuditedModel):
    """docs/01-data-model.md section 5. Created once per admission —
    `person` is reused (not the `Student` row itself) on re-admission.

    `person` is a plain FK, not the O2O docs/01-data-model.md section 5
    literally specifies. That doc and docs/04-state-machines.md section 5
    contradict each other: section 5 there is explicit that re-admission
    creates "a **new** `Student` row ... against the **same** `Person`,
    with the prior `Student` record retained" — which is only possible if
    one `Person` can have more than one `Student` row over time. An O2O
    would make that a database-level impossibility, silently breaking the
    one behaviour SOP §67 exists for. Resolving in favour of the state
    machine doc, since it describes the actual required behaviour rather
    than summarising cardinality; flagging here since data-model docs say
    changes to this file land in the same commit as the code.
    """

    student_code = models.CharField(max_length=20, unique=True)
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="students")
    admission = models.ForeignKey(Admission, on_delete=models.PROTECT, related_name="students")
    admission_date = models.DateField()
    # Nullable for a direct admission: the wizard collects a season and a
    # residential/non-residential category, not a Programme — batch
    # allotment (and the Programme that implies) happens afterward, by the
    # Head Coach. Every enquiry/trial-based Student still gets one at
    # creation time, same as always.
    programme = models.ForeignKey(
        Programme, on_delete=models.PROTECT, null=True, blank=True, related_name="students"
    )
    residential = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=StudentStatus.choices, default=StudentStatus.ACTIVE
    )
    withdrawn_on = models.DateField(null=True, blank=True)
    completed_on = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return self.student_code


class StudentProfile(AuditedModel):
    """The 33-field offline form's deferred half (Prompt G) — chased only
    once, after the student record exists, never re-collected from the
    direct-admission wizard (CLAUDE.md rule 2). Scoped here to what the
    student/parent portal actually captures: the three coach-assessed
    fields (highest_level_played, batting_style, bowling_style) and the
    three office-assigned fields (registration_no — already `student_
    code`, batch_allotted, coach_assigned) route to the coach's assessment
    screen and Head Coach batch allotment respectively, neither of which
    exists yet — not modelled here to avoid dead, unexposed columns ahead
    of that work.

    `blood_group` and `student_email` aren't here either — both already
    exist on `Person` (`blood_group`, `email`), captured once there rather
    than duplicated onto a second record for the same human being.
    """

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="profile")

    # Personal
    nationality = models.CharField(max_length=100, blank=True)
    # Optional and stays optional — the Aadhaar *copy* is already on file
    # from admission; this number is collected only if something actually
    # demands it, never chased (docs/05-build-sequence.md Prompt G).
    aadhaar_number = models.CharField(max_length=20, blank=True)
    permanent_address = models.TextField(blank=True)

    # Guardian
    occupation = models.CharField(max_length=100, blank=True)
    annual_income = models.CharField(max_length=100, blank=True)
    guardian_email = models.EmailField(blank=True)
    second_guardian = models.TextField(blank=True)

    # Academic
    school_name = models.CharField(max_length=150, blank=True)
    board = models.CharField(max_length=100, blank=True)
    class_or_course = models.CharField(max_length=100, blank=True)
    medium_of_instruction = models.CharField(max_length=100, blank=True)
    academic_session = models.CharField(max_length=20, blank=True)

    # Cricket (student/parent-known portion only)
    playing_experience_years = models.PositiveSmallIntegerField(null=True, blank=True)
    previous_academy = models.CharField(max_length=150, blank=True)
    achievements = models.TextField(blank=True)

    # Residential
    food_preference = models.CharField(max_length=100, blank=True)
    room_preference = models.CharField(max_length=100, blank=True)
    local_guardian_address = models.TextField(blank=True)

    # Medical
    allergies = models.TextField(blank=True)
    existing_conditions = models.TextField(blank=True)
    past_injuries = models.TextField(blank=True)
    family_doctor_contact = models.CharField(max_length=16, blank=True)

    def __str__(self) -> str:
        return f"Profile for {self.student}"


class StudentStatusHistory(AuditedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, choices=StudentStatus.choices, blank=True)
    to_status = models.CharField(max_length=20, choices=StudentStatus.choices)
    reason = models.TextField()
    changed_by = models.ForeignKey("iam.User", on_delete=models.PROTECT, related_name="+")
    approval = models.ForeignKey(
        ApprovalRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.student}: {self.from_status or '—'} -> {self.to_status}"
