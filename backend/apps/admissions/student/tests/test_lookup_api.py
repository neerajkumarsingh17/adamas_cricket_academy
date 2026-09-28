import datetime

import pytest
from rest_framework.test import APIClient

from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory

from .factories import StudentFactory


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
def test_lookup_matches_by_student_code(api_client, seeded_roles):
    user = _user_with_role("head_coach")
    target = StudentFactory(student_code="ACA/2627/0042")
    StudentFactory(student_code="ACA/2627/0099")
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/students/lookup/?q=0042")

    assert response.status_code == 200
    assert [row["id"] for row in response.data] == [str(target.id)]


@pytest.mark.django_db
def test_lookup_matches_by_name(api_client, seeded_roles):
    user = _user_with_role("administration")
    target = StudentFactory(person=PersonFactory(first_name="Rohan", last_name="Das"))
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/students/lookup/?q=Rohan")

    assert response.status_code == 200
    assert [row["id"] for row in response.data] == [str(target.id)]


@pytest.mark.django_db
def test_lookup_requires_at_least_three_characters(api_client, seeded_roles):
    user = _user_with_role("head_coach")
    StudentFactory(person=PersonFactory(first_name="Ro"))
    api_client.force_authenticate(user)

    assert api_client.get("/api/v1/students/lookup/?q=Ro").data == []


@pytest.mark.django_db
def test_lookup_is_gated_on_batch_add(api_client, seeded_roles):
    """Gated on batch:add (the enrol form's own permission), not a general
    student directory — accounts holds no batch grant at all."""
    user = _user_with_role("accounts")
    api_client.force_authenticate(user)

    assert api_client.get("/api/v1/students/lookup/?q=anything").status_code == 403
