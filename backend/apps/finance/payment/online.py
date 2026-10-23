"""Collecting a payment online — the gateway's checkout window opened at
the desk, or a payment link sent to the payer. Gateway-agnostic
(everything provider-specific sits behind `gateways`) and
purpose-agnostic: an OnlinePayment is either a direct admission's fee or
a ledger payment (monthly coaching fee, ...), and only `_record()`
differs between the two.

A gateway-confirmed payment needs no manual verification: the gateway's
signed confirmation *is* the verification.

Every path that can discover a payment — the browser's checkout
response, a webhook, "Check payment status", or the next attempt to
start a payment — ends in `settle()`, which is idempotent, so a payment
reported twice is still recorded once.
"""

import datetime
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from .gateways import GATEWAYS, get_gateway
from .gateways.base import Customer, GatewayError
from .models import (
    OnlinePayment,
    OnlinePaymentKind,
    OnlinePaymentStatus,
    Payment,
    PaymentMode,
)

logger = logging.getLogger(__name__)

LINK_VALID_DAYS = 7


def open_attempts(queryset):
    return queryset.filter(status=OnlinePaymentStatus.CREATED)


def close(attempt: OnlinePayment) -> None:
    """Stop an open attempt from taking money — once the thing it was for
    has been paid some other way, or a new attempt replaces it."""
    if attempt.kind == OnlinePaymentKind.LINK:
        try:
            get_gateway(attempt.gateway).cancel_link(gateway_id=attempt.gateway_id)
        except GatewayError:
            # Already paid/expired at the gateway, or unreachable — the
            # next sync settles or flags it either way.
            logger.warning("Could not cancel payment link %s", attempt.gateway_id, exc_info=True)
            return
    attempt.status = OnlinePaymentStatus.CANCELLED
    attempt.save(update_fields=["status", "updated_at"])


def close_all(queryset) -> None:
    for attempt in list(open_attempts(queryset)):
        close(attempt)


# --- Starting a payment --- #


def start_checkout(
    *,
    amount: Decimal,
    reference: str,
    description: str,
    customer: Customer,
    notes: dict,
    user,
    **target,
) -> tuple[OnlinePayment, dict]:
    """`target` is what the payment is for — `admission=...`, or
    `person=..., payment_type=..., billing_period=...`."""
    gateway = get_gateway()
    session = gateway.create_checkout(
        amount=amount, reference=reference, description=description, customer=customer, notes=notes
    )
    attempt = OnlinePayment.objects.create(
        kind=OnlinePaymentKind.CHECKOUT,
        gateway=gateway.name,
        gateway_id=session.gateway_id,
        amount=amount,
        created_by=user,
        **target,
    )
    return attempt, {"gateway": gateway.name, "options": session.client_options}


def send_link(
    *,
    amount: Decimal,
    reference: str,
    description: str,
    customer: Customer,
    notes: dict,
    user,
    **target,
) -> OnlinePayment:
    if not customer.mobile:
        raise ValidationError({"detail": "No mobile number on file to send the link to."})
    gateway = get_gateway()
    session = gateway.create_link(
        amount=amount,
        reference=reference,
        description=description,
        customer=customer,
        expires_in_days=LINK_VALID_DAYS,
        notes=notes,
    )
    return OnlinePayment.objects.create(
        kind=OnlinePaymentKind.LINK,
        gateway=gateway.name,
        gateway_id=session.gateway_id,
        amount=amount,
        short_url=session.short_url,
        sent_to=customer.mobile,
        created_by=user,
        **target,
    )


# --- Finding out it was paid --- #


def confirm(attempt: OnlinePayment, payload: dict) -> None:
    """The browser's report from the checkout window — verified by the
    gateway adapter before anything is recorded."""
    if attempt.kind != OnlinePaymentKind.CHECKOUT:
        raise ValidationError({"detail": "Only a desk checkout can be confirmed this way."})
    if attempt.status == OnlinePaymentStatus.PAID:
        return
    payment_id = get_gateway(attempt.gateway).confirm_checkout(
        gateway_id=attempt.gateway_id, amount=attempt.amount, payload=payload
    )
    settle(attempt, payment_id)


def sync(attempt: OnlinePayment) -> None:
    """Ask the gateway where an open attempt stands; settle it if paid."""
    if attempt.status != OnlinePaymentStatus.CREATED:
        return
    gateway = get_gateway(attempt.gateway)
    if attempt.kind == OnlinePaymentKind.LINK:
        status = gateway.link_status(gateway_id=attempt.gateway_id)
    else:
        status = gateway.checkout_status(gateway_id=attempt.gateway_id, amount=attempt.amount)
    if status.state == OnlinePaymentStatus.PAID:
        settle(attempt, status.payment_id)
    elif status.state in (OnlinePaymentStatus.CANCELLED, OnlinePaymentStatus.EXPIRED):
        attempt.status = status.state
        attempt.save(update_fields=["status", "updated_at"])


def sync_all(queryset) -> None:
    for attempt in list(open_attempts(queryset)):
        sync(attempt)


def handle_webhook(gateway_name: str, *, body: bytes, headers) -> None:
    event = get_gateway(gateway_name).parse_webhook(body=body, headers=headers)
    if event is None:
        return
    attempt = OnlinePayment.objects.filter(
        gateway=gateway_name, gateway_id=event.gateway_id
    ).first()
    if attempt is not None and event.payment_id:
        settle(attempt, event.payment_id)


# --- Managing a sent link --- #


def resend_link(attempt: OnlinePayment) -> None:
    _require_open_link(attempt)
    get_gateway(attempt.gateway).resend_link(gateway_id=attempt.gateway_id)


def cancel_link(attempt: OnlinePayment) -> None:
    _require_open_link(attempt)
    sync(attempt)
    attempt.refresh_from_db()
    if attempt.status == OnlinePaymentStatus.PAID:
        raise ValidationError({"detail": "It has already been paid — the link can't be cancelled."})
    if attempt.status == OnlinePaymentStatus.CREATED:
        get_gateway(attempt.gateway).cancel_link(gateway_id=attempt.gateway_id)
        attempt.status = OnlinePaymentStatus.CANCELLED
        attempt.save(update_fields=["status", "updated_at"])


def _require_open_link(attempt: OnlinePayment) -> None:
    if attempt.kind != OnlinePaymentKind.LINK or attempt.status != OnlinePaymentStatus.CREATED:
        raise ValidationError({"detail": "This payment link is no longer open."})


# --- Recording a confirmed payment --- #


def gateway_label(name: str) -> str:
    return GATEWAYS[name].label if name in GATEWAYS else name


@transaction.atomic
def settle(attempt: OnlinePayment, gateway_payment_id: str) -> None:
    attempt = OnlinePayment.objects.select_for_update().get(pk=attempt.pk)
    if attempt.status == OnlinePaymentStatus.PAID:
        return  # already recorded — reported again by another path
    attempt.status = OnlinePaymentStatus.PAID
    attempt.gateway_payment_id = gateway_payment_id
    attempt.paid_at = timezone.now()
    attempt.save(update_fields=["status", "gateway_payment_id", "paid_at", "updated_at"])

    try:
        # Savepoint: if the payment can't be recorded (already paid some
        # other way, admission moved on, ...), the money is still marked as
        # received and flagged — never rolled back out of sight.
        with transaction.atomic():
            note = _record(attempt, gateway_payment_id)
    except (ValidationError, DjangoValidationError, APIException) as exc:
        note = (
            f"Paid online, but it could not be recorded ({exc}). "
            "Record it manually or refund it from the gateway dashboard."
        )
    if note:
        attempt.note = note
        attempt.save(update_fields=["note", "updated_at"])
        logger.warning("Online payment %s needs attention: %s", gateway_payment_id, note)


def _record(attempt: OnlinePayment, gateway_payment_id: str) -> str:
    """Create the real payment record. Returns a note for a person to act
    on (e.g. a refund) instead, when it can't be recorded."""
    if attempt.admission_id is not None:
        # The admission app owns its own state machine; it depends on this
        # app, never the other way round, hence the local import.
        from apps.admissions.admission.online_payment import record_admission_fee

        return record_admission_fee(
            attempt, gateway_payment_id, label=gateway_label(attempt.gateway)
        )
    return _record_ledger_payment(attempt, gateway_payment_id)


def _record_ledger_payment(attempt: OnlinePayment, gateway_payment_id: str) -> str:
    from . import services

    if (
        attempt.billing_period
        and Payment.objects.filter(
            person=attempt.person,
            payment_type=attempt.payment_type,
            billing_period=attempt.billing_period,
        ).exists()
    ):
        return (
            "Paid online, but this month had already been recorded for this person. "
            "Refund this payment from the gateway dashboard."
        )
    payment = services.record_payment(
        attempt.person,
        payment_type=attempt.payment_type,
        amount=attempt.amount,
        payment_mode=PaymentMode.GATEWAY,
        payment_date=datetime.date.today(),
        user=attempt.created_by,
        billing_period=attempt.billing_period,
        reference_no=gateway_payment_id,
        idempotency_key=f"{attempt.gateway}:{gateway_payment_id}",
    )
    attempt.payment = payment
    attempt.save(update_fields=["payment", "updated_at"])
    return ""


# --- Ledger payments (monthly coaching fee, ...) --- #


def _ledger_target(person, payment_type, billing_period) -> dict:
    return {"person": person, "payment_type": payment_type, "billing_period": billing_period}


def _ledger_attempts(person, payment_type, billing_period):
    return OnlinePayment.objects.filter(**_ledger_target(person, payment_type, billing_period))


def _check_ledger_ready(person, payment_type, billing_period, amount: Decimal) -> None:
    """What Payment.clean() and its uniqueness rule would reject, checked
    *before* the payer is asked for money."""
    if amount <= 0:
        raise ValidationError({"amount": "Enter an amount above zero to collect online."})
    if payment_type.is_recurring:
        if not billing_period:
            raise ValidationError({"billing_period": "Required for a recurring payment type."})
        if billing_period.day != 1:
            raise ValidationError({"billing_period": "Must be the first of the month."})
        if Payment.objects.filter(
            person=person, payment_type=payment_type, billing_period=billing_period
        ).exists():
            raise ValidationError(
                {"billing_period": "This month is already recorded for this person."}
            )


def _ledger_customer(person) -> Customer:
    """A student's fee is normally paid by their parent — the link goes to
    the primary guardian's mobile when there is one, else the person's own."""
    from apps.people.models import StudentGuardian

    link = (
        StudentGuardian.objects.filter(student__person=person, is_primary=True)
        .select_related("guardian__person")
        .first()
    )
    if link is not None and link.guardian.person.mobile:
        return Customer(name=str(link.guardian.person), mobile=link.guardian.person.mobile)
    return Customer(name=str(person), mobile=person.mobile)


def _ledger_details(person, payment_type, billing_period) -> dict:
    period = f" - {billing_period:%B %Y}" if billing_period else ""
    return {
        "description": f"{payment_type.label}{period} - {person}",
        "notes": {"person_id": str(person.id), "payment_type": payment_type.code},
    }


def _prepare_ledger(person, payment_type, billing_period, amount: Decimal) -> None:
    # A window or link from earlier may have been paid after all.
    sync_all(_ledger_attempts(person, payment_type, billing_period))
    _check_ledger_ready(person, payment_type, billing_period, amount)
    if billing_period:
        # One way to pay a given month at a time.
        close_all(_ledger_attempts(person, payment_type, billing_period))


def start_ledger_checkout(
    *, person, payment_type, billing_period, amount: Decimal, user
) -> tuple[OnlinePayment, dict]:
    _prepare_ledger(person, payment_type, billing_period, amount)
    count = OnlinePayment.objects.filter(person=person).count() + 1
    return start_checkout(
        amount=amount,
        reference=f"PAY-{str(person.id)[:8]}-{count}",
        customer=_ledger_customer(person),
        user=user,
        **_ledger_details(person, payment_type, billing_period),
        **_ledger_target(person, payment_type, billing_period),
    )


def send_ledger_link(
    *, person, payment_type, billing_period, amount: Decimal, user
) -> OnlinePayment:
    _prepare_ledger(person, payment_type, billing_period, amount)
    count = OnlinePayment.objects.filter(person=person).count() + 1
    return send_link(
        amount=amount,
        reference=f"PAY-{str(person.id)[:8]}-{count}",
        customer=_ledger_customer(person),
        user=user,
        **_ledger_details(person, payment_type, billing_period),
        **_ledger_target(person, payment_type, billing_period),
    )
