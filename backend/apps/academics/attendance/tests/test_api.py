import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academics.batch.tests.factories import CoachFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory, StaffFactory

from ..models import Status
from .factories import AttendanceCorrectionFactory


def _user_with_role(role_code: str, **user_kwargs):
    user = UserFactory(**user_kwargs)
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=role_code), valid_from=datetime.date(2020, 1, 1)
    )
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_head_coach_can_approve_a_correction(api_client, seeded_roles):
    user = _user_with_role("head_coach")
    correction = AttendanceCorrectionFactory(from_status=Status.ABSENT, to_status=Status.PRESENT)
    api_client.force_authenticate(user)

    response = api_client.post(f"/api/v1/corrections/{correction.id}/approve/")

    assert response.status_code == 200
    correction.attendance.refresh_from_db()
    assert correction.attendance.status == Status.PRESENT


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", ["academy_head", "administration"])
def test_academy_head_and_administration_can_approve_a_correction(
    api_client, seeded_roles, role_code
):
    """Extended from Head-Coach-only (SOP §70) — both roles now get
    `approve` on `attendance` (seed_roles.py's MATRIX row)."""
    user = _user_with_role(role_code)
    correction = AttendanceCorrectionFactory(from_status=Status.ABSENT, to_status=Status.PRESENT)
    api_client.force_authenticate(user)

    response = api_client.post(f"/api/v1/corrections/{correction.id}/approve/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_sports_ops_cannot_approve_a_correction(api_client, seeded_roles):
    user = _user_with_role("sports_ops")
    correction = AttendanceCorrectionFactory()
    api_client.force_authenticate(user)

    response = api_client.post(f"/api/v1/corrections/{correction.id}/approve/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_requesting_a_correction_does_not_change_attendance(api_client, seeded_roles):
    from .factories import AttendanceFactory

    # "all"-scope role, deliberately not "coach" — this test is about
    # request_correction() not mutating Attendance.status, not about
    # coach-scoping (covered separately below).
    user = _user_with_role("administration")
    attendance = AttendanceFactory(status=Status.ABSENT)
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/v1/attendance/{attendance.id}/corrections/",
        {"to_status": Status.PRESENT, "reason": "Marked in error."},
    )

    assert response.status_code == 201
    attendance.refresh_from_db()
    assert attendance.status == Status.ABSENT


@pytest.mark.django_db
def test_coach_can_mark_their_own_session(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory
    from apps.admissions.student.tests.factories import StudentFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    coach = CoachFactory(staff=StaffFactory(person=coach_user.person))
    session = TrainingSessionFactory(coach=coach)
    student = StudentFactory()
    api_client.force_authenticate(coach_user)

    response = api_client.post(
        f"/api/v1/sessions/{session.id}/attendance/",
        [{"student": str(student.id), "status": Status.PRESENT}],
        format="json",
    )

    assert response.status_code == 200
    assert response.data[0]["ok"] is True


@pytest.mark.django_db
def test_coach_cannot_mark_another_coachs_session(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory
    from apps.admissions.student.tests.factories import StudentFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    CoachFactory(staff=StaffFactory(person=coach_user.person))
    other_session = TrainingSessionFactory()  # a different, unrelated coach
    student = StudentFactory()
    api_client.force_authenticate(coach_user)

    roster_response = api_client.get(f"/api/v1/sessions/{other_session.id}/roster/")
    mark_response = api_client.post(
        f"/api/v1/sessions/{other_session.id}/attendance/",
        [{"student": str(student.id), "status": Status.PRESENT}],
        format="json",
    )
    cancel_response = api_client.post(
        f"/api/v1/sessions/{other_session.id}/cancel/", {"reason": "n/a"}
    )

    assert roster_response.status_code == 404
    assert mark_response.status_code == 404
    assert cancel_response.status_code == 404


@pytest.mark.django_db
def test_coach_can_reschedule_and_edit_their_own_future_session(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    coach = CoachFactory(staff=StaffFactory(person=coach_user.person))
    session = TrainingSessionFactory(
        coach=coach, date=timezone.localdate() + datetime.timedelta(days=7)
    )
    api_client.force_authenticate(coach_user)

    response = api_client.post(
        f"/api/v1/sessions/{session.id}/update-details/", {"objective": "Death bowling"}
    )

    assert response.status_code == 200
    assert response.data["objective"] == "Death bowling"


@pytest.mark.django_db
def test_coach_can_mark_their_own_session_conducted(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    coach = CoachFactory(staff=StaffFactory(person=coach_user.person))
    session = TrainingSessionFactory(coach=coach, is_conducted=False)
    api_client.force_authenticate(coach_user)

    response = api_client.post(f"/api/v1/sessions/{session.id}/mark-conducted/")

    assert response.status_code == 200
    assert response.data["is_conducted"] is True


@pytest.mark.django_db
def test_coach_cannot_mark_another_coachs_session_conducted(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    CoachFactory(staff=StaffFactory(person=coach_user.person))
    other_session = TrainingSessionFactory(is_conducted=False)
    api_client.force_authenticate(coach_user)

    response = api_client.post(f"/api/v1/sessions/{other_session.id}/mark-conducted/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_marking_conducted_is_refused_once_the_24_hour_window_has_closed(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    coach = CoachFactory(staff=StaffFactory(person=coach_user.person))
    session = TrainingSessionFactory(
        coach=coach, date=timezone.localdate() - datetime.timedelta(days=2), is_conducted=False
    )
    api_client.force_authenticate(coach_user)

    response = api_client.post(f"/api/v1/sessions/{session.id}/mark-conducted/")

    assert response.status_code == 409


@pytest.mark.django_db
def test_marking_conducted_is_refused_before_the_session_has_started(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    coach = CoachFactory(staff=StaffFactory(person=coach_user.person))
    session = TrainingSessionFactory(
        coach=coach, date=timezone.localdate() + datetime.timedelta(days=7), is_conducted=False
    )
    api_client.force_authenticate(coach_user)

    response = api_client.post(f"/api/v1/sessions/{session.id}/mark-conducted/")

    assert response.status_code == 409


@pytest.mark.django_db
def test_marking_attendance_is_refused_before_the_session_has_started(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory
    from apps.admissions.student.tests.factories import StudentFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    coach = CoachFactory(staff=StaffFactory(person=coach_user.person))
    session = TrainingSessionFactory(
        coach=coach, date=timezone.localdate() + datetime.timedelta(days=7)
    )
    student = StudentFactory()
    api_client.force_authenticate(coach_user)

    response = api_client.post(
        f"/api/v1/sessions/{session.id}/attendance/",
        [{"student": str(student.id), "status": Status.PRESENT}],
        format="json",
    )

    assert response.status_code == 409


@pytest.mark.django_db
def test_marking_attendance_is_refused_once_the_24_hour_window_has_closed(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory
    from apps.admissions.student.tests.factories import StudentFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    coach = CoachFactory(staff=StaffFactory(person=coach_user.person))
    session = TrainingSessionFactory(
        coach=coach, date=timezone.localdate() - datetime.timedelta(days=2)
    )
    student = StudentFactory()
    api_client.force_authenticate(coach_user)

    response = api_client.post(
        f"/api/v1/sessions/{session.id}/attendance/",
        [{"student": str(student.id), "status": Status.PRESENT}],
        format="json",
    )

    assert response.status_code == 409


@pytest.mark.django_db
def test_coach_cannot_edit_another_coachs_session(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    CoachFactory(staff=StaffFactory(person=coach_user.person))
    other_session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))
    api_client.force_authenticate(coach_user)

    response = api_client.post(
        f"/api/v1/sessions/{other_session.id}/update-details/", {"objective": "n/a"}
    )

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", ["administration", "academy_head", "head_coach"])
def test_batch_admin_roles_can_delete_a_future_unmarked_session(
    api_client, seeded_roles, role_code
):
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    user = _user_with_role(role_code)
    session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))
    session_id = session.id
    api_client.force_authenticate(user)

    response = api_client.post(f"/api/v1/sessions/{session_id}/delete/")

    assert response.status_code == 204
    from apps.academics.batch.models import TrainingSession

    assert not TrainingSession.objects.filter(id=session_id).exists()


@pytest.mark.django_db
def test_coach_cannot_delete_even_their_own_session(api_client, seeded_roles):
    """Delete is narrowed to batch_admin (Administration/Academy Head/
    Head Coach) — a bigger authority than the own-scope attendance grant
    a Coach otherwise has on their own sessions."""
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    coach_user = _user_with_role("coach", person=PersonFactory())
    coach = CoachFactory(staff=StaffFactory(person=coach_user.person))
    session = TrainingSessionFactory(
        coach=coach, date=timezone.localdate() + datetime.timedelta(days=7)
    )
    api_client.force_authenticate(coach_user)

    response = api_client.post(f"/api/v1/sessions/{session.id}/delete/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_deleting_a_session_with_attendance_is_refused(api_client, seeded_roles):
    from apps.academics.batch.tests.factories import TrainingSessionFactory

    from .factories import AttendanceFactory

    user = _user_with_role("administration")
    session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))
    AttendanceFactory(session=session, status=Status.PRESENT)
    api_client.force_authenticate(user)

    response = api_client.post(f"/api/v1/sessions/{session.id}/delete/")

    assert response.status_code == 409
