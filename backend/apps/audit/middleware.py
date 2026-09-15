import contextvars
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

_current_request_var: contextvars.ContextVar[HttpRequest | None] = contextvars.ContextVar(
    "current_request", default=None
)


def get_current_request() -> HttpRequest | None:
    return _current_request_var.get()


class CurrentRequestMiddleware:
    """Makes the in-flight request available to apps.audit.signals, which
    runs inside model save()/delete() and has no request object of its own.

    Stores the request itself (not `request.user`) because DRF's JWT
    authentication resolves `request.user` lazily on first access — by a
    ModuleScopedViewSet's `check_permissions()`, well before any save() a
    view goes on to do — so reading `request.user` lazily, at signal-fire
    time rather than middleware-entry time, is what makes the actor come
    out correct instead of always-anonymous.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        token = _current_request_var.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request_var.reset(token)
