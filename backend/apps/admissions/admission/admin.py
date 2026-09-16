from django.contrib import admin

from .models import Admission, AdmissionChecklistItem, AdmissionIntake, ConsentRecord


class AdmissionChecklistItemInline(admin.TabularInline):
    model = AdmissionChecklistItem
    extra = 0
    autocomplete_fields = ["document_type", "document"]


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ["application_no", "person", "programme", "step", "fee_payment_status"]
    list_filter = ["step", "fee_payment_status", "programme"]
    search_fields = ["application_no", "person__first_name", "person__last_name"]
    autocomplete_fields = ["person", "enquiry", "trial_registration", "programme"]
    inlines = [AdmissionChecklistItemInline]


@admin.register(AdmissionChecklistItem)
class AdmissionChecklistItemAdmin(admin.ModelAdmin):
    list_display = ["admission", "document_type", "is_mandatory", "status"]
    list_filter = ["status", "is_mandatory", "document_type"]
    search_fields = ["admission__application_no"]
    autocomplete_fields = ["admission", "document_type"]


@admin.register(AdmissionIntake)
class AdmissionIntakeAdmin(admin.ModelAdmin):
    list_display = [
        "admission",
        "full_name",
        "admission_category",
        "age_category",
        "guardian_name",
        "guardian_mobile",
    ]
    list_filter = ["admission_category", "age_category", "gender"]
    search_fields = ["full_name", "guardian_name", "guardian_mobile", "admission__application_no"]
    autocomplete_fields = ["admission", "season", "age_category"]
    # age_category is computed in save() from date_of_birth + season (see
    # the model's own comment) — never hand-editable, same reasoning as
    # people.admin.PersonAdmin's dedupe_key.
    readonly_fields = ["age_category"]


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ["admission", "consent_type", "granted", "version", "granted_at"]
    list_filter = ["consent_type", "granted"]
    search_fields = ["admission__application_no", "declared_by_name"]
    autocomplete_fields = ["admission", "consent_type"]
