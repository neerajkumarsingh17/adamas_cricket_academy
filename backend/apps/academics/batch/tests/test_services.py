import datetime

import pytest
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.admissions.student.tests.factories import StudentFactory

from .. import services
from .factories import BatchEnrollmentFactory, BatchFactory, TrainingSessionFactory


@pytest.mark.django_db
def test_enrol_creates_an_active_enrollment():
    batch = BatchFactory(capacity=20)
    student = StudentFactory()

    enrollment = services.enrol(student, batch, from_date=datetime.date(2026, 4, 1))

    assert enrollment.student == student
    assert enrollment.batch == batch
    assert enrollment.is_active is True


@pytest.mark.django_db
def test_enrolling_into_a_full_batch_is_refused():
    batch = BatchFactory(capacity=1)
    BatchEnrollmentFactory(batch=batch, is_active=True)
    student = StudentFactory()

    with pytest.raises(services.BatchFull) as exc_info:
        services.enrol(student, batch, from_date=datetime.date(2026, 4, 1))
    assert exc_info.value.status_code == 409
    assert isinstance(exc_info.value, APIException)


@pytest.mark.django_db
def test_a_student_with_an_active_enrollment_cannot_enrol_again():
    student = StudentFactory()
    BatchEnrollmentFactory(student=student, is_active=True, batch=BatchFactory(capacity=20))
    other_batch = BatchFactory(capacity=20)

    with pytest.raises(services.StudentAlreadyEnrolled):
        services.enrol(student, other_batch, from_date=datetime.date(2026, 4, 1))


@pytest.mark.django_db
def test_an_inactive_enrollment_does_not_count_towards_capacity():
    batch = BatchFactory(capacity=1)
    BatchEnrollmentFactory(batch=batch, is_active=False)
    student = StudentFactory()

    # Must not raise.
    services.enrol(student, batch, from_date=datetime.date(2026, 4, 1))


@pytest.mark.django_db
def test_transfer_closes_the_old_row_and_opens_a_new_one():
    old_batch = BatchFactory(capacity=20)
    new_batch = BatchFactory(capacity=20)
    enrollment = BatchEnrollmentFactory(batch=old_batch, is_active=True)
    effective_date = datetime.date(2026, 5, 1)

    new_enrollment = services.transfer(enrollment, new_batch, effective_date)

    enrollment.refresh_from_db()
    assert enrollment.is_active is False
    assert enrollment.to_date == effective_date
    assert new_enrollment.batch == new_batch
    assert new_enrollment.student == enrollment.student
    assert new_enrollment.from_date == effective_date
    assert new_enrollment.is_active is True


@pytest.mark.django_db
def test_transfer_into_a_full_batch_is_refused():
    old_batch = BatchFactory(capacity=20)
    new_batch = BatchFactory(capacity=1)
    BatchEnrollmentFactory(batch=new_batch, is_active=True)
    enrollment = BatchEnrollmentFactory(batch=old_batch, is_active=True)

    with pytest.raises(services.BatchFull):
        services.transfer(enrollment, new_batch, datetime.date(2026, 5, 1))

    # The old row must not have been closed by a transfer that ultimately
    # failed — the whole thing is one transaction.
    enrollment.refresh_from_db()
    assert enrollment.is_active is True


@pytest.mark.django_db
def test_assert_batch_editable_allows_a_batch_with_only_future_sessions():
    batch = BatchFactory()
    TrainingSessionFactory(batch=batch, date=timezone.localdate() + datetime.timedelta(days=7))

    services.assert_batch_editable(batch)  # must not raise


@pytest.mark.django_db
def test_assert_batch_editable_refuses_a_batch_with_a_past_session():
    batch = BatchFactory()
    TrainingSessionFactory(batch=batch, date=timezone.localdate() - datetime.timedelta(days=1))

    with pytest.raises(services.BatchAlreadyStarted):
        services.assert_batch_editable(batch)


@pytest.mark.django_db
def test_assert_batch_editable_refuses_a_batch_starting_today():
    batch = BatchFactory()
    TrainingSessionFactory(batch=batch, date=timezone.localdate())

    with pytest.raises(services.BatchAlreadyStarted):
        services.assert_batch_editable(batch)


@pytest.mark.django_db
def test_delete_batch_refuses_a_started_batch():
    batch = BatchFactory()
    TrainingSessionFactory(batch=batch, date=timezone.localdate() - datetime.timedelta(days=1))

    with pytest.raises(services.BatchAlreadyStarted):
        services.delete_batch(batch)


@pytest.mark.django_db
def test_delete_batch_refuses_a_batch_with_any_enrollment():
    batch = BatchFactory()
    BatchEnrollmentFactory(batch=batch, is_active=False)  # even a past, inactive one

    with pytest.raises(services.BatchHasEnrollments):
        services.delete_batch(batch)


@pytest.mark.django_db
def test_delete_batch_clears_future_sessions_and_deletes_the_batch():
    batch = BatchFactory()
    TrainingSessionFactory(batch=batch, date=timezone.localdate() + datetime.timedelta(days=7))
    batch_id = batch.id

    services.delete_batch(batch)

    from ..models import Batch, TrainingSession

    assert not Batch.objects.filter(id=batch_id).exists()
    assert not TrainingSession.objects.filter(batch_id=batch_id).exists()


@pytest.mark.django_db
def test_generate_sessions_creates_rows_on_matching_weekdays_only():
    batch = BatchFactory(weekdays="1,3,5")  # Mon/Wed/Fri

    result = services.generate_sessions(days=14)

    assert result["created"] > 0
    for session in batch.sessions.all():
        assert session.date.isoweekday() in {1, 3, 5}
        assert session.training_type is None


@pytest.mark.django_db
def test_generate_sessions_is_idempotent_on_replay():
    batch = BatchFactory(weekdays="1,3,5")

    first = services.generate_sessions(days=14)
    second = services.generate_sessions(days=14)

    assert first["created"] > 0
    assert second["created"] == 0
    assert second["skipped"] == first["created"]
    assert batch.sessions.count() == first["created"]
