from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import AuditedModel

from .services import compute_dedupe_key, normalize_mobile_e164


class Gender(models.TextChoices):
    MALE = "M", "Male"
    FEMALE = "F", "Female"
    OTHER = "O", "Other"


class BloodGroup(models.TextChoices):
    A_POSITIVE = "A+", "A+"
    A_NEGATIVE = "A-", "A-"
    B_POSITIVE = "B+", "B+"
    B_NEGATIVE = "B-", "B-"
    AB_POSITIVE = "AB+", "AB+"
    AB_NEGATIVE = "AB-", "AB-"
    O_POSITIVE = "O+", "O+"
    O_NEGATIVE = "O-", "O-"


class Person(AuditedModel):
    """The human being. Created once, never duplicated — SOP §78.

    docs/01-data-model.md section 1. `photograph` (FK Document) isn't here
    yet — apps.admissions.document doesn't have a Document model until
    T-203; it lands as an AddField migration once that exists.
    """

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)

    mobile = models.CharField(max_length=15, db_index=True)
    email = models.EmailField(blank=True)

    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)

    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)

    dedupe_key = models.CharField(max_length=64, db_index=True, editable=False, blank=True)

    def save(self, *args, **kwargs):
        self.mobile = normalize_mobile_e164(self.mobile)
        self.dedupe_key = compute_dedupe_key(
            first_name=self.first_name,
            last_name=self.last_name,
            date_of_birth=self.date_of_birth,
            mobile=self.mobile,
        )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Guardian(AuditedModel):
    person = models.OneToOneField(Person, on_delete=models.PROTECT)
    occupation = models.CharField(max_length=100, blank=True)
    portal_access = models.BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.person)


class Relationship(models.TextChoices):
    FATHER = "father", "Father"
    MOTHER = "mother", "Mother"
    GUARDIAN = "guardian", "Guardian"
    OTHER = "other", "Other"


class StudentGuardian(AuditedModel):
    """A guardian's relationship to one student. `student` is a string
    reference — apps.admissions.student.Student is a stub until T-701;
    docs/00-project-structure.md's dependency rules call for a string
    reference here rather than a direct cross-app import regardless.
    """

    student = models.ForeignKey(
        "student.Student", on_delete=models.CASCADE, related_name="guardians"
    )
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="students")
    relationship = models.CharField(max_length=20, choices=Relationship.choices)
    is_primary = models.BooleanField(default=False)
    is_emergency_contact = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "guardian"], name="unique_student_guardian"),
        ]

    def clean(self):
        super().clean()
        if self.is_primary:
            conflicting = StudentGuardian.objects.filter(student=self.student, is_primary=True)
            if self.pk:
                conflicting = conflicting.exclude(pk=self.pk)
            if conflicting.exists():
                raise ValidationError(
                    {"is_primary": "This student already has a primary guardian."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class StaffType(models.TextChoices):
    COACH = "coach", "Coach"
    MEDICAL = "medical", "Medical"
    PHYSIO = "physio", "Physio"
    HOSTEL = "hostel", "Hostel"
    TRANSPORT = "transport", "Transport"
    ADMIN = "admin", "Admin"
    ATHLETE_MGMT = "athlete_mgmt", "Athlete Management"


class Staff(AuditedModel):
    person = models.OneToOneField(Person, on_delete=models.PROTECT)
    employee_code = models.CharField(max_length=20, unique=True)
    staff_type = models.CharField(max_length=20, choices=StaffType.choices)
    joining_date = models.DateField()
    exit_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.person} ({self.employee_code})"
