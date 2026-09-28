import datetime

import pytest
from rest_framework.test import APIClient

from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory

from .factories import PersonFactory


def _user_with_role(role_code: str):
    user = UserFactory()
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=role_code), valid_from=datetime.date(2020, 1, 1)
    )
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_lookup_matches_by_mobile(api_client, seeded_roles):
    user = _user_with_role("administration")
    PersonFactory(first_name="Rohan", last_name="Das", mobile="+919800001234")
    PersonFactory(first_name="Someone", last_name="Else", mobile="+919811119999")
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/persons/lookup/?q=9800001234")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["first_name"] == "Rohan"


@pytest.mark.django_db
def test_lookup_matches_by_name(api_client, seeded_roles):
    user = _user_with_role("accounts")
    PersonFactory(first_name="Rohan", last_name="Das")
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/persons/lookup/?q=Rohan")

    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_lookup_requires_at_least_three_characters(api_client, seeded_roles):
    user = _user_with_role("administration")
    PersonFactory(first_name="Ro")
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/persons/lookup/?q=Ro")

    assert response.status_code == 200
    assert response.data == []


@pytest.mark.django_db
def test_coach_cannot_use_the_payment_lookup(api_client, seeded_roles):
    """Gated on payment:add, not a general person directory."""
    user = _user_with_role("coach")
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/persons/lookup/?q=anything")

    assert response.status_code == 403
