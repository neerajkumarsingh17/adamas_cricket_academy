import datetime

import pytest
from rest_framework.test import APIClient

from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.models import Relationship
from apps.people.tests.factories import GuardianFactory, PersonFactory, StudentGuardianFactory

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
def test_administration_sees_the_composite_profile(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    student = StudentFactory()

    response = api_client.get(f"/api/v1/students/{student.id}/")

    assert response.status_code == 200
    assert set(response.data.keys()) == {"personal", "parent", "cricket", "academy"}
    assert response.data["academy"]["student_code"] == student.student_code


@pytest.mark.django_db
def test_a_parent_can_see_their_own_child_but_not_another_parents_child(api_client, seeded_roles):
    parent_user = _user_with_role("parent")
    parent_user.person = PersonFactory()
    parent_user.save()
    guardian = GuardianFactory(person=parent_user.person)
    own_child = StudentFactory()
    StudentGuardianFactory(student=own_child, guardian=guardian, relationship=Relationship.FATHER)
    someone_elses_child = StudentFactory()

    api_client.force_authenticate(parent_user)

    own_response = api_client.get(f"/api/v1/students/{own_child.id}/")
    assert own_response.status_code == 200

    other_response = api_client.get(f"/api/v1/students/{someone_elses_child.id}/")
    assert other_response.status_code == 404  # not 403 — docs/03-rbac.md rule 3


@pytest.mark.django_db
def test_a_student_role_with_no_person_sees_nothing(api_client, seeded_roles):
    student_user = _user_with_role("student")  # no .person set
    api_client.force_authenticate(student_user)
    someone = StudentFactory()

    response = api_client.get(f"/api/v1/students/{someone.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_status_change_endpoint_returns_202_when_approval_is_pending(api_client, seeded_roles):
    from apps.core.models import ApprovalRule

    ApprovalRule.objects.update_or_create(
        module="students",
        action="suspended",
        defaults={"required_role": Role.objects.get(code="academy_head")},
    )
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    student = StudentFactory(status="active")

    response = api_client.post(
        f"/api/v1/students/{student.id}/status/",
        {"to_status": "suspended", "reason": "Disciplinary incident under review."},
    )

    assert response.status_code == 202, response.data
    assert response.data["status"] == "approval_pending"


@pytest.mark.django_db
def test_administration_can_link_a_new_guardian(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    student = StudentFactory()

    response = api_client.post(
        f"/api/v1/students/{student.id}/guardians/",
        {
            "first_name": "Ritu",
            "last_name": "Banerjee",
            "date_of_birth": "1982-06-15",
            "gender": "F",
            "mobile": "+919811122233",
            "relationship": "mother",
            "is_primary": True,
            "grant_portal_access": True,
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["relationship"] == "mother"
    assert response.data["is_primary"] is True


@pytest.mark.django_db
def test_coach_cannot_link_a_guardian(api_client, seeded_roles):
    user = _user_with_role("coach")
    api_client.force_authenticate(user)
    student = StudentFactory()

    response = api_client.post(
        f"/api/v1/students/{student.id}/guardians/",
        {"person_id": str(PersonFactory().id), "relationship": "guardian"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_administration_can_unlink_a_guardian(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    student = StudentFactory()
    link = StudentGuardianFactory(student=student)

    response = api_client.delete(f"/api/v1/students/{student.id}/guardians/{link.id}/")

    assert response.status_code == 204


@pytest.mark.django_db
def test_administration_can_grant_a_student_login(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    student = StudentFactory()

    response = api_client.post(
        f"/api/v1/students/{student.id}/login-access/",
        {"mobile": "+919833344455"},
        format="json",
    )

    assert response.status_code == 200, response.data
    assert response.data["created"] is True


@pytest.mark.django_db
def test_coach_cannot_grant_a_student_login(api_client, seeded_roles):
    user = _user_with_role("coach")
    api_client.force_authenticate(user)
    student = StudentFactory()

    response = api_client.post(f"/api/v1/students/{student.id}/login-access/", {}, format="json")

    assert response.status_code == 403
