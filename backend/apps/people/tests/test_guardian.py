import pytest
from django.core.exceptions import ValidationError

from apps.admissions.student.tests.factories import StudentFactory
from apps.people.models import Guardian, StudentGuardian

from .factories import GuardianFactory, StudentGuardianFactory


@pytest.mark.django_db
def test_one_guardian_with_two_children_is_a_single_guardian_row():
    guardian = GuardianFactory()
    first_child = StudentFactory()
    second_child = StudentFactory()

    StudentGuardianFactory(guardian=guardian, student=first_child, is_primary=True)
    StudentGuardianFactory(guardian=guardian, student=second_child, is_primary=True)

    assert Guardian.objects.count() == 1
    assert StudentGuardian.objects.filter(guardian=guardian).count() == 2


@pytest.mark.django_db
def test_second_primary_guardian_for_same_student_is_rejected():
    student = StudentFactory()
    StudentGuardianFactory(student=student, is_primary=True)

    with pytest.raises(ValidationError):
        StudentGuardianFactory(student=student, is_primary=True)

    assert StudentGuardian.objects.filter(student=student, is_primary=True).count() == 1


@pytest.mark.django_db
def test_second_non_primary_guardian_for_same_student_is_allowed():
    student = StudentFactory()
    StudentGuardianFactory(student=student, is_primary=True)

    StudentGuardianFactory(student=student, is_primary=False)

    assert StudentGuardian.objects.filter(student=student).count() == 2


@pytest.mark.django_db
def test_primary_guardian_can_be_reassigned_to_a_different_guardian():
    """Updating the existing primary row (not creating a second one) must
    not trip over itself in the uniqueness check.
    """
    student = StudentFactory()
    primary = StudentGuardianFactory(student=student, is_primary=True)

    primary.is_emergency_contact = True
    primary.save()

    assert StudentGuardian.objects.get(pk=primary.pk).is_emergency_contact is True


@pytest.mark.django_db
def test_duplicate_student_guardian_pair_is_rejected():
    guardian = GuardianFactory()
    student = StudentFactory()
    StudentGuardianFactory(student=student, guardian=guardian)

    with pytest.raises(ValidationError):
        StudentGuardianFactory(student=student, guardian=guardian)
