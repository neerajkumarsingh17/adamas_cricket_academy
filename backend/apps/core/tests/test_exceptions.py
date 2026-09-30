from django.core.exceptions import ValidationError as DjangoValidationError
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


def test_envelope_for_model_full_clean_field_error():
    """Payment.full_clean() (services.record_payment) raises exactly this
    shape for a negative amount — MinValueValidator(0) rejecting it via
    Model.clean_fields(), not Payment.clean()'s own hand-written errors.
    Left untranslated this fell through drf_exception_handler (which only
    recognises DRF's own ValidationError) straight to Django's raw 500
    page instead of the API's error envelope.
    """
    exc = DjangoValidationError({"amount": ["Ensure this value is greater than or equal to 0."]})

    response = exception_handler(exc, {"request": None})

    assert response.status_code == 400
    assert response.data["field_errors"] == {
        "amount": ["Ensure this value is greater than or equal to 0."]
    }
    assert response.data["message"] == "Validation failed."


def test_envelope_for_model_full_clean_non_field_error():
    """Person.save() (apps/people/models.py:115) and Payment.clean()'s own
    hand-written checks can raise a plain (non-field) ValidationError too
    — Django files that under "__all__", not a real field name.
    """
    exc = DjangoValidationError("Cannot be in the future.")

    response = exception_handler(exc, {"request": None})

    assert response.status_code == 400
    assert response.data["field_errors"] == {}
    assert response.data["message"] == "Cannot be in the future."
