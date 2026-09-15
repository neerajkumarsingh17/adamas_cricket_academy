from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.iam.services import generate_and_store_otp, verify_otp
from apps.people.tests.factories import PersonFactory

from .factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_otp_login_works_end_to_end_against_stubbed_sms_backend(api_client):
    person = PersonFactory(mobile="9876543210")
    UserFactory(person=person)

    with patch("apps.iam.views.send_otp_sms") as mock_send:
        request_response = api_client.post("/api/v1/auth/otp/request/", {"mobile": "9876543210"})
    assert request_response.status_code == 200

    mock_send.assert_called_once()
    sent_mobile, otp = mock_send.call_args[0]
    assert sent_mobile == "+919876543210"
    assert len(otp) == 6

    verify_response = api_client.post(
        "/api/v1/auth/otp/verify/", {"mobile": "9876543210", "otp": otp}
    )

    assert verify_response.status_code == 200
    assert "access" in verify_response.data
    assert "refresh" in verify_response.data


@pytest.mark.django_db
def test_otp_verify_rejects_wrong_code(api_client):
    person = PersonFactory(mobile="9876543210")
    UserFactory(person=person)

    with patch("apps.iam.views.send_otp_sms"):
        api_client.post("/api/v1/auth/otp/request/", {"mobile": "9876543210"})

    response = api_client.post(
        "/api/v1/auth/otp/verify/", {"mobile": "9876543210", "otp": "000000"}
    )

    assert response.status_code == 401


def test_otp_is_single_use():
    otp = generate_and_store_otp("+919876543210")

    assert verify_otp("+919876543210", otp) is True
    assert verify_otp("+919876543210", otp) is False


@pytest.mark.django_db
def test_otp_verify_fails_when_no_user_linked_to_mobile(api_client):
    PersonFactory(mobile="9876543210")  # no User account linked

    with patch("apps.iam.views.send_otp_sms") as mock_send:
        api_client.post("/api/v1/auth/otp/request/", {"mobile": "9876543210"})
    otp = mock_send.call_args[0][1]

    response = api_client.post("/api/v1/auth/otp/verify/", {"mobile": "9876543210", "otp": otp})

    assert response.status_code == 401


@pytest.mark.django_db
def test_fourth_otp_request_in_ten_minutes_is_throttled(api_client):
    person = PersonFactory(mobile="9876543210")
    UserFactory(person=person)

    with patch("apps.iam.views.send_otp_sms"):
        for _ in range(3):
            response = api_client.post("/api/v1/auth/otp/request/", {"mobile": "9876543210"})
            assert response.status_code == 200

        fourth_response = api_client.post("/api/v1/auth/otp/request/", {"mobile": "9876543210"})

    assert fourth_response.status_code == 429


@pytest.mark.django_db
def test_otp_rate_limit_is_keyed_by_normalised_mobile(api_client):
    """ "9876543210" and "+91-98765-43210" are the same number — the limit
    must be shared, not bypassable by varying the input format.
    """
    person = PersonFactory(mobile="9876543210")
    UserFactory(person=person)

    with patch("apps.iam.views.send_otp_sms"):
        api_client.post("/api/v1/auth/otp/request/", {"mobile": "9876543210"})
        api_client.post("/api/v1/auth/otp/request/", {"mobile": "+91-98765-43210"})
        api_client.post("/api/v1/auth/otp/request/", {"mobile": "09876543210"})

        fourth_response = api_client.post("/api/v1/auth/otp/request/", {"mobile": "919876543210"})

    assert fourth_response.status_code == 429
