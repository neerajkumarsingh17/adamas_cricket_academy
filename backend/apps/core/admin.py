from django.contrib import admin

from .models import (
    AgeCategory,
    ApprovalRequest,
    ApprovalRule,
    AssessmentCriterion,
    Building,
    ConsentType,
    DocumentType,
    EnquirySource,
    FeeHead,
    PaymentType,
    Programme,
    Season,
    TrainingType,
    Venue,
)


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(AgeCategory)
class AgeCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "min_age", "max_age", "as_on_date_rule", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "address", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "address"]


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "address", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "address"]


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "start_date", "end_date", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(EnquirySource)
class EnquirySourceAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(TrainingType)
class TrainingTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "applies_to", "is_mandatory_default", "has_expiry"]
    list_filter = ["applies_to", "is_mandatory_default", "has_expiry"]
    search_fields = ["code", "name"]


@admin.register(FeeHead)
class FeeHeadAdmin(admin.ModelAdmin):
    list_display = ["label", "code", "applies_to", "is_mandatory", "display_order", "is_active"]
    list_filter = ["applies_to", "is_mandatory", "is_active"]
    search_fields = ["code", "label"]


@admin.register(ConsentType)
class ConsentTypeAdmin(admin.ModelAdmin):
    list_display = ["label", "code", "version", "is_mandatory", "is_active"]
    list_filter = ["is_mandatory", "is_active"]
    search_fields = ["code", "label"]


@admin.register(PaymentType)
class PaymentTypeAdmin(admin.ModelAdmin):
    list_display = ["label", "code", "is_recurring", "display_order", "is_active"]
    list_filter = ["is_recurring", "is_active"]
    search_fields = ["code", "label"]


@admin.register(AssessmentCriterion)
class AssessmentCriterionAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "group", "scale_min", "scale_max", "weight", "is_active"]
    list_filter = ["group", "is_active"]
    search_fields = ["code", "name"]


@admin.register(ApprovalRule)
class ApprovalRuleAdmin(admin.ModelAdmin):
    list_display = ["module", "action", "required_role"]
    list_filter = ["module"]
    search_fields = ["module", "action"]
    autocomplete_fields = ["required_role"]


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    """Read-only. Deciding a request must go through
    apps.core.services.approvals.decide() so its invariants (no
    self-approval, rejection requires a reason) can't be bypassed by
    editing a row directly here — same reasoning as AuditLog (CLAUDE.md
    rule 4: never add an UPDATE or DELETE path outside the app's own
    write path).
    """

    list_display = ["rule", "content_type", "object_id", "status", "requested_by", "decided_by"]
    list_filter = ["status", "rule__module"]
    search_fields = ["requested_by__login_id", "decided_by__login_id"]
    autocomplete_fields = ["rule", "requested_by", "decided_by"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
