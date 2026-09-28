from django import forms
from django.contrib import admin

from . import services
from .models import AdmissionPayment, Payment, PaymentLedgerStatus

_PAYMENT_ADD_FIELDS = [
    "person",
    "payment_type",
    "billing_period",
    "amount",
    "payment_mode",
    "reference_no",
    "payment_date",
]


class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = _PAYMENT_ADD_FIELDS


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


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """This is where staff record a monthly coaching fee (or any other
    PaymentType) — pick Payment type = "Monthly Coaching Fee", a
    `billing_period`, amount, mode, date, and Save.

    `add` is allowed, but `save_model` below routes it through
    services.record_payment() instead of a plain `obj.save()` — that's
    what mints confirmation_no from the PCF series and runs clean()'s
    recurring/billing_period rule, so a payment created here is
    indistinguishable from one created via the API. Once a row exists it
    reverts to read-only (`has_change_permission` False), same reasoning
    as AdmissionPaymentAdmin: hand-editing an already-issued receipt
    would let it drift from what the payer was actually shown. Settling
    (minting invoice_no) is the "Mark selected payments as settled"
    action below, not a field edit.
    """

    form = PaymentAdminForm
    list_display = [
        "confirmation_no",
        "invoice_no",
        "person",
        "payment_type",
        "billing_period",
        "amount",
        "status",
        "payment_date",
    ]
    list_filter = ["payment_type", "status", "payment_mode"]
    search_fields = [
        "confirmation_no",
        "invoice_no",
        "reference_no",
        "person__first_name",
        "person__last_name",
        "person__mobile",
    ]
    autocomplete_fields = ["person", "payment_type", "recorded_by", "settled_by"]
    actions = ["mark_as_settled"]

    def get_fields(self, request, obj=None):
        if obj is None:
            return _PAYMENT_ADD_FIELDS
        return [f.name for f in self.model._meta.fields if f.name != "id"]

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        # Always False, including for a not-yet-saved `obj=None` add
        # request — this only blocks *editing an existing row*; Django's
        # add flow is gated by has_add_permission above instead.
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # `change` is always False here (has_change_permission blocks
        # edits) — `obj` is the unsaved instance Django built from the
        # form, discarded in favour of record_payment(), which mints
        # confirmation_no and enforces clean()'s validation rules that a
        # bare `obj.save()` would skip.
        services.record_payment(
            form.cleaned_data["person"],
            payment_type=form.cleaned_data["payment_type"],
            billing_period=form.cleaned_data["billing_period"],
            amount=form.cleaned_data["amount"],
            payment_mode=form.cleaned_data["payment_mode"],
            reference_no=form.cleaned_data["reference_no"],
            payment_date=form.cleaned_data["payment_date"],
            user=request.user,
        )

    @admin.action(description="Mark selected payments as settled (issues invoice)")
    def mark_as_settled(self, request, queryset):
        settled = 0
        for payment in queryset.filter(status=PaymentLedgerStatus.CONFIRMED):
            services.mark_settled(payment, user=request.user)
            settled += 1
        skipped = queryset.count() - settled
        if settled:
            self.message_user(request, f"{settled} payment(s) marked as settled and invoiced.")
        if skipped:
            self.message_user(
                request,
                f"{skipped} payment(s) skipped — not in 'confirmed' status.",
                level="warning",
            )
