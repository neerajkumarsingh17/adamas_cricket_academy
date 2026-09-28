from django.contrib import admin

from .models import Batch, BatchEnrollment, Coach, TrainingSession


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ["staff", "specialisation", "experience_years", "is_available"]
    list_filter = ["is_available"]
    search_fields = [
        "staff__employee_code",
        "staff__person__first_name",
        "staff__person__last_name",
        "specialisation",
    ]
    autocomplete_fields = ["staff"]


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "age_category",
        "coach",
        "venue",
        "capacity",
        "monthly_fee",
        "residential_monthly_fee",
        "is_active",
    ]
    list_filter = ["age_category", "venue", "is_active"]
    search_fields = ["name"]
    autocomplete_fields = ["age_category", "coach", "venue"]


@admin.register(BatchEnrollment)
class BatchEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "batch", "from_date", "to_date", "is_active"]
    list_filter = ["is_active", "batch"]
    search_fields = [
        "student__student_code",
        "student__person__first_name",
        "student__person__last_name",
    ]
    autocomplete_fields = ["student", "batch"]


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ["batch", "date", "coach", "training_type", "is_conducted"]
    list_filter = ["training_type", "is_conducted", "batch"]
    search_fields = ["batch__name"]
    autocomplete_fields = ["batch", "coach", "training_type"]
