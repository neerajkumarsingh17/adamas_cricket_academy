"""Online payment gateways. `get_gateway()` is the only entry point the
rest of the codebase uses; settings.PAYMENT_GATEWAY picks the adapter.

To add a provider: write `<name>.py` implementing base.PaymentGateway,
add it to GATEWAYS below, add the matching opener in
frontend/src/lib/paymentGateways, and set PAYMENT_GATEWAY=<name> plus
that provider's keys in .env.
"""

from django.conf import settings

from .base import GatewayError, PaymentGateway
from .razorpay import RazorpayGateway

GATEWAYS: dict[str, type[PaymentGateway]] = {
    RazorpayGateway.name: RazorpayGateway,
}

__all__ = ["GATEWAYS", "GatewayError", "PaymentGateway", "get_gateway", "online_enabled"]


def get_gateway(name: str | None = None) -> PaymentGateway:
    """The configured gateway — or, given `name`, the one a stored
    OnlinePayment went through (it may predate a provider switch)."""
    name = name or settings.PAYMENT_GATEWAY
    gateway_cls = GATEWAYS.get(name)
    if gateway_cls is None:
        raise GatewayError("Online payments are not set up.")
    gateway = gateway_cls()
    if not gateway.is_configured():
        raise GatewayError(f"{gateway.label} keys are not configured.")
    return gateway


def online_enabled() -> PaymentGateway | None:
    try:
        return get_gateway()
    except GatewayError:
        return None
