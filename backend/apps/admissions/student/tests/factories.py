import factory
from factory.django import DjangoModelFactory

from apps.admissions.admission.tests.factories import AdmissionFactory
from apps.admissions.student.models import Student, StudentStatusHistory
from apps.core.tests.factories import ProgrammeFactory
from apps.people.tests.factories import PersonFactory


class StudentFactory(DjangoModelFactory):
    class Meta:
        model = Student

    student_code = factory.Sequence(lambda n: f"ACA/2627/{n:04d}")
    person = factory.SubFactory(PersonFactory)
    admission = factory.SubFactory(AdmissionFactory)
    admission_date = factory.Faker("date_this_year")
    programme = factory.SubFactory(ProgrammeFactory)


class StudentStatusHistoryFactory(DjangoModelFactory):
    class Meta:
        model = StudentStatusHistory

    student = factory.SubFactory(StudentFactory)
    to_status = "active"
    reason = factory.Faker("sentence")
    changed_by = factory.SubFactory("apps.iam.tests.factories.UserFactory")
