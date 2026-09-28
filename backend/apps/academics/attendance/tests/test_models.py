import pytest
from django.db import IntegrityError

from apps.academics.batch.tests.factories import TrainingSessionFactory
from apps.admissions.student.tests.factories import StudentFactory

from ..models import COUNTS_AS_PRESENT, NOT_COUNTED, Status
from .factories import AttendanceFactory


@pytest.mark.django_db
def test_a_student_cannot_be_marked_twice_for_one_session():
    session = TrainingSessionFactory()
    student = StudentFactory()
    AttendanceFactory(session=session, student=student)

    with pytest.raises(IntegrityError):
        AttendanceFactory(session=session, student=student)


@pytest.mark.django_db
def test_the_same_student_can_be_marked_for_a_different_session():
    student = StudentFactory()
    AttendanceFactory(session=TrainingSessionFactory(), student=student)

    # Must not raise — the unique constraint is (session, student), not
    # student alone.
    AttendanceFactory(session=TrainingSessionFactory(), student=student)


def test_counts_as_present_and_not_counted_partition_the_policy():
    """The two module-level sets are the entire attendance policy — every
    status appears in exactly one of them, or in neither (a genuine
    absence)."""
    assert COUNTS_AS_PRESENT & NOT_COUNTED == set()
    assert Status.ABSENT not in COUNTS_AS_PRESENT
    assert Status.ABSENT not in NOT_COUNTED
    assert Status.LEAVE not in COUNTS_AS_PRESENT
    assert Status.LEAVE not in NOT_COUNTED
