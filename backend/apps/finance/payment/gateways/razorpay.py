"""Razorpay adapter for `PaymentGateway` — orders + Checkout at the desk,
Payment Links for the parent, signed webhooks.

Standard library only (urllib + hmac), no `razorpay` SDK: every call is
one authenticated JSON request, and the SDK would add a dependency (and
its own `requests` pin) for nothing more. `_request()` is the single seam
tests patch — the test suite never reaches Razorpay.

Settings: RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET.
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from .base import (
    CheckoutSession,
    GatewayError,
    GatewayStatus,
    LinkSession,
    PaymentGateway,
    WebhookEvent,
)

API_BASE = "https://api.razorpay.com/v1"
TIMEOUT_SECONDS = 20
BRAND_COLOUR = "#E87722"  # the academy orange, for Razorpay's own window


def _paise(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def _request(method: str, path: str, body: dict | None = None) -> dict:
    credentials = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Basic {base64.b64encode(credentials).decode()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            description = json.loads(exc.read())["error"]["description"]
        except (ValueError, KeyError, TypeError):
            description = exc.reason
        raise GatewayError(f"Razorpay: {description}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise GatewayError("Could not reach Razorpay. Check the connection and try again.") from exc


class RazorpayGateway(PaymentGateway):
    name = "razorpay"
    label = "Razorpay"

    def is_configured(self) -> bool:
        return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)

    # --- Desk checkout --- #

    def create_checkout(self, *, amount, reference, description, customer, notes):
        order = _request(
            "POST",
            "/orders",
            {
                "amount": _paise(amount),
                "currency": "INR",
                "receipt": reference[:40],
                "notes": notes,
            },
        )
        return CheckoutSession(
            gateway_id=order["id"],
            # Exactly the options Razorpay's checkout.js takes.
            client_options={
                "key": settings.RAZORPAY_KEY_ID,
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": "INR",
                "name": "Adamas Cricket Academy",
                "description": description,
                "prefill": {"name": customer.name, "contact": customer.mobile},
                "notes": notes,
                "theme": {"color": BRAND_COLOUR},
            },
        )

    def confirm_checkout(self, *, gateway_id, amount, payload):
        payment_id = str(payload.get("razorpay_payment_id", ""))
        signature = str(payload.get("razorpay_signature", ""))
        if str(payload.get("razorpay_order_id", "")) != gateway_id or not payment_id:
            raise GatewayError("The payment response does not belong to this order.")
        expected = _hmac_hex(settings.RAZORPAY_KEY_SECRET, f"{gateway_id}|{payment_id}".encode())
        if not hmac.compare_digest(expected, signature):
            raise GatewayError("The payment response failed signature verification.")
        payment = _request("GET", f"/payments/{payment_id}")
        if payment.get("order_id") != gateway_id or payment.get("amount") != _paise(amount):
            raise GatewayError("The payment amount does not match the fee due.")
        self._ensure_captured(payment)
        return payment_id

    def checkout_status(self, *, gateway_id, amount):
        items = _request("GET", f"/orders/{gateway_id}/payments").get("items", [])
        for payment in items:
            if payment.get("status") in ("captured", "authorized") and payment.get(
                "amount"
            ) == _paise(amount):
                self._ensure_captured(payment)
                return GatewayStatus(state="paid", payment_id=payment["id"])
        return GatewayStatus(state="created")

    def _ensure_captured(self, payment: dict) -> None:
        # Accounts with auto-capture off hand back `authorized` money that
        # is refunded after a few days unless we capture it.
        if payment.get("status") == "authorized":
            _request(
                "POST",
                f"/payments/{payment['id']}/capture",
                {"amount": payment["amount"], "currency": "INR"},
            )
        elif payment.get("status") != "captured":
            raise GatewayError(f"The payment is {payment.get('status', 'not complete')}.")

    # --- Payment links --- #

    def create_link(self, *, amount, reference, description, customer, expires_in_days, notes):
        link = _request(
            "POST",
            "/payment_links",
            {
                "amount": _paise(amount),
                "currency": "INR",
                "reference_id": reference[:40],
                "description": description[:2048],
                "customer": {"name": customer.name, "contact": customer.mobile},
                "notify": {"sms": True, "email": False},
                "reminder_enable": True,
                "expire_by": int(time.time()) + expires_in_days * 86_400,
                "notes": notes,
            },
        )
        return LinkSession(gateway_id=link["id"], short_url=link["short_url"])

    def link_status(self, *, gateway_id):
        link = _request("GET", f"/payment_links/{gateway_id}")
        state = link.get("status")
        if state == "paid":
            payments = link.get("payments") or []
            return GatewayStatus(
                state="paid", payment_id=payments[0].get("payment_id", "") if payments else ""
            )
        if state in ("cancelled", "expired"):
            return GatewayStatus(state=state)
        return GatewayStatus(state="created")

    def cancel_link(self, *, gateway_id):
        _request("POST", f"/payment_links/{gateway_id}/cancel")

    def resend_link(self, *, gateway_id):
        _request("POST", f"/payment_links/{gateway_id}/notify_by/sms")

    # --- Webhooks --- #

    def parse_webhook(self, *, body, headers):
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        signature = headers.get("X-Razorpay-Signature", "")
        if not secret or not hmac.compare_digest(_hmac_hex(secret, body), signature):
            raise GatewayError("Webhook signature verification failed.")

        event = json.loads(body)
        payload = event.get("payload", {})
        payment = payload.get("payment", {}).get("entity", {})
        if event.get("event") == "payment_link.paid":
            link = payload.get("payment_link", {}).get("entity", {})
            return WebhookEvent(gateway_id=link.get("id", ""), payment_id=payment.get("id", ""))
        if event.get("event") in ("order.paid", "payment.captured") and payment.get("order_id"):
            return WebhookEvent(gateway_id=payment["order_id"], payment_id=payment.get("id", ""))
        return None
