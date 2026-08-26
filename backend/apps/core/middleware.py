import contextvars
import logging
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

REQUEST_ID_HEADER = "X-Request-ID"

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_var.get()


class RequestIDMiddleware:
    """Generates a request id (or reuses an inbound one), makes it available
    to views and the exception handler via `request.request_id`, echoes it
    on the response header, and exposes it to logging via `get_request_id()`
    / `RequestIDLogFilter`.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]
        token = _request_id_var.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _request_id_var.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        return response


class RequestIDLogFilter(logging.Filter):
    """Attach `request_id` to log records — reference it from a formatter as
    `%(request_id)s` once LOGGING is configured.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
