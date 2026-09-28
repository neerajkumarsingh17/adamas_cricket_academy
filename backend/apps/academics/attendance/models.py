"""docs/00-project-structure.md's academics/attendance app (M10)."""

from django.db import models

from apps.academics.batch.models import TrainingSession
from apps.admissions.student.models import Student
from apps.core.models import AuditedModel


class Status(models.TextChoices):
    PRESENT = "present", "Present"
    LATE = "late", "Late"
    ABSENT = "absent", "Absent"
    LEAVE = "leave", "Leave"
    MEDICAL_LEAVE = "medical_leave", "Medical leave"
    TOURNAMENT_DUTY = "tournament_duty", "Tournament duty"
    OFFICIAL_DUTY = "official_duty", "Official duty"


# The entire attendance policy. Nothing else may hardcode a status —
# a report/aggregation asking "did this count as present" checks
# membership in one of these two sets, never `status == "..."` directly.
COUNTS_AS_PRESENT = {Status.PRESENT, Status.LATE, Status.TOURNAMENT_DUTY, Status.OFFICIAL_DUTY}
NOT_COUNTED = {Status.MEDICAL_LEAVE}


class Attendance(AuditedModel):
    session = models.ForeignKey(
        TrainingSession, on_delete=models.CASCADE, related_name="attendance_records"
    )
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="attendance_records"
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey("iam.User", on_delete=models.PROTECT, related_name="+")
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"], name="unique_attendance_per_session_student"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.session} — {self.status}"


class CorrectionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class AttendanceCorrection(AuditedModel):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name="corrections")
    from_status = models.CharField(max_length=20, choices=Status.choices)
    to_status = models.CharField(max_length=20, choices=Status.choices)
    reason = models.TextField()
    requested_by = models.ForeignKey("iam.User", on_delete=models.PROTECT, related_name="+")
    # Distinct from "approved_by is null" so a rejected correction doesn't
    # keep showing up in a "pending" queue forever — added when the
    # corrections queue needed a real pending/approved/rejected filter.
    status = models.CharField(
        max_length=20, choices=CorrectionStatus.choices, default=CorrectionStatus.PENDING
    )
    approved_by = models.ForeignKey(
        "iam.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.attendance}: {self.from_status} -> {self.to_status}"
