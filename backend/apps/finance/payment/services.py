"""Write and read paths for the unified payment ledger — see
models.Payment's docstring for the two-stage confirmation/invoice design.
"""

import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.services.numbering import next_number

from .models import Payment, PaymentLedgerStatus
from .state import PaymentStateMachine


def record_payment(
    person,
    *,
    payment_type,
    amount,
    payment_mode,
    payment_date,
    user,
    billing_period=None,
    reference_no: str = "",
    idempotency_key: str = "",
) -> Payment:
    """Creates a Payment at CONFIRMED and mints its confirmation_no —
    "Payment Confirmation... issued immediately when a payment is
    received" (spec §4), not a separate manual step. A replay of the same
    Idempotency-Key is a no-op returning the existing row, same pattern as
    apps.admissions.admission.services.record_direct_payment.
    """
    if idempotency_key:
        existing = Payment.objects.filter(person=person, idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing

    payment = Payment(
        person=person,
        payment_type=payment_type,
        billing_period=billing_period,
        amount=amount,
        payment_mode=payment_mode,
        reference_no=reference_no,
        payment_date=payment_date,
        recorded_by=user,
        idempotency_key=idempotency_key,
        confirmation_no=next_number("PCF"),
    )
    # PaymentStateMachine.apply() is still run (even though `status`
    # already defaults to CONFIRMED) so this creation path goes through
    # the same guard/role machinery as every other state-driven write in
    # this codebase, rather than relying on the model default alone.
    machine = PaymentStateMachine(payment)
    machine.apply(PaymentLedgerStatus.CONFIRMED, user=user)
    payment.full_clean()
    payment.save()
    return payment


@transaction.atomic
def mark_settled(payment: Payment, *, user) -> Payment:
    """confirmed -> settled. Mints invoice_no from the INV series only
    now — "Invoice... issued only after the payment is confirmed as
    settled" (spec §4).
    """
    machine = PaymentStateMachine(payment)
    machine.apply(PaymentLedgerStatus.SETTLED, user=user)
    payment.invoice_no = next_number("INV")
    payment.invoiced_at = timezone.now()
    payment.settled_by = user
    payment.save(update_fields=["status", "invoice_no", "invoiced_at", "settled_by", "updated_at"])
    return payment


def void_payment(payment: Payment, *, user, reason: str) -> Payment:
    """confirmed -> void. The row is kept, not deleted (unlike
    apps.admissions.admission.services.verify_direct_payment's
    reject-and-delete for AdmissionPayment) — a real confirmation_no was
    already minted and shown to the payer, so voiding must stay visible
    in the ledger rather than disappear.
    """
    machine = PaymentStateMachine(payment)
    machine.apply(PaymentLedgerStatus.VOID, user=user, reason=reason)
    payment.void_reason = reason
    payment.save(update_fields=["status", "void_reason", "updated_at"])
    return payment


def admission_fee_paid(admission, admission_payment, *, user) -> Payment:
    """Mirrors a verified AdmissionPayment (the direct-admission wizard's
    one-time fee, untouched by this feature) into the unified ledger, so
    the admission fee still shows up in the same history the spec asks
    for — called from
    apps.admissions.student.services.approve_admission, once
    admission.person is guaranteed set. It can't be called any earlier
    (e.g. from verify_direct_payment, when the payment itself is
    verified): a fresh direct-intake admission has no Person yet at that
    point — Person resolution only happens at approval.
    """
    from apps.core.models import PaymentType

    if admission.person_id is None:
        raise ValidationError({"detail": "Admission has no Person yet — cannot mirror payment."})

    payment_type = PaymentType.objects.get(code="admission_fee")
    return record_payment(
        admission.person,
        payment_type=payment_type,
        amount=admission.fee_total,
        payment_mode=admission_payment.payment_mode,
        payment_date=admission_payment.payment_date,
        user=user,
        reference_no=admission_payment.receipt_no,
        idempotency_key=f"admission-fee:{admission_payment.id}",
    )


def _current_month_recurring_payment(person):
    today = datetime.date.today()
    return (
        Payment.objects.filter(
            person=person,
            payment_type__is_recurring=True,
            billing_period=today.replace(day=1),
            status__in=[PaymentLedgerStatus.CONFIRMED, PaymentLedgerStatus.SETTLED],
        )
        .order_by("-created_at")
        .first()
    )


def is_current_month_paid(person) -> bool:
    """The exact "paid this month" check payment_history()'s own
    current_month block makes — extracted so it has one definition, used
    both there and by apps.academics.batch's roster fee-status pill,
    rather than the same query living in two places.
    """
    return _current_month_recurring_payment(person) is not None


def payment_history(person) -> dict:
    """GET .../payments — spec §5: "the current month's status... shown
    first" plus "a complete month-by-month history of all periods."
    `current_month` only ever reports "paid" or "due": the current month,
    by definition, can't yet be "overdue" — that label only makes sense
    for a *past* recurring month still sitting unpaid, which `history`
    already surfaces via its own `status`/`billing_period` per row without
    this function inventing a specific day-of-month cutoff the spec never
    states.
    """
    from .serializers import PaymentSerializer

    today = datetime.date.today()
    current_period = today.replace(day=1)
    qs = Payment.objects.filter(person=person).order_by("-payment_date", "-created_at")
    current_month_payment = _current_month_recurring_payment(person)

    return {
        "current_month": {
            "billing_period": current_period,
            "status": "paid" if current_month_payment else "due",
            "payment": PaymentSerializer(current_month_payment).data
            if current_month_payment
            else None,
        },
        "history": PaymentSerializer(qs, many=True).data,
    }
