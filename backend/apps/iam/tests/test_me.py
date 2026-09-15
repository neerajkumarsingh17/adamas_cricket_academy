import pytest
from rest_framework.test import APIClient

from apps.people.tests.factories import PersonFactory

from .factories import PermissionFactory, RolePermissionFactory, UserFactory, UserRoleFactory


@pytest.mark.django_db
def test_me_requires_authentication():
    response = APIClient().get("/api/v1/auth/me/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_user_person_roles_and_flattened_permissions():
    person = PersonFactory()
    user = UserFactory(person=person)
    permission = PermissionFactory(module="admission", verb="approve")
    role_permission = RolePermissionFactory(permission=permission, scope="all")
    UserRoleFactory(user=user, role=role_permission.role)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    data = response.data
    assert data["id"] == str(user.id)
    assert data["login_id"] == user.login_id
    assert data["person"]["id"] == str(person.id)
    assert {"code": role_permission.role.code, "name": role_permission.role.name} in data["roles"]
    assert {"module": "admission", "verb": "approve", "scope": "all"} in data["permissions"]


@pytest.mark.django_db
def test_me_person_is_null_for_system_account():
    user = UserFactory(person=None)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    assert response.data["person"] is None
