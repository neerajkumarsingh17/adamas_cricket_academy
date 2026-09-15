import factory
from factory.django import DjangoModelFactory

from apps.admissions.admission.tests.factories import DirectAdmissionFactory
from apps.core.tests.factories import FeeHeadFactory
from apps.finance.fee.models import AdmissionFeeLine


class AdmissionFeeLineFactory(DjangoModelFactory):
    class Meta:
        model = AdmissionFeeLine

    admission = factory.SubFactory(DirectAdmissionFactory)
    fee_head = factory.SubFactory(FeeHeadFactory)
    amount = "1000.00"
