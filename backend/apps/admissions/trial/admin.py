from django.contrib import admin

from .models import TrialAssessment, TrialAssessmentScore, TrialRegistration, TrialResult, TrialSlot


class TrialAssessmentScoreInline(admin.TabularInline):
    model = TrialAssessmentScore
    extra = 0


@admin.register(TrialSlot)
class TrialSlotAdmin(admin.ModelAdmin):
    list_display = ["date", "reporting_time", "venue", "age_category", "booked_count", "capacity"]
    list_filter = ["venue", "age_category"]
    search_fields = ["venue__name", "age_category__name"]
    autocomplete_fields = ["venue", "age_category"]


@admin.register(TrialRegistration)
class TrialRegistrationAdmin(admin.ModelAdmin):
    list_display = ["trial_id", "enquiry", "slot", "payment_status", "attended"]
    list_filter = ["payment_status", "attended"]
    search_fields = ["trial_id", "enquiry__enquiry_no", "enquiry__student_name"]
    autocomplete_fields = ["enquiry", "person", "slot"]


@admin.register(TrialAssessment)
class TrialAssessmentAdmin(admin.ModelAdmin):
    list_display = ["registration", "assessed_by", "assessed_at", "is_locked"]
    list_filter = ["is_locked"]
    search_fields = ["registration__trial_id"]
    autocomplete_fields = ["registration", "assessed_by"]
    inlines = [TrialAssessmentScoreInline]


@admin.register(TrialResult)
class TrialResultAdmin(admin.ModelAdmin):
    list_display = ["registration", "outcome", "declared_by", "declared_at", "review_on"]
    list_filter = ["outcome"]
    search_fields = ["registration__trial_id"]
    autocomplete_fields = ["registration", "declared_by"]
