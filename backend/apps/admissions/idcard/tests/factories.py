import factory
from factory.django import DjangoModelFactory

from apps.admissions.idcard.models import IDCard
from apps.admissions.student.tests.factories import StudentFactory


class IDCardFactory(DjangoModelFactory):
    class Meta:
        model = IDCard

    student = factory.SubFactory(StudentFactory)
    card_no = factory.Sequence(lambda n: f"ACA/2627/{n:04d}-1")
    issued_on = factory.Faker("date_this_year")
    valid_until = factory.Faker("future_date")
    qr_payload = factory.Sequence(lambda n: f"opaque-signed-token-{n}")
