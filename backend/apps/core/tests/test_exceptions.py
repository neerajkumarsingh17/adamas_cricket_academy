from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import exception_handler


def test_envelope_for_detail_style_exception():
    response = exception_handler(NotFound(), {"request": None})

    assert response.status_code == 404
    assert response.data == {
        "code": "not_found",
        "message": "Not found.",
        "field_errors": {},
        "request_id": "",
    }


def test_envelope_for_field_validation_error():
    exc = ValidationError({"mobile": ["This field is required."]})

    response = exception_handler(exc, {"request": None})

    assert response.status_code == 400
    assert response.data["code"] == "invalid"
    assert response.data["field_errors"] == {"mobile": ["This field is required."]}
    assert response.data["message"] == "Validation failed."


def test_unhandled_exception_returns_none():
    assert exception_handler(ValueError("boom"), {"request": None}) is None
