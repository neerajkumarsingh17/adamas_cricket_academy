"""The contract every online payment gateway adapter implements.

Everything outside this package — admission services, views, models,
the frontend — talks only to `PaymentGateway` and the plain dataclasses
below, never to a provider's API. Switching provider means writing one
new adapter module next to razorpay.py and registering it in
`__init__.py`; nothing else changes.

Amounts cross this boundary as `Decimal` rupees; converting to whatever
unit a provider wants (paise for Razorpay) is the adapter's job.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from rest_framework import status
from rest_framework.exceptions import APIException


class GatewayError(APIException):
    """The gateway refused the call or couldn't be reached. 502: the
    request to us was fine, the payment gateway behind it wasn't."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "The payment gateway could not complete the request. Try again."
    default_code = "payment_gateway_error"


@dataclass(frozen=True)
class Customer:
    name: str
    mobile: str


@dataclass(frozen=True)
class CheckoutSession:
    """A payment window the desk opens in the browser. `client_options`
    is handed to the frontend as-is — the matching entry in
    frontend/src/lib/paymentGateways opens the provider's own window with
    it and posts back whatever the provider returns."""

    gateway_id: str
    client_options: dict


@dataclass(frozen=True)
class LinkSession:
    gateway_id: str
    short_url: str


@dataclass(frozen=True)
class GatewayStatus:
    """Where a checkout or link stands at the gateway right now. `state`
    uses OnlinePaymentStatus's vocabulary: created/paid/cancelled/expired."""

    state: str
    payment_id: str = ""


@dataclass(frozen=True)
class WebhookEvent:
    """A gateway telling us a checkout or link was paid."""

    gateway_id: str
    payment_id: str
    extra: dict = field(default_factory=dict)


class PaymentGateway(ABC):
    name: str  # matches settings.PAYMENT_GATEWAY, stored on OnlinePayment.gateway
    label: str  # shown to staff, e.g. "Razorpay"

    @abstractmethod
    def is_configured(self) -> bool: ...

    # --- Desk checkout --- #

    @abstractmethod
    def create_checkout(
        self,
        *,
        amount: Decimal,
        reference: str,
        description: str,
        customer: Customer,
        notes: dict,
    ) -> CheckoutSession: ...

    @abstractmethod
    def confirm_checkout(self, *, gateway_id: str, amount: Decimal, payload: dict) -> str:
        """Verify what the browser posted back after paying (signature,
        amount, that the money was actually taken) and return the
        gateway's payment id. Raise GatewayError if any check fails."""

    @abstractmethod
    def checkout_status(self, *, gateway_id: str, amount: Decimal) -> GatewayStatus:
        """For a checkout whose window was closed before the browser could
        report back — has it been paid anyway?"""

    # --- Payment links --- #

    @abstractmethod
    def create_link(
        self,
        *,
        amount: Decimal,
        reference: str,
        description: str,
        customer: Customer,
        expires_in_days: int,
        notes: dict,
    ) -> LinkSession: ...

    @abstractmethod
    def link_status(self, *, gateway_id: str) -> GatewayStatus: ...

    @abstractmethod
    def cancel_link(self, *, gateway_id: str) -> None: ...

    @abstractmethod
    def resend_link(self, *, gateway_id: str) -> None: ...

    # --- Webhooks --- #

    @abstractmethod
    def parse_webhook(self, *, body: bytes, headers) -> WebhookEvent | None:
        """A verified "this was paid" event, or None for events we don't
        act on. Raise GatewayError if the signature doesn't check out."""
