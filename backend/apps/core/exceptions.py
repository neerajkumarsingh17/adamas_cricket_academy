from rest_framework.views import exception_handler as drf_exception_handler

from .middleware import get_request_id


def exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER: reshapes every non-2xx response into the
    project envelope — {code, message, field_errors, request_id} — per
    docs/02-api-spec.md.
    """
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
