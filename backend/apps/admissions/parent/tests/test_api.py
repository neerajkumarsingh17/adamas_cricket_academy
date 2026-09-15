import datetime

import pytest
from rest_framework.test import APIClient

from apps.admissions.student.tests.factories import StudentFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.models import Relationship as PeopleRelationship
from apps.people.tests.factories import GuardianFactory, PersonFactory, StudentGuardianFactory


def _parent_user():
    user = UserFactory()
    UserRole.objects.create(
        user=user, role=Role.objects.get(code="parent"), valid_from=datetime.date(2020, 1, 1)
    )
    user.person = PersonFactory()
    user.save()
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_parent_sees_only_their_own_children(api_client, seeded_roles):
    parent = _parent_user()
    guardian = GuardianFactory(person=parent.person)
    own_child = StudentFactory()
    StudentGuardianFactory(
        student=own_child, guardian=guardian, relationship=PeopleRelationship.MOTHER
    )
    other_child = StudentFactory()

    api_client.force_authenticate(parent)

    list_response = api_client.get("/api/v1/parents/me/children/")
    assert list_response.status_code == 200
    ids = {row["id"] for row in list_response.data}
    assert str(own_child.id) in ids
    assert str(other_child.id) not in ids

    own_detail = api_client.get(f"/api/v1/parents/me/children/{own_child.id}/")
    assert own_detail.status_code == 200

    other_detail = api_client.get(f"/api/v1/parents/me/children/{other_child.id}/")
    assert other_detail.status_code == 404


@pytest.mark.django_db
def test_portal_settings_are_created_on_first_access(api_client, seeded_roles):
    parent = _parent_user()
    GuardianFactory(person=parent.person)
    api_client.force_authenticate(parent)

    response = api_client.get("/api/v1/parents/me/settings/")

    assert response.status_code == 200
    assert response.data["sms_opt_in"] is True


@pytest.mark.django_db
def test_patching_settings_persists(api_client, seeded_roles):
    parent = _parent_user()
    GuardianFactory(person=parent.person)
    api_client.force_authenticate(parent)

    response = api_client.patch("/api/v1/parents/me/settings/", {"sms_opt_in": False})

    assert response.status_code == 200
    assert response.data["sms_opt_in"] is False
