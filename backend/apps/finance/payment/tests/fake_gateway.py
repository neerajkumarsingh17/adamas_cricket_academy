"""A stand-in payment gateway for tests — online collection must not care
which provider is behind it. The `fake_gateway` fixture (backend/
conftest.py) switches settings.PAYMENT_GATEWAY to it for a test.
"""

from apps.finance.payment.gateways.base import (
    CheckoutSession,
    GatewayError,
    GatewayStatus,
    LinkSession,
    PaymentGateway,
    WebhookEvent,
)


class FakeGateway(PaymentGateway):
    name = "fake"
    label = "Fake Pay"
    counter = 0
    # gateway_id -> GatewayStatus the "gateway" reports
    statuses: dict[str, GatewayStatus] = {}
    cancelled: list[str] = []

    def is_configured(self):
        return True

    def _next(self, prefix):
        FakeGateway.counter += 1
        return f"{prefix}_{FakeGateway.counter}"

    def create_checkout(self, *, amount, reference, description, customer, notes):
        gateway_id = self._next("order")
        return CheckoutSession(gateway_id=gateway_id, client_options={"amount": str(amount)})

    def confirm_checkout(self, *, gateway_id, amount, payload):
        if payload.get("signature") != "good":
            raise GatewayError("bad signature")
        return payload["payment_id"]

    def checkout_status(self, *, gateway_id, amount):
        return self.statuses.get(gateway_id, GatewayStatus(state="created"))

    def create_link(self, *, amount, reference, description, customer, expires_in_days, notes):
        gateway_id = self._next("plink")
        return LinkSession(gateway_id=gateway_id, short_url=f"https://pay.example/{gateway_id}")

    def link_status(self, *, gateway_id):
        return self.statuses.get(gateway_id, GatewayStatus(state="created"))

    def cancel_link(self, *, gateway_id):
        self.cancelled.append(gateway_id)

    def resend_link(self, *, gateway_id):
        pass

    def parse_webhook(self, *, body, headers):
        if headers.get("X-Fake-Signature") != "good":
            raise GatewayError("bad signature")
        gateway_id, payment_id = body.decode().split(":")
        return WebhookEvent(gateway_id=gateway_id, payment_id=payment_id)
