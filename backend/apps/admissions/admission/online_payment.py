"""Collecting a direct admission's fee online — the admission side of
apps.finance.payment.online (which does the gateway work for every kind
of online payment).

What's admission-specific lives here: what must be true before the
parent is asked for money, and what "paid" means for the admission —
draft -> payment_recorded -> payment_verified in one go, skipping the
Accounts verification step cash goes through (the gateway's signed
confirmation *is* the verification).
"""

import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.finance.payment import online
from apps.finance.payment.gateways.base import Customer
from apps.finance.payment.models import (
    AdmissionPayment,
    OnlinePayment,
    OnlinePaymentKind,
    PaymentMode,
)

from .models import Admission, AdmissionStep
from .state import DirectAdmissionStateMachine


def _ready_for_payment(admission: Admission):
    """Everything the cash path checks, checked *before* the parent is
    asked for money — a payment that then couldn't be recorded against
    the admission would have to be refunded by hand."""
    if not hasattr(admission, "intake"):
        raise ValidationError({"detail": "Online payment is only for direct admissions."})
    if admission.step != AdmissionStep.DRAFT or hasattr(admission, "payment"):
        raise ValidationError({"detail": "A payment has already been recorded for this admission."})
    transition = DirectAdmissionStateMachine(admission).transition_for(
        AdmissionStep.PAYMENT_RECORDED
    )
    if transition is not None and transition.guard is not None:
        transition.guard(admission, user=None, reason="")  # raises naming what's missing
    amount = admission.fee_total
    if amount <= 0:
        raise ValidationError({"fee_lines": "Enter the fee amount before collecting payment."})
    return amount


def _payment_details(admission: Admission) -> dict:
    intake = admission.intake
    return {
        "description": f"Admission fee - {intake.full_name} ({admission.application_no})",
        "customer": Customer(name=intake.guardian_name, mobile=intake.guardian_mobile),
        "notes": {"admission_id": str(admission.id), "application_no": admission.application_no},
    }


def record_admission_fee(attempt: OnlinePayment, gateway_payment_id: str, *, label: str) -> str:
    """apps.finance.payment.online's hook once an admission's online
    payment is confirmed. Returns a note for a person to act on instead
    when the admission can no longer take it."""
    from . import services

    assert attempt.admission_id is not None  # only ever called for admission attempts
    admission = Admission.objects.select_for_update().get(pk=attempt.admission_id)
    if admission.step != AdmissionStep.DRAFT or hasattr(admission, "payment"):
        return (
            "Paid online after a payment had already been recorded for this admission. "
            "Refund this payment from the gateway dashboard."
        )
    services.record_direct_payment(
        admission,
        payment_mode=PaymentMode.GATEWAY,
        payment_date=datetime.date.today(),
        user=attempt.created_by,
        reference_no=gateway_payment_id,
        idempotency_key=f"{attempt.gateway}:{gateway_payment_id}",
    )
    DirectAdmissionStateMachine(admission).apply(AdmissionStep.PAYMENT_VERIFIED)
    admission.save(update_fields=["step", "updated_at"])
    payment = AdmissionPayment.objects.get(admission=admission)
    payment.verified_at = timezone.now()
    payment.verification_note = f"Verified automatically by {label} (payment {gateway_payment_id})."
    payment.save(update_fields=["verified_at", "verification_note", "updated_at"])
    return ""


def close_open_attempts(admission: Admission) -> None:
    """Once the fee is paid — online or at the desk — no other open link
    or window may take a second payment. Called from
    services.record_direct_payment, so every way of paying goes through it.
    """
    online.close_all(admission.online_payments.all())


# --- Public API (called from views) --- #


def sync(admission: Admission) -> bool:
    """Ask the gateway about every open attempt; record any that were
    paid. True once the admission's fee has been paid."""
    online.sync_all(admission.online_payments.all())
    admission.refresh_from_db()
    return admission.step != AdmissionStep.DRAFT


def start_checkout(admission: Admission, *, user) -> dict | None:
    """The options the browser opens the gateway's window with — or None
    if a check on earlier attempts shows the fee is already paid."""
    if sync(admission):
        return None
    amount = _ready_for_payment(admission)
    # Only one way to pay at a time: an open link would let the parent pay
    # again from their phone while paying here.
    close_open_attempts(admission)
    _, checkout = online.start_checkout(
        amount=amount,
        reference=admission.application_no,
        user=user,
        admission=admission,
        **_payment_details(admission),
    )
    return checkout


def confirm_checkout(admission: Admission, *, gateway_id: str, payload: dict) -> None:
    attempt = admission.online_payments.filter(
        kind=OnlinePaymentKind.CHECKOUT, gateway_id=gateway_id
    ).first()
    if attempt is None:
        raise ValidationError({"detail": "Unknown payment for this admission."})
    online.confirm(attempt, payload)


def send_link(admission: Admission, *, user) -> None:
    if sync(admission):
        return
    amount = _ready_for_payment(admission)
    close_open_attempts(admission)
    online.send_link(
        amount=amount,
        reference=f"{admission.application_no}-{admission.online_payments.count() + 1}",
        user=user,
        admission=admission,
        **_payment_details(admission),
    )


def _open_link(admission: Admission) -> OnlinePayment:
    attempt = (
        online.open_attempts(admission.online_payments.all())
        .filter(kind=OnlinePaymentKind.LINK)
        .first()
    )
    if attempt is None:
        raise ValidationError({"detail": "There is no open payment link for this admission."})
    return attempt


def resend_link(admission: Admission) -> None:
    online.resend_link(_open_link(admission))


def cancel_link(admission: Admission) -> None:
    online.cancel_link(_open_link(admission))
