from django.contrib import admin

from .models import Admission, AdmissionChecklistItem


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
