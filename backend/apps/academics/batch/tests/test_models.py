import pytest
from django.db import IntegrityError

from apps.admissions.student.tests.factories import StudentFactory

from .factories import BatchEnrollmentFactory, BatchFactory


@pytest.mark.django_db
def test_a_student_cannot_have_two_active_enrollments():
    """The partial unique index on BatchEnrollment — a database
    constraint, not an if-check: two active enrolments for one student
    would mean two monthly fees.
    """
    student = StudentFactory()
    BatchEnrollmentFactory(student=student, is_active=True)

    with pytest.raises(IntegrityError):
        BatchEnrollmentFactory(student=student, batch=BatchFactory(), is_active=True)


@pytest.mark.django_db
def test_a_student_can_have_a_second_enrollment_once_the_first_is_inactive():
    """The constraint is partial (WHERE is_active=True) — an inactive
    (ended) enrolment doesn't block a new active one for the same student.
    """
    student = StudentFactory()
    BatchEnrollmentFactory(student=student, is_active=False)

    # Must not raise.
    BatchEnrollmentFactory(student=student, batch=BatchFactory(), is_active=True)
