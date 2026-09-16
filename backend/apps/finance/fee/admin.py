from django.contrib import admin

from .models import AdmissionFeeLine


@admin.register(AdmissionFeeLine)
class AdmissionFeeLineAdmin(admin.ModelAdmin):
    """Read-only. `Admission.fee_total` sums these live — see the model's
    own docstring on why a stored total is never kept in sync by hand —
    so editing a line's amount here rather than through the fee-collection
    endpoint would silently change what the admission's total means
    without a matching receipt line to explain it.
    """

    list_display = ["admission", "fee_head", "amount"]
    list_filter = ["fee_head"]
    search_fields = ["admission__application_no"]
    autocomplete_fields = ["admission", "fee_head"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
