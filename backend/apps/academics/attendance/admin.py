from django.contrib import admin

from .models import Attendance, AttendanceCorrection


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["session", "student", "status", "marked_by", "marked_at"]
    list_filter = ["status", "session__batch"]
    search_fields = [
        "student__student_code",
        "student__person__first_name",
        "student__person__last_name",
    ]
    autocomplete_fields = ["session", "student", "marked_by"]


@admin.register(AttendanceCorrection)
class AttendanceCorrectionAdmin(admin.ModelAdmin):
    list_display = [
        "attendance",
        "from_status",
        "to_status",
        "requested_by",
        "approved_by",
        "approved_at",
    ]
    list_filter = ["from_status", "to_status"]
    search_fields = ["attendance__student__student_code"]
    autocomplete_fields = ["attendance", "requested_by", "approved_by"]
