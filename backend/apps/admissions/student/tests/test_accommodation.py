import datetime

import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.core.tests.factories import BuildingFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import GuardianFactory, PersonFactory, StudentGuardianFactory

from .. import services
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
def test_update_accommodation_sets_building_and_room_for_a_residential_student():
    student = StudentFactory(residential=True)
    building = BuildingFactory()

    updated = services.update_accommodation(student, building=building, room_number="204")

    assert updated.building_id == building.id
    assert updated.room_number == "204"
    student.refresh_from_db()
    assert student.building_id == building.id
    assert student.room_number == "204"


@pytest.mark.django_db
def test_update_accommodation_refuses_a_building_for_a_non_residential_student():
    student = StudentFactory(residential=False)
    building = BuildingFactory()

    with pytest.raises(ValidationError):
        services.update_accommodation(student, building=building)

    student.refresh_from_db()
    assert student.building_id is None


@pytest.mark.django_db
def test_update_accommodation_allows_clearing_a_building_regardless_of_residential():
    building = BuildingFactory()
    student = StudentFactory(residential=True, building=building, room_number="101")

    services.update_accommodation(student, building=None, room_number="")

    student.refresh_from_db()
    assert student.building_id is None
    assert student.room_number == ""


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", ["hostel", "administration"])
def test_hostel_and_admin_can_view_and_assign_accommodation(api_client, seeded_roles, role_code):
    student = StudentFactory(residential=True)
    building = BuildingFactory()
    user = _user_with_role(role_code)
    api_client.force_authenticate(user)

    get_response = api_client.get(f"/api/v1/students/{student.id}/accommodation/")
    assert get_response.status_code == 200, get_response.data
    assert get_response.data["building"] is None

    patch_response = api_client.patch(
        f"/api/v1/students/{student.id}/accommodation/",
        {"building": str(building.id), "room_number": "12B"},
    )
    assert patch_response.status_code == 200, patch_response.data
    assert patch_response.data["building"] == building.id
    assert patch_response.data["building_name"] == building.name
    assert patch_response.data["room_number"] == "12B"


@pytest.mark.django_db
def test_assigning_a_building_to_a_non_residential_student_is_refused(api_client, seeded_roles):
    student = StudentFactory(residential=False)
    building = BuildingFactory()
    user = _user_with_role("hostel")
    api_client.force_authenticate(user)

    response = api_client.patch(
        f"/api/v1/students/{student.id}/accommodation/", {"building": str(building.id)}
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_student_can_view_but_not_edit_their_own_accommodation(api_client, seeded_roles):
    student = StudentFactory(residential=True)
    student_user = UserFactory(person=student.person)
    UserRole.objects.create(
        user=student_user,
        role=Role.objects.get(code="student"),
        valid_from=datetime.date(2020, 1, 1),
    )
    api_client.force_authenticate(student_user)

    get_response = api_client.get(f"/api/v1/students/{student.id}/accommodation/")
    assert get_response.status_code == 200, get_response.data

    patch_response = api_client.patch(
        f"/api/v1/students/{student.id}/accommodation/", {"room_number": "999"}
    )
    assert patch_response.status_code == 403


@pytest.mark.django_db
def test_parent_can_view_but_not_edit_their_childs_accommodation(api_client, seeded_roles):
    student = StudentFactory(residential=True)
    guardian_person = PersonFactory()
    guardian = GuardianFactory(person=guardian_person)
    StudentGuardianFactory(student=student, guardian=guardian, is_primary=True)
    parent_user = UserFactory(person=guardian_person)
    UserRole.objects.create(
        user=parent_user, role=Role.objects.get(code="parent"), valid_from=datetime.date(2020, 1, 1)
    )
    api_client.force_authenticate(parent_user)

    get_response = api_client.get(f"/api/v1/students/{student.id}/accommodation/")
    assert get_response.status_code == 200

    patch_response = api_client.patch(
        f"/api/v1/students/{student.id}/accommodation/", {"room_number": "999"}
    )
    assert patch_response.status_code == 403


@pytest.mark.django_db
def test_a_student_cannot_view_someone_elses_accommodation(api_client, seeded_roles):
    student = StudentFactory(residential=True)
    other_student = StudentFactory(residential=True)
    other_user = UserFactory(person=other_student.person)
    UserRole.objects.create(
        user=other_user, role=Role.objects.get(code="student"), valid_from=datetime.date(2020, 1, 1)
    )
    api_client.force_authenticate(other_user)

    response = api_client.get(f"/api/v1/students/{student.id}/accommodation/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_coach_has_no_access_to_accommodation(api_client, seeded_roles):
    """docs/03-rbac.md's Residential / Transport row: Coach's cell is `-`."""
    student = StudentFactory(residential=True)
    coach_user = _user_with_role("coach")
    api_client.force_authenticate(coach_user)

    get_response = api_client.get(f"/api/v1/students/{student.id}/accommodation/")
    patch_response = api_client.patch(
        f"/api/v1/students/{student.id}/accommodation/", {"room_number": "999"}
    )

    assert get_response.status_code == 403
    assert patch_response.status_code == 403
