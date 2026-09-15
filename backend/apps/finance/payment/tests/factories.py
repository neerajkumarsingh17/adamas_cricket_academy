import datetime

import factory
from factory.django import DjangoModelFactory

from apps.admissions.admission.tests.factories import DirectAdmissionFactory
from apps.finance.payment.models import AdmissionPayment, PaymentMode
from apps.iam.tests.factories import UserFactory


class AdmissionPaymentFactory(DjangoModelFactory):
    class Meta:
        model = AdmissionPayment

    admission = factory.SubFactory(DirectAdmissionFactory)
    payment_mode = PaymentMode.UPI
    receipt_no = factory.Sequence(lambda n: f"RCP/2627/{n:05d}")
    payment_date = datetime.date(2026, 4, 10)
    recorded_by = factory.SubFactory(UserFactory)
