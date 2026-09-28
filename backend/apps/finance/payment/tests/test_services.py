import datetime

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.state import InvalidTransition
from apps.core.tests.factories import PaymentTypeFactory
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory

from .. import services
from ..models import PaymentLedgerStatus
from .factories import PaymentFactory


@pytest.mark.django_db
def test_record_payment_confirms_immediately_and_mints_confirmation_no():
    """Spec: "Payment Confirmation... issued immediately when a payment
    is received" — not a separate manual step."""
    person = PersonFactory()
    payment_type = PaymentTypeFactory(is_recurring=False)
    user = UserFactory()

    payment = services.record_payment(
        person,
        payment_type=payment_type,
        amount="1000.00",
        payment_mode="upi",
        payment_date=datetime.date.today(),
        user=user,
    )

    assert payment.status == PaymentLedgerStatus.CONFIRMED
    assert payment.confirmation_no.startswith("PCF/")
    assert payment.invoice_no is None


@pytest.mark.django_db
def test_record_payment_is_idempotent_on_replay():
    person = PersonFactory()
    payment_type = PaymentTypeFactory(is_recurring=False)
    user = UserFactory()

    first = services.record_payment(
        person,
        payment_type=payment_type,
        amount="1000.00",
        payment_mode="upi",
        payment_date=datetime.date.today(),
        user=user,
        idempotency_key="replay-key-1",
    )
    second = services.record_payment(
        person,
        payment_type=payment_type,
        amount="1000.00",
        payment_mode="upi",
        payment_date=datetime.date.today(),
        user=user,
        idempotency_key="replay-key-1",
    )

    assert first.id == second.id


@pytest.mark.django_db
def test_mark_settled_mints_invoice_no():
    """Spec: "Invoice... issued only after the payment is confirmed as
    settled" — invoice_no stays null until this point."""
    payment = PaymentFactory()
    user = UserFactory()
    assert payment.invoice_no is None

    settled = services.mark_settled(payment, user=user)

    assert settled.status == PaymentLedgerStatus.SETTLED
    assert settled.invoice_no.startswith("INV/")
    assert settled.invoiced_at is not None
    assert settled.settled_by == user


@pytest.mark.django_db
def test_settling_an_already_settled_payment_is_rejected():
    """Rejected-transition coverage — CLAUDE.md testing policy: a test
    per transition AND per rejected transition."""
    payment = PaymentFactory()
    user = UserFactory()
    services.mark_settled(payment, user=user)

    with pytest.raises(InvalidTransition):
        services.mark_settled(payment, user=user)


@pytest.mark.django_db
def test_void_payment_requires_a_reason():
    payment = PaymentFactory()
    user = UserFactory()

    with pytest.raises(ValidationError):
        services.void_payment(payment, user=user, reason="")


@pytest.mark.django_db
def test_void_payment_keeps_the_row_with_its_confirmation_no():
    """Unlike AdmissionPayment's reject-and-delete, a voided Payment row
    survives — its confirmation_no was already shown to the payer."""
    payment = PaymentFactory()
    user = UserFactory()
    confirmation_no = payment.confirmation_no

    voided = services.void_payment(payment, user=user, reason="Wrong amount entered.")

    assert voided.status == PaymentLedgerStatus.VOID
    assert voided.confirmation_no == confirmation_no
    assert voided.void_reason == "Wrong amount entered."


@pytest.mark.django_db
def test_voiding_an_already_voided_payment_is_rejected():
    payment = PaymentFactory()
    user = UserFactory()
    services.void_payment(payment, user=user, reason="Wrong amount entered.")

    with pytest.raises(InvalidTransition):
        services.void_payment(payment, user=user, reason="Again.")


@pytest.mark.django_db
def test_payment_history_reports_current_month_paid_when_a_recurring_payment_exists():
    person = PersonFactory()
    recurring = PaymentTypeFactory(is_recurring=True)
    today = datetime.date.today()
    current_period = today.replace(day=1)
    PaymentFactory(person=person, payment_type=recurring, billing_period=current_period)

    result = services.payment_history(person)

    assert result["current_month"]["status"] == "paid"
    assert result["current_month"]["billing_period"] == current_period


@pytest.mark.django_db
def test_payment_history_reports_current_month_due_with_no_payment():
    person = PersonFactory()

    result = services.payment_history(person)

    assert result["current_month"]["status"] == "due"
    assert result["current_month"]["payment"] is None
    assert result["history"] == []


@pytest.mark.django_db
def test_is_current_month_paid_agrees_with_payment_history():
    """The roster fee-status pill and the portal's current_month block
    must never disagree — both go through the same helper."""
    person = PersonFactory()
    recurring = PaymentTypeFactory(is_recurring=True)
    current_period = datetime.date.today().replace(day=1)

    assert services.is_current_month_paid(person) is False
    assert services.payment_history(person)["current_month"]["status"] == "due"

    PaymentFactory(person=person, payment_type=recurring, billing_period=current_period)

    assert services.is_current_month_paid(person) is True
    assert services.payment_history(person)["current_month"]["status"] == "paid"


@pytest.mark.django_db
def test_is_current_month_paid_ignores_one_off_and_voided_payments():
    person = PersonFactory()
    one_off = PaymentTypeFactory(is_recurring=False)
    recurring = PaymentTypeFactory(is_recurring=True)
    current_period = datetime.date.today().replace(day=1)

    # A one-off payment (admission fee) this month is not a coaching fee.
    PaymentFactory(person=person, payment_type=one_off, billing_period=None)
    assert services.is_current_month_paid(person) is False

    # A voided recurring payment doesn't count either.
    voided = PaymentFactory(person=person, payment_type=recurring, billing_period=current_period)
    services.void_payment(voided, user=UserFactory(), reason="Bounced cheque.")
    assert services.is_current_month_paid(person) is False
