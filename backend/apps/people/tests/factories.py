import factory
from factory.django import DjangoModelFactory

from apps.people.models import (
    Gender,
    Guardian,
    Person,
    Relationship,
    Staff,
    StaffType,
    StudentGuardian,
)


class PersonFactory(DjangoModelFactory):
    class Meta:
        model = Person

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    date_of_birth = factory.Faker("date_of_birth", minimum_age=5, maximum_age=18)
    gender = Gender.OTHER
    mobile = factory.Sequence(lambda n: f"90000{n:05d}")
    email = factory.Faker("email")
    address_line1 = factory.Faker("street_address")
    city = factory.Faker("city")
    state = factory.Faker("state")
    pincode = factory.Sequence(lambda n: f"{100000 + n:06d}")


class GuardianFactory(DjangoModelFactory):
    class Meta:
        model = Guardian

    person = factory.SubFactory(PersonFactory)
    occupation = factory.Faker("job")
    portal_access = False


class StudentGuardianFactory(DjangoModelFactory):
    class Meta:
        model = StudentGuardian

    # Lazy string reference, not a top-level import: student's own factory
    # chain (student -> admission -> people) would otherwise create a
    # circular import with this module.
    student = factory.SubFactory("apps.admissions.student.tests.factories.StudentFactory")
    guardian = factory.SubFactory(GuardianFactory)
    relationship = Relationship.GUARDIAN
    is_primary = False
    is_emergency_contact = False


class StaffFactory(DjangoModelFactory):
    class Meta:
        model = Staff

    person = factory.SubFactory(PersonFactory)
    employee_code = factory.Sequence(lambda n: f"EMP{n:05d}")
    staff_type = StaffType.COACH
    joining_date = factory.Faker("date_this_decade")
