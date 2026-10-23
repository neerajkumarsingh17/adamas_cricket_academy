"""Collecting a ledger payment (monthly coaching fee, ...) online from the
Payments page, against the fake gateway."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.core.tests.factories import PaymentTypeFactory
from apps.finance.payment import online, services
from apps.finance.payment.gateways.base import GatewayError, GatewayStatus
from apps.finance.payment.models import OnlinePayment, OnlinePaymentStatus, Payment, PaymentMode
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory, StudentGuardianFactory

pytestmark = pytest.mark.usefixtures("fake_gateway")


OCTOBER = datetime.date(2026, 10, 1)


def _monthly_fee():
    return PaymentTypeFactory(code="monthly_coaching_fee", is_recurring=True)


def _start(person=None, payment_type=None, period=OCTOBER, amount="2500.00", user=None):
    return online.start_ledger_checkout(
        person=person or PersonFactory(),
        payment_type=payment_type or _monthly_fee(),
        billing_period=period,
        amount=Decimal(amount),
        user=user or UserFactory(),
    )


@pytest.mark.django_db
def test_a_paid_checkout_creates_the_ledger_payment():
    desk = UserFactory()
    attempt, checkout = _start(user=desk)

    online.confirm(attempt, {"signature": "good", "payment_id": "pay_1"})

    attempt.refresh_from_db()
    assert checkout["gateway"] == "fake"
    assert attempt.status == OnlinePaymentStatus.PAID
    payment = attempt.payment
    assert payment.payment_mode == PaymentMode.GATEWAY
    assert payment.reference_no == "pay_1"
    assert payment.amount == Decimal("2500.00")
    assert payment.billing_period == OCTOBER
    assert payment.recorded_by == desk
    assert payment.confirmation_no


@pytest.mark.django_db
def test_a_forged_response_records_nothing():
    attempt, _ = _start()

    with pytest.raises(GatewayError):
        online.confirm(attempt, {"signature": "forged", "payment_id": "x"})

    assert not Payment.objects.exists()


@pytest.mark.django_db
def test_a_month_already_paid_cannot_be_charged_again():
    person, fee = PersonFactory(), _monthly_fee()
    services.record_payment(
        person,
        payment_type=fee,
        amount=Decimal("2500"),
        payment_mode="cash",
        payment_date=datetime.date.today(),
        user=UserFactory(),
        billing_period=OCTOBER,
    )

    with pytest.raises(ValidationError):
        _start(person=person, payment_type=fee)

    assert not OnlinePayment.objects.exists()


@pytest.mark.django_db
def test_a_recurring_fee_needs_a_month():
    with pytest.raises(ValidationError):
        _start(period=None)


@pytest.mark.django_db
def test_a_one_off_fee_needs_no_month():
    attempt, _ = _start(payment_type=PaymentTypeFactory(is_recurring=False), period=None)

    online.confirm(attempt, {"signature": "good", "payment_id": "pay_2"})

    attempt.refresh_from_db()
    assert attempt.payment.billing_period is None


@pytest.mark.django_db
def test_a_students_link_goes_to_the_primary_guardian():
    link = StudentGuardianFactory(is_primary=True)
    student_person = link.student.person

    attempt = online.send_ledger_link(
        person=student_person,
        payment_type=_monthly_fee(),
        billing_period=OCTOBER,
        amount=Decimal("2500"),
        user=UserFactory(),
    )

    assert attempt.sent_to == link.guardian.person.mobile
    assert attempt.kind == "link"


@pytest.mark.django_db
def test_a_paid_link_is_recorded_when_checked(fake_gateway):
    person, fee = PersonFactory(), _monthly_fee()
    attempt = online.send_ledger_link(
        person=person,
        payment_type=fee,
        billing_period=OCTOBER,
        amount=Decimal("2500"),
        user=UserFactory(),
    )
    fake_gateway.statuses[attempt.gateway_id] = GatewayStatus(state="paid", payment_id="pay_3")

    online.sync(attempt)

    assert Payment.objects.get(person=person, billing_period=OCTOBER).reference_no == "pay_3"


@pytest.mark.django_db
def test_recording_the_month_by_hand_cancels_its_open_link(fake_gateway):
    person, fee = PersonFactory(), _monthly_fee()
    attempt = online.send_ledger_link(
        person=person,
        payment_type=fee,
        billing_period=OCTOBER,
        amount=Decimal("2500"),
        user=UserFactory(),
    )

    services.record_payment(
        person,
        payment_type=fee,
        amount=Decimal("2500"),
        payment_mode="cash",
        payment_date=datetime.date.today(),
        user=UserFactory(),
        billing_period=OCTOBER,
    )

    attempt.refresh_from_db()
    assert attempt.status == OnlinePaymentStatus.CANCELLED
    assert fake_gateway.cancelled == [attempt.gateway_id]


@pytest.mark.django_db
def test_paying_a_link_for_a_month_already_recorded_is_flagged_for_refund():
    person, fee = PersonFactory(), _monthly_fee()
    attempt = online.send_ledger_link(
        person=person,
        payment_type=fee,
        billing_period=OCTOBER,
        amount=Decimal("2500"),
        user=UserFactory(),
    )
    services.record_payment(
        person,
        payment_type=fee,
        amount=Decimal("2500"),
        payment_mode="cash",
        payment_date=datetime.date.today(),
        user=UserFactory(),
        billing_period=OCTOBER,
    )

    online.handle_webhook(
        "fake", body=f"{attempt.gateway_id}:pay_4".encode(), headers={"X-Fake-Signature": "good"}
    )

    attempt.refresh_from_db()
    assert attempt.status == OnlinePaymentStatus.PAID
    assert "Refund" in attempt.note
    assert Payment.objects.filter(person=person).count() == 1  # the cash one only


# --- API --- #


def _user_with_role(code):
    user = UserFactory()
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=code), valid_from=datetime.date(2020, 1, 1)
    )
    return user


@pytest.mark.django_db
def test_api_send_link_then_list_shows_it_waiting(seeded_roles):
    client = APIClient()
    client.force_authenticate(_user_with_role("accounts"))
    person, fee = PersonFactory(), _monthly_fee()

    sent = client.post(
        "/api/v1/payments/online/send-link/",
        {
            "person": str(person.id),
            "payment_type": str(fee.id),
            "billing_period": "2026-10-01",
            "amount": "2500.00",
        },
        format="json",
    )
    waiting = client.get("/api/v1/payments/online/")

    assert sent.status_code == 200, sent.data
    assert sent.data["status"] == "created"
    assert [row["id"] for row in waiting.data["results"]] == [sent.data["id"]]
    assert waiting.data["results"][0]["person_name"] == str(person)


@pytest.mark.django_db
def test_api_checkout_then_confirm_records_the_payment(seeded_roles):
    client = APIClient()
    client.force_authenticate(_user_with_role("administration"))
    person, fee = PersonFactory(), _monthly_fee()

    started = client.post(
        "/api/v1/payments/online/checkout/",
        {
            "person": str(person.id),
            "payment_type": str(fee.id),
            "billing_period": "2026-10-01",
            "amount": "2500.00",
        },
        format="json",
    )
    attempt_id = started.data["online_payment"]["id"]
    confirmed = client.post(
        f"/api/v1/payments/online/{attempt_id}/confirm/",
        {"payload": {"signature": "good", "payment_id": "pay_5"}},
        format="json",
    )

    assert started.status_code == 200, started.data
    assert confirmed.status_code == 200, confirmed.data
    assert confirmed.data["status"] == "paid"
    assert confirmed.data["payment"] is not None


@pytest.mark.django_db
def test_api_setup_reports_the_gateway(seeded_roles):
    client = APIClient()
    client.force_authenticate(_user_with_role("accounts"))

    response = client.get("/api/v1/payments/online/setup/")

    assert response.status_code == 200
    assert response.data == {"gateway": "fake", "label": "Fake Pay"}


@pytest.mark.django_db
def test_api_a_coach_cannot_collect_ledger_payments(seeded_roles):
    # docs/03-rbac.md: Coach holds nothing on `payment`.
    client = APIClient()
    client.force_authenticate(_user_with_role("coach"))

    response = client.post(
        "/api/v1/payments/online/send-link/",
        {"person": str(PersonFactory().id), "payment_type": str(_monthly_fee().id), "amount": "1"},
        format="json",
    )

    assert response.status_code == 403
    assert not OnlinePayment.objects.exists()
