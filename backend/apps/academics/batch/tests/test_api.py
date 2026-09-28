import datetime
import threading

import pytest
from django.db import connections
from django.utils import timezone
from rest_framework.test import APIClient

from apps.admissions.student.tests.factories import StudentFactory
from apps.core.tests.factories import AgeCategoryFactory, VenueFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory

from .factories import BatchEnrollmentFactory, BatchFactory, CoachFactory, TrainingSessionFactory


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
def test_enrolling_into_a_full_batch_returns_batch_full(api_client, seeded_roles):
    user = _user_with_role("administration")
    batch = BatchFactory(capacity=1)
    BatchEnrollmentFactory(batch=batch, is_active=True)
    student = StudentFactory()
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/v1/batches/{batch.id}/enrol/",
        {"student": str(student.id), "from_date": "2026-04-01"},
    )

    assert response.status_code == 409
    assert response.data["code"] == "batch_full"


@pytest.mark.django_db
def test_batch_list_reports_seats_used_vs_capacity(api_client, seeded_roles):
    user = _user_with_role("administration")
    batch = BatchFactory(capacity=25)
    BatchEnrollmentFactory(batch=batch, is_active=True)
    BatchEnrollmentFactory(batch=batch, is_active=False)  # must not count
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/batches/")

    row = next(r for r in response.data["results"] if r["id"] == str(batch.id))
    assert row["enrolled_count"] == 1
    assert row["seats_available"] == 24


@pytest.mark.django_db
def test_enrollments_filter_by_batch_and_active(api_client, seeded_roles):
    user = _user_with_role("administration")
    batch = BatchFactory()
    active = BatchEnrollmentFactory(batch=batch, is_active=True)
    BatchEnrollmentFactory(batch=batch, is_active=False)
    BatchEnrollmentFactory(is_active=True)  # another batch
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/enrollments/?batch={batch.id}&is_active=true")

    assert response.status_code == 200
    assert [r["id"] for r in response.data["results"]] == [str(active.id)]


def _create_payload(**overrides):
    payload = {
        "name": "U-14 Evening",
        "age_category": str(AgeCategoryFactory().id),
        "coach": str(CoachFactory().id),
        "venue": str(VenueFactory().id),
        "capacity": 20,
        "weekdays": "1,3,5",
        "start_time": "16:00:00",
        "end_time": "18:00:00",
        "monthly_fee": "3500.00",
        "residential_monthly_fee": "12000.00",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_administration_can_create_a_batch(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)

    response = api_client.post("/api/v1/batches/", _create_payload(), format="json")

    assert response.status_code == 201
    assert response.data["name"] == "U-14 Evening"
    assert response.data["seats_available"] == 20
    assert response.data["monthly_fee"] == "3500.00"
    assert response.data["residential_monthly_fee"] == "12000.00"


@pytest.mark.django_db
def test_creating_a_batch_without_a_residential_fee_is_refused(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    payload = _create_payload()
    del payload["residential_monthly_fee"]

    response = api_client.post("/api/v1/batches/", payload, format="json")

    assert response.status_code == 400
    assert "residential_monthly_fee" in response.data["field_errors"]


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", ["sports_ops", "coach"])
def test_other_roles_cannot_create_a_batch(api_client, seeded_roles, role_code):
    user = _user_with_role(role_code)
    api_client.force_authenticate(user)

    response = api_client.post("/api/v1/batches/", _create_payload(), format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_administration_can_edit_a_batch_with_no_sessions_yet(api_client, seeded_roles):
    user = _user_with_role("administration")
    batch = BatchFactory(name="Old name")
    api_client.force_authenticate(user)

    response = api_client.patch(f"/api/v1/batches/{batch.id}/", {"name": "New name"}, format="json")

    assert response.status_code == 200
    assert response.data["name"] == "New name"


@pytest.mark.django_db
def test_editing_a_started_batch_is_refused(api_client, seeded_roles):
    user = _user_with_role("administration")
    batch = BatchFactory()
    TrainingSessionFactory(batch=batch, date=timezone.localdate() - datetime.timedelta(days=1))
    api_client.force_authenticate(user)

    response = api_client.patch(f"/api/v1/batches/{batch.id}/", {"name": "New name"}, format="json")

    assert response.status_code == 409
    assert response.data["code"] == "batch_already_started"


@pytest.mark.django_db
def test_administration_can_delete_an_empty_batch(api_client, seeded_roles):
    user = _user_with_role("administration")
    batch = BatchFactory()
    TrainingSessionFactory(batch=batch, date=timezone.localdate() + datetime.timedelta(days=7))
    api_client.force_authenticate(user)

    response = api_client.delete(f"/api/v1/batches/{batch.id}/")

    assert response.status_code == 204


@pytest.mark.django_db
def test_deleting_a_batch_with_enrollments_is_refused(api_client, seeded_roles):
    user = _user_with_role("administration")
    batch = BatchFactory()
    BatchEnrollmentFactory(batch=batch, is_active=True)
    api_client.force_authenticate(user)

    response = api_client.delete(f"/api/v1/batches/{batch.id}/")

    assert response.status_code == 409
    assert response.data["code"] == "batch_has_enrollments"


@pytest.mark.django_db
def test_coach_list_is_readable_by_any_authenticated_role(api_client, seeded_roles):
    user = _user_with_role("coach")
    coach = CoachFactory()
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/coaches/")

    assert response.status_code == 200
    assert str(coach.id) in [c["id"] for c in response.data["results"]]


@pytest.mark.django_db(transaction=True)
def test_concurrent_enrolments_at_capacity_only_one_succeeds(seeded_roles):
    """The whole reason enrol() takes select_for_update on the batch: two
    admins both reading "0 of 1 used" and both writing is exactly how a
    1-seat batch would end up with 2 active enrolments without the lock.
    """
    from apps.academics.batch import services

    batch = BatchFactory(capacity=1)
    students = [StudentFactory(), StudentFactory()]
    outcomes: list[str] = []

    def attempt(student):
        try:
            services.enrol(student, batch, from_date=datetime.date(2026, 4, 1))
            outcomes.append("ok")
        except services.BatchFull:
            outcomes.append("full")
        finally:
            connections.close_all()

    threads = [threading.Thread(target=attempt, args=(s,)) for s in students]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes.count("ok") == 1
    assert outcomes.count("full") == 1
    assert batch.enrollments.filter(is_active=True).count() == 1
