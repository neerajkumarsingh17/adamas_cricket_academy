from django.contrib import admin

from .models import AdmissionPayment


@admin.register(AdmissionPayment)
class AdmissionPaymentAdmin(admin.ModelAdmin):
    """Read-only. `receipt_no` is minted once via core.services.numbering
    and de-duplicated by `idempotency_key`; verification stamps
    `verified_by`/`verified_at` through the record/verify-payment
    endpoints. Editing a row directly here would let those invariants
    (CLAUDE.md rule 7: money is transactional) drift from what the receipt
    and audit trail actually say — same reasoning as
    apps.core.admin.ApprovalRequestAdmin.
    """

    list_display = [
        "receipt_no",
        "admission",
        "amount",
        "payment_mode",
        "payment_date",
        "recorded_by",
        "verified_by",
        "verified_at",
        "created_at",
    ]
    list_filter = ["payment_mode", "verified_at"]
    search_fields = ["receipt_no", "admission__application_no"]
    autocomplete_fields = ["admission", "recorded_by", "verified_by"]

    @admin.display(description="Amount")
    def amount(self, obj):
        # AdmissionPayment has no amount column of its own — one payment
        # can cover several AdmissionFeeLine rows (registration + coaching
        # etc.), so the model docstring is explicit that the total is never
        # stored here, only on the lines. Reusing Admission.fee_total keeps
        # this in sync with them by construction rather than duplicating
        # the Sum() aggregate.
        return obj.admission.fee_total

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
