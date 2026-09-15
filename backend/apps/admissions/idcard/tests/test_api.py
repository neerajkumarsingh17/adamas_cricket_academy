import datetime

import pytest
from rest_framework.test import APIClient

from apps.admissions.student.tests.factories import StudentFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import GuardianFactory, PersonFactory, StudentGuardianFactory


def _user_with_role(role_code: str, **kwargs):
    user = UserFactory(**kwargs)
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=role_code), valid_from=datetime.date(2020, 1, 1)
    )
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_administration_can_issue_a_card(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    student = StudentFactory()

    response = api_client.post(f"/api/v1/students/{student.id}/id-card/")

    assert response.status_code == 201, response.data
    assert response.data["status"] == "active"


@pytest.mark.django_db
def test_a_coach_cannot_issue_a_card(api_client, seeded_roles):
    # docs/03-rbac.md's provisional idcard row: coach has no row entry ("-").
    user = _user_with_role("coach")
    api_client.force_authenticate(user)
    student = StudentFactory()

    response = api_client.post(f"/api/v1/students/{student.id}/id-card/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_qr_resolve_is_reachable_without_authentication(api_client, seeded_roles):
    from apps.admissions.idcard import services

    student = StudentFactory()
    card = services.issue_card(student, issued_by=UserFactory())

    response = api_client.get(f"/api/v1/id-cards/resolve/{card.qr_payload}/")

    assert response.status_code == 200
    assert response.data["valid"] is True
    assert "student_code" not in response.data


@pytest.mark.django_db
def test_a_student_can_render_their_own_card(api_client, seeded_roles):
    from apps.admissions.idcard import services

    student = StudentFactory()
    card = services.issue_card(student, issued_by=UserFactory())
    user = _user_with_role("student", person=student.person)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/id-cards/{card.id}/render.pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


@pytest.mark.django_db
def test_a_parent_can_render_their_childs_card(api_client, seeded_roles):
    from apps.admissions.idcard import services

    student = StudentFactory()
    card = services.issue_card(student, issued_by=UserFactory())
    guardian_person = PersonFactory()
    StudentGuardianFactory(student=student, guardian=GuardianFactory(person=guardian_person))
    user = _user_with_role("parent", person=guardian_person)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/id-cards/{card.id}/render.pdf/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_a_student_cannot_render_another_students_card(api_client, seeded_roles):
    # docs/03-rbac.md rule 3 / CLAUDE.md rule 6: object-level authorisation
    # — not in their own-scoped queryset, so 404, never 403.
    from apps.admissions.idcard import services

    someone_elses_card = services.issue_card(StudentFactory(), issued_by=UserFactory())
    user = _user_with_role("student", person=PersonFactory())
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/id-cards/{someone_elses_card.id}/render.pdf/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_a_role_with_no_idcard_access_cannot_render_any_card(api_client, seeded_roles):
    from apps.admissions.idcard import services

    card = services.issue_card(StudentFactory(), issued_by=UserFactory())
    user = _user_with_role("accounts")
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/id-cards/{card.id}/render.pdf/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_batch_print_still_requires_the_print_verb_not_just_view(api_client, seeded_roles):
    from apps.admissions.idcard import services

    student = StudentFactory()
    services.issue_card(student, issued_by=UserFactory())
    user = _user_with_role("student", person=student.person)
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/v1/id-cards/batch-print/", {"student_ids": [str(student.id)]}, format="json"
    )

    assert response.status_code == 403
