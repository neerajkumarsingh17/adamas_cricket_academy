import pytest
from rest_framework.test import APIClient

from .factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_login_with_correct_password_returns_access_and_refresh(api_client):
    user = UserFactory()
    user.set_password("s3cret-pass")
    user.save()

    response = api_client.post(
        "/api/v1/auth/login/", {"login_id": user.login_id, "password": "s3cret-pass"}
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_login_with_wrong_password_is_rejected(api_client):
    user = UserFactory()
    user.set_password("s3cret-pass")
    user.save()

    response = api_client.post(
        "/api/v1/auth/login/", {"login_id": user.login_id, "password": "wrong"}
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_login_stamps_last_login_at(api_client):
    user = UserFactory()
    user.set_password("s3cret-pass")
    user.save()
    assert user.last_login_at is None

    api_client.post("/api/v1/auth/login/", {"login_id": user.login_id, "password": "s3cret-pass"})

    user.refresh_from_db()
    assert user.last_login_at is not None


@pytest.mark.django_db
def test_reused_refresh_token_is_rejected(api_client):
    """The Check: rotating refresh, old token blacklisted on use."""
    user = UserFactory()
    user.set_password("s3cret-pass")
    user.save()

    login_response = api_client.post(
        "/api/v1/auth/login/", {"login_id": user.login_id, "password": "s3cret-pass"}
    )
    original_refresh = login_response.data["refresh"]

    first_refresh_response = api_client.post("/api/v1/auth/refresh/", {"refresh": original_refresh})
    assert first_refresh_response.status_code == 200
    assert first_refresh_response.data["refresh"] != original_refresh

    reused_response = api_client.post("/api/v1/auth/refresh/", {"refresh": original_refresh})

    assert reused_response.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_the_refresh_token(api_client):
    user = UserFactory()
    user.set_password("s3cret-pass")
    user.save()

    login_response = api_client.post(
        "/api/v1/auth/login/", {"login_id": user.login_id, "password": "s3cret-pass"}
    )
    refresh_token = login_response.data["refresh"]

    logout_response = api_client.post("/api/v1/auth/logout/", {"refresh": refresh_token})
    assert logout_response.status_code == 200

    refresh_after_logout = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
    assert refresh_after_logout.status_code == 401
