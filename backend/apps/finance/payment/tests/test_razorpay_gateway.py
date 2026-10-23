"""The Razorpay adapter against a stubbed API — `_request` is patched, so
nothing here reaches Razorpay."""

import hashlib
import hmac
import json
from decimal import Decimal
from unittest import mock

import pytest

from apps.finance.payment.gateways import get_gateway
from apps.finance.payment.gateways.base import Customer, GatewayError

REQUEST = "apps.finance.payment.gateways.razorpay._request"
SECRET = "test_secret"


@pytest.fixture(autouse=True)
def razorpay_settings(settings):
    settings.PAYMENT_GATEWAY = "razorpay"
    settings.RAZORPAY_KEY_ID = "rzp_test_key"
    settings.RAZORPAY_KEY_SECRET = SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = "hook_secret"


def _sign(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def test_unconfigured_keys_mean_no_online_payments(settings):
    settings.RAZORPAY_KEY_SECRET = ""
    with pytest.raises(GatewayError):
        get_gateway()


def test_checkout_order_is_created_in_paise_with_window_options():
    with mock.patch(REQUEST, return_value={"id": "order_1", "amount": 500050}) as request:
        session = get_gateway().create_checkout(
            amount=Decimal("5000.50"),
            reference="APP-1",
            description="Admission fee",
            customer=Customer(name="Parent", mobile="+919800000001"),
            notes={},
        )

    assert request.call_args.args[:2] == ("POST", "/orders")
    assert request.call_args.args[2]["amount"] == 500050
    assert session.gateway_id == "order_1"
    assert session.client_options["key"] == "rzp_test_key"
    assert session.client_options["order_id"] == "order_1"
    assert session.client_options["prefill"]["contact"] == "+919800000001"


def test_a_correctly_signed_captured_payment_is_confirmed():
    payload = {
        "razorpay_order_id": "order_1",
        "razorpay_payment_id": "pay_1",
        "razorpay_signature": _sign(SECRET, "order_1|pay_1"),
    }
    payment = {"id": "pay_1", "order_id": "order_1", "amount": 500000, "status": "captured"}
    with mock.patch(REQUEST, return_value=payment):
        payment_id = get_gateway().confirm_checkout(
            gateway_id="order_1", amount=Decimal("5000"), payload=payload
        )

    assert payment_id == "pay_1"


def test_a_bad_signature_is_refused_without_calling_razorpay():
    payload = {
        "razorpay_order_id": "order_1",
        "razorpay_payment_id": "pay_1",
        "razorpay_signature": "forged",
    }
    with mock.patch(REQUEST) as request, pytest.raises(GatewayError):
        get_gateway().confirm_checkout(
            gateway_id="order_1", amount=Decimal("5000"), payload=payload
        )

    request.assert_not_called()


def test_a_payment_for_the_wrong_amount_is_refused():
    payload = {
        "razorpay_order_id": "order_1",
        "razorpay_payment_id": "pay_1",
        "razorpay_signature": _sign(SECRET, "order_1|pay_1"),
    }
    payment = {"id": "pay_1", "order_id": "order_1", "amount": 100, "status": "captured"}
    with mock.patch(REQUEST, return_value=payment), pytest.raises(GatewayError):
        get_gateway().confirm_checkout(
            gateway_id="order_1", amount=Decimal("5000"), payload=payload
        )


def test_an_authorized_payment_is_captured():
    payload = {
        "razorpay_order_id": "order_1",
        "razorpay_payment_id": "pay_1",
        "razorpay_signature": _sign(SECRET, "order_1|pay_1"),
    }
    payment = {"id": "pay_1", "order_id": "order_1", "amount": 500000, "status": "authorized"}
    with mock.patch(REQUEST, side_effect=[payment, {}]) as request:
        get_gateway().confirm_checkout(
            gateway_id="order_1", amount=Decimal("5000"), payload=payload
        )

    assert request.call_args.args[:2] == ("POST", "/payments/pay_1/capture")


@pytest.mark.parametrize(
    "razorpay_status,state",
    [("created", "created"), ("paid", "paid"), ("cancelled", "cancelled"), ("expired", "expired")],
)
def test_link_status_is_mapped(razorpay_status, state):
    link = {"status": razorpay_status, "payments": [{"payment_id": "pay_3"}]}
    with mock.patch(REQUEST, return_value=link):
        status = get_gateway().link_status(gateway_id="plink_1")

    assert status.state == state
    if state == "paid":
        assert status.payment_id == "pay_3"


def test_a_signed_link_paid_webhook_is_parsed():
    body = json.dumps(
        {
            "event": "payment_link.paid",
            "payload": {
                "payment_link": {"entity": {"id": "plink_1"}},
                "payment": {"entity": {"id": "pay_4"}},
            },
        }
    ).encode()
    signature = hmac.new(b"hook_secret", body, hashlib.sha256).hexdigest()

    event = get_gateway().parse_webhook(body=body, headers={"X-Razorpay-Signature": signature})

    assert (event.gateway_id, event.payment_id) == ("plink_1", "pay_4")


def test_an_unsigned_webhook_is_refused():
    with pytest.raises(GatewayError):
        get_gateway().parse_webhook(body=b"{}", headers={"X-Razorpay-Signature": "nope"})
