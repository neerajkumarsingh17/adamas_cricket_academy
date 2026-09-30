from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler as drf_exception_handler

from .middleware import get_request_id


def exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER: reshapes every non-2xx response into the
    project envelope — {code, message, field_errors, request_id} — per
    docs/02-api-spec.md.
    """
    if isinstance(exc, DjangoValidationError):
        # Model.full_clean() raises Django's own ValidationError, not
        # DRF's — services.record_payment/set_fee_lines/Person.save()
        # (the only three full_clean() call sites in the codebase) all
        # rely on it to reject bad data. drf_exception_handler below only
        # recognises APIException/Http404/PermissionDenied and returns
        # None for anything else, which sends this straight past the
        # envelope to Django's raw 500 page — caught 2026-09-29 recording
        # a negative payment amount, which full_clean()'s MinValueValidator
        # correctly rejects but as an *uncaught* rejection. Re-wrapped as
        # DRF's ValidationError here so it takes the exact path a
        # serializer-level failure already does.
        exc = DRFValidationError(detail=_django_validation_detail(exc))

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    request = context.get("request")
    request_id = getattr(request, "request_id", "") if request else ""
    request_id = request_id or get_request_id()

    code = getattr(exc, "default_code", "error")
    message, field_errors = _split_detail(response.data)

    response.data = {
        "code": code,
        "message": message,
        "field_errors": field_errors,
        "request_id": request_id,
    }
    return response


def _django_validation_detail(exc: DjangoValidationError) -> dict | list:
    if hasattr(exc, "error_dict"):
        return {field: [str(m) for m in messages] for field, messages in exc.message_dict.items()}
    return list(exc.messages)


def _split_detail(data: object) -> tuple[str, dict]:
    if isinstance(data, dict) and set(data) == {"detail"}:
        return str(data["detail"]), {}
    if isinstance(data, dict):
        field_errors = {
            field: [str(e) for e in errors] if isinstance(errors, list) else [str(errors)]
            for field, errors in data.items()
        }
        return "Validation failed.", field_errors
    if isinstance(data, list):
        return "; ".join(str(e) for e in data), {}
    return str(data), {}
