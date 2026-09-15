import datetime

import pytest
from rest_framework.test import APIClient

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
def test_a_freshly_created_student_opens_with_an_empty_profile():
    student = StudentFactory(
        residential=False, person=PersonFactory(email="", blood_group="")
    )

    result = services.profile_completeness(student)

    assert result["percent"] == 0
    assert result["next_field"] is not None


@pytest.mark.django_db
def test_completeness_moves_as_fields_fill_in():
    student = StudentFactory(residential=False)
    before = services.profile_completeness(student)["percent"]

    services.update_profile(
        student,
        profile_fields={"nationality": "Indian", "school_name": "DPS Kolkata"},
        person_fields={"blood_group": "O+"},
    )

    after = services.profile_completeness(student)["percent"]
    assert after > before


@pytest.mark.django_db
def test_next_field_reports_the_first_pending_field_in_order():
    student = StudentFactory(
        residential=False, person=PersonFactory(email="", blood_group="")
    )
    # blood_group is first in the ordering — fill it, expect the next one.
    services.update_profile(
        student, profile_fields={}, person_fields={"blood_group": "O+"}
    )

    result = services.profile_completeness(student)

    assert result["next_field"] == "student email"


@pytest.mark.django_db
def test_aadhaar_number_is_never_the_reported_next_field():
    """Optional and stays optional — never chased (Prompt G)."""
    student = StudentFactory(residential=False)
    services.get_or_create_profile(student)

    fields = services._profile_field_status(student)  # noqa: SLF001 — testing the ordering itself
    names = [name for name, _, _ in fields]

    assert "aadhaar_number" not in names


@pytest.mark.django_db
def test_residential_student_has_local_guardian_fields_counted():
    student = StudentFactory(residential=True)
    names_residential = [name for name, _, _ in services._profile_field_status(student)]  # noqa: SLF001

    other = StudentFactory(residential=False)
    names_non_residential = [name for name, _, _ in services._profile_field_status(other)]  # noqa: SLF001

    assert "food_preference" in names_residential
    assert "food_preference" not in names_non_residential


@pytest.mark.django_db
def test_update_profile_writes_to_person_for_blood_group_and_email():
    student = StudentFactory()

    services.update_profile(
        student,
        profile_fields={},
        person_fields={"blood_group": "AB+", "email": "student@example.com"},
    )

    student.person.refresh_from_db()
    assert student.person.blood_group == "AB+"
    assert student.person.email == "student@example.com"


@pytest.mark.django_db
def test_student_can_view_and_update_their_own_profile(api_client, seeded_roles):
    student = StudentFactory()
    student_user = UserFactory(person=student.person)
    UserRole.objects.create(
        user=student_user,
        role=Role.objects.get(code="student"),
        valid_from=datetime.date(2020, 1, 1),
    )
    api_client.force_authenticate(student_user)

    get_response = api_client.get(f"/api/v1/students/{student.id}/profile/")
    assert get_response.status_code == 200, get_response.data

    patch_response = api_client.patch(
        f"/api/v1/students/{student.id}/profile/", {"nationality": "Indian"}
    )
    assert patch_response.status_code == 200, patch_response.data
    assert patch_response.data["nationality"] == "Indian"


@pytest.mark.django_db
def test_parent_can_update_their_childs_profile(api_client, seeded_roles):
    student = StudentFactory()
    guardian_person = PersonFactory()
    guardian = GuardianFactory(person=guardian_person)
    StudentGuardianFactory(student=student, guardian=guardian, is_primary=True)
    parent_user = UserFactory(person=guardian_person)
    UserRole.objects.create(
        user=parent_user, role=Role.objects.get(code="parent"), valid_from=datetime.date(2020, 1, 1)
    )
    api_client.force_authenticate(parent_user)

    response = api_client.patch(
        f"/api/v1/students/{student.id}/profile/", {"school_name": "DPS Kolkata"}
    )

    assert response.status_code == 200, response.data
    assert response.data["school_name"] == "DPS Kolkata"


@pytest.mark.django_db
def test_a_student_cannot_update_someone_elses_profile(api_client, seeded_roles):
    student = StudentFactory()
    other_student = StudentFactory()
    other_user = UserFactory(person=other_student.person)
    UserRole.objects.create(
        user=other_user, role=Role.objects.get(code="student"), valid_from=datetime.date(2020, 1, 1)
    )
    api_client.force_authenticate(other_user)

    response = api_client.patch(
        f"/api/v1/students/{student.id}/profile/", {"nationality": "Indian"}
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_staff_with_view_only_cannot_patch_a_profile(api_client, seeded_roles):
    """docs/03-rbac.md: Accounts holds only `V` on student_profile."""
    student = StudentFactory()
    accounts_user = _user_with_role("accounts")
    api_client.force_authenticate(accounts_user)

    get_response = api_client.get(f"/api/v1/students/{student.id}/profile/")
    assert get_response.status_code == 200

    patch_response = api_client.patch(
        f"/api/v1/students/{student.id}/profile/", {"nationality": "Indian"}
    )
    assert patch_response.status_code == 403


@pytest.mark.django_db
def test_coach_and_office_fields_are_not_reachable_from_this_endpoint(api_client, seeded_roles):
    """highest_level_played/batting_style/bowling_style and
    batch_allotted/coach_assigned aren't modelled at all yet (see
    StudentProfile's docstring) — a PATCH naming them is silently ignored,
    not honoured, same as age_category on the direct-admission intake.
    """
    student = StudentFactory()
    student_user = UserFactory(person=student.person)
    UserRole.objects.create(
        user=student_user,
        role=Role.objects.get(code="student"),
        valid_from=datetime.date(2020, 1, 1),
    )
    api_client.force_authenticate(student_user)

    response = api_client.patch(
        f"/api/v1/students/{student.id}/profile/",
        {"highest_level_played": "State", "batch_allotted": "Morning A"},
    )

    assert response.status_code == 200, response.data
    assert "highest_level_played" not in response.data
    assert "batch_allotted" not in response.data
