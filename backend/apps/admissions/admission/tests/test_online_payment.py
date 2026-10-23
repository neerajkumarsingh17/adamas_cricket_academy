"""Online fee collection, end to end through the admission flow, against a
fake gateway — the flow must not care which provider is behind it."""

import datetime

import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.admissions.admission import online_payment, services
from apps.admissions.admission.models import AdmissionStep
from apps.core.tests.factories import ConsentTypeFactory, FeeHeadFactory
from apps.finance.fee.tests.factories import AdmissionFeeLineFactory
from apps.finance.payment import online
from apps.finance.payment.gateways.base import GatewayError, GatewayStatus
from apps.finance.payment.models import OnlinePayment, OnlinePaymentStatus, PaymentMode
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory

from .factories import AdmissionIntakeFactory, DirectAdmissionFactory

pytestmark = pytest.mark.usefixtures("fake_gateway")


def _ready_admission(fee="5000.00"):
    admission = DirectAdmissionFactory()
    AdmissionIntakeFactory(admission=admission)
    consent = ConsentTypeFactory(is_mandatory=True)
    services.record_consents(
        admission,
        decisions=[{"consent_type": consent, "granted": True}],
        declared_by_name="Guardian Name",
    )
    AdmissionFeeLineFactory(
        admission=admission, fee_head=FeeHeadFactory(is_mandatory=True), amount=fee
    )
    return admission


def _paid_through_checkout(admission, user):
    checkout = online_payment.start_checkout(admission, user=user)
    gateway_id = OnlinePayment.objects.get(admission=admission).gateway_id
    online_payment.confirm_checkout(
        admission, gateway_id=gateway_id, payload={"signature": "good", "payment_id": "pay_1"}
    )
    return checkout


# --- Desk checkout --- #


@pytest.mark.django_db
def test_checkout_returns_the_gateways_window_options():
    admission = _ready_admission()

    checkout = online_payment.start_checkout(admission, user=UserFactory())

    assert checkout == {"gateway": "fake", "options": {"amount": "5000.00"}}
    attempt = OnlinePayment.objects.get(admission=admission)
    assert (attempt.kind, attempt.gateway, attempt.status) == ("checkout", "fake", "created")


@pytest.mark.django_db
def test_a_confirmed_checkout_records_and_verifies_the_payment():
    admission = _ready_admission()
    desk = UserFactory()

    _paid_through_checkout(admission, desk)

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.PAYMENT_VERIFIED  # no Accounts step
    payment = admission.payment
    assert payment.payment_mode == PaymentMode.GATEWAY
    assert payment.reference_no == "pay_1"
    assert payment.recorded_by == desk
    assert payment.verified_at is not None
    assert "Fake Pay" in payment.verification_note
    assert OnlinePayment.objects.get(admission=admission).status == OnlinePaymentStatus.PAID


@pytest.mark.django_db
def test_a_forged_checkout_response_records_nothing():
    admission = _ready_admission()
    online_payment.start_checkout(admission, user=UserFactory())
    gateway_id = OnlinePayment.objects.get(admission=admission).gateway_id

    with pytest.raises(GatewayError):
        online_payment.confirm_checkout(
            admission, gateway_id=gateway_id, payload={"signature": "forged", "payment_id": "x"}
        )

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.DRAFT
    assert not hasattr(admission, "payment")


@pytest.mark.django_db
def test_the_same_payment_reported_twice_is_recorded_once():
    admission = _ready_admission()
    _paid_through_checkout(admission, UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)

    online_payment.confirm_checkout(
        admission,
        gateway_id=attempt.gateway_id,
        payload={"signature": "good", "payment_id": "pay_1"},
    )
    online.handle_webhook(
        "fake", body=f"{attempt.gateway_id}:pay_1".encode(), headers={"X-Fake-Signature": "good"}
    )

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.PAYMENT_VERIFIED
    assert attempt.admission.payment.receipt_no  # exactly one AdmissionPayment (OneToOne)


@pytest.mark.django_db
def test_nothing_is_charged_before_the_admission_is_ready():
    admission = DirectAdmissionFactory()
    AdmissionIntakeFactory(admission=admission)
    ConsentTypeFactory(is_mandatory=True)  # never granted
    AdmissionFeeLineFactory(admission=admission, amount="5000.00")

    with pytest.raises(ValidationError):
        online_payment.start_checkout(admission, user=UserFactory())

    assert not OnlinePayment.objects.exists()


@pytest.mark.django_db
def test_a_window_closed_after_paying_is_picked_up_on_the_next_attempt(fake_gateway):
    admission = _ready_admission()
    online_payment.start_checkout(admission, user=UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)
    fake_gateway.statuses[attempt.gateway_id] = GatewayStatus(state="paid", payment_id="pay_9")

    checkout = online_payment.start_checkout(admission, user=UserFactory())

    assert checkout is None  # no second window — it was already paid
    admission.refresh_from_db()
    assert admission.step == AdmissionStep.PAYMENT_VERIFIED
    assert admission.payment.reference_no == "pay_9"


# --- Payment links --- #


@pytest.mark.django_db
def test_sending_a_link_records_where_it_went():
    admission = _ready_admission()

    online_payment.send_link(admission, user=UserFactory())

    attempt = OnlinePayment.objects.get(admission=admission)
    assert attempt.kind == "link"
    assert attempt.short_url.startswith("https://pay.example/plink_")
    assert attempt.sent_to == admission.intake.guardian_mobile
    admission.refresh_from_db()
    assert admission.step == AdmissionStep.DRAFT  # waits for the parent


@pytest.mark.django_db
def test_a_paid_link_moves_the_admission_on_when_checked(fake_gateway):
    admission = _ready_admission()
    online_payment.send_link(admission, user=UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)
    fake_gateway.statuses[attempt.gateway_id] = GatewayStatus(state="paid", payment_id="pay_5")

    assert online_payment.sync(admission) is True

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.PAYMENT_VERIFIED
    assert admission.payment.reference_no == "pay_5"


@pytest.mark.django_db
def test_a_paid_link_moves_the_admission_on_by_webhook():
    admission = _ready_admission()
    online_payment.send_link(admission, user=UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)

    online.handle_webhook(
        "fake", body=f"{attempt.gateway_id}:pay_7".encode(), headers={"X-Fake-Signature": "good"}
    )

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.PAYMENT_VERIFIED


@pytest.mark.django_db
def test_a_new_link_or_window_cancels_the_open_link(fake_gateway):
    admission = _ready_admission()
    online_payment.send_link(admission, user=UserFactory())
    first = OnlinePayment.objects.get(admission=admission)

    online_payment.start_checkout(admission, user=UserFactory())

    first.refresh_from_db()
    assert first.status == OnlinePaymentStatus.CANCELLED
    assert fake_gateway.cancelled == [first.gateway_id]


@pytest.mark.django_db
def test_an_expired_link_is_marked_expired(fake_gateway):
    admission = _ready_admission()
    online_payment.send_link(admission, user=UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)
    fake_gateway.statuses[attempt.gateway_id] = GatewayStatus(state="expired")

    assert online_payment.sync(admission) is False

    attempt.refresh_from_db()
    assert attempt.status == OnlinePaymentStatus.EXPIRED


@pytest.mark.django_db
def test_recording_cash_cancels_an_open_link(fake_gateway):
    admission = _ready_admission()
    online_payment.send_link(admission, user=UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)

    services.record_direct_payment(
        admission, payment_mode="cash", payment_date=datetime.date.today(), user=UserFactory()
    )

    attempt.refresh_from_db()
    assert attempt.status == OnlinePaymentStatus.CANCELLED
    assert fake_gateway.cancelled == [attempt.gateway_id]


@pytest.mark.django_db
def test_paying_online_after_cash_was_recorded_is_flagged_for_refund():
    admission = _ready_admission()
    online_payment.send_link(admission, user=UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)
    services.record_direct_payment(
        admission, payment_mode="cash", payment_date=datetime.date.today(), user=UserFactory()
    )

    online.handle_webhook(
        "fake", body=f"{attempt.gateway_id}:pay_8".encode(), headers={"X-Fake-Signature": "good"}
    )

    attempt.refresh_from_db()
    assert attempt.status == OnlinePaymentStatus.PAID
    assert "Refund" in attempt.note
    admission.refresh_from_db()
    assert admission.payment.payment_mode == "cash"  # cash record untouched


@pytest.mark.django_db
def test_a_forged_webhook_is_refused():
    admission = _ready_admission()
    online_payment.send_link(admission, user=UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)

    with pytest.raises(GatewayError):
        online.handle_webhook("fake", body=f"{attempt.gateway_id}:pay_x".encode(), headers={})

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.DRAFT


# --- API --- #


def _desk_user():
    user = UserFactory()
    UserRole.objects.create(
        user=user,
        role=Role.objects.get(code="administration"),
        valid_from=datetime.date(2020, 1, 1),
    )
    return user


@pytest.mark.django_db
def test_api_checkout_then_confirm(seeded_roles):
    admission = _ready_admission()
    client = APIClient()
    client.force_authenticate(_desk_user())

    started = client.post(f"/api/v1/admissions/{admission.id}/online-payment/checkout/")
    assert started.status_code == 200, started.data
    gateway_id = OnlinePayment.objects.get(admission=admission).gateway_id

    confirmed = client.post(
        f"/api/v1/admissions/{admission.id}/online-payment/confirm/",
        {"gateway_id": gateway_id, "payload": {"signature": "good", "payment_id": "pay_2"}},
        format="json",
    )

    assert confirmed.status_code == 200, confirmed.data
    assert confirmed.data["step"] == AdmissionStep.PAYMENT_VERIFIED
    assert confirmed.data["direct_payment"]["reference_no"] == "pay_2"
    assert confirmed.data["online_payment"]["status"] == "paid"


@pytest.mark.django_db
def test_api_a_role_without_admission_add_cannot_collect_fees(seeded_roles):
    # Same permission as recording a cash payment: `admission`/`add`
    # (docs/03-rbac.md). Medical holds nothing on admissions.
    admission = _ready_admission()
    medical = UserFactory()
    UserRole.objects.create(
        user=medical,
        role=Role.objects.get(code="medical_team"),
        valid_from=datetime.date(2020, 1, 1),
    )
    client = APIClient()
    client.force_authenticate(medical)

    response = client.post(f"/api/v1/admissions/{admission.id}/online-payment/send-link/")

    assert response.status_code == 403
    assert not OnlinePayment.objects.exists()


@pytest.mark.django_db
def test_api_webhook_is_public_but_signature_checked(seeded_roles):
    admission = _ready_admission()
    online_payment.send_link(admission, user=UserFactory())
    attempt = OnlinePayment.objects.get(admission=admission)
    client = APIClient()

    forged = client.post(
        "/api/v1/payments/gateway/fake/webhook/",
        data=f"{attempt.gateway_id}:pay_1",
        content_type="text/plain",
    )
    signed = client.post(
        "/api/v1/payments/gateway/fake/webhook/",
        data=f"{attempt.gateway_id}:pay_1",
        content_type="text/plain",
        HTTP_X_FAKE_SIGNATURE="good",
    )

    assert forged.status_code == 502
    assert signed.status_code == 200
    admission.refresh_from_db()
    assert admission.step == AdmissionStep.PAYMENT_VERIFIED


@pytest.mark.django_db
def test_bootstrap_says_which_gateway_is_on(seeded_roles):
    client = APIClient()
    client.force_authenticate(_desk_user())

    response = client.get("/api/v1/admissions/direct/bootstrap/")

    assert response.data["online_payment"] == {"gateway": "fake", "label": "Fake Pay"}
