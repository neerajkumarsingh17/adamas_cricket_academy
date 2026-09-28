import factory
from factory.django import DjangoModelFactory

from apps.academics.batch.tests.factories import TrainingSessionFactory
from apps.admissions.student.tests.factories import StudentFactory
from apps.iam.tests.factories import UserFactory

from ..models import Attendance, AttendanceCorrection, Status


class AttendanceFactory(DjangoModelFactory):
    class Meta:
        model = Attendance

    session = factory.SubFactory(TrainingSessionFactory)
    student = factory.SubFactory(StudentFactory)
    status = Status.PRESENT
    marked_by = factory.SubFactory(UserFactory)


class AttendanceCorrectionFactory(DjangoModelFactory):
    class Meta:
        model = AttendanceCorrection

    attendance = factory.SubFactory(AttendanceFactory)
    from_status = Status.PRESENT
    to_status = Status.ABSENT
    reason = "Marked in error."
    requested_by = factory.SubFactory(UserFactory)
