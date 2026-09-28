import datetime

import factory
from factory.django import DjangoModelFactory

from apps.admissions.admission.tests.factories import DirectAdmissionFactory
from apps.core.tests.factories import PaymentTypeFactory
from apps.finance.payment.models import AdmissionPayment, Payment, PaymentMode
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory


class AdmissionPaymentFactory(DjangoModelFactory):
    class Meta:
        model = AdmissionPayment

    admission = factory.SubFactory(DirectAdmissionFactory)
    payment_mode = PaymentMode.UPI
    receipt_no = factory.Sequence(lambda n: f"RCP/2627/{n:05d}")
    payment_date = datetime.date(2026, 4, 10)
    recorded_by = factory.SubFactory(UserFactory)


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    person = factory.SubFactory(PersonFactory)
    payment_type = factory.SubFactory(PaymentTypeFactory)
    amount = "1500.00"
    payment_mode = PaymentMode.UPI
    payment_date = datetime.date(2026, 4, 10)
    recorded_by = factory.SubFactory(UserFactory)
    confirmation_no = factory.Sequence(lambda n: f"PCF/2627/{n:05d}")
