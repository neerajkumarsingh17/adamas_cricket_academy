from decimal import Decimal

import pytest

from apps.finance.fee.tests.factories import AdmissionFeeLineFactory

from .factories import DirectAdmissionFactory


@pytest.mark.django_db
def test_fee_total_equals_sum_of_its_lines():
    admission = DirectAdmissionFactory()
    AdmissionFeeLineFactory(admission=admission, amount="500.00")
    line = AdmissionFeeLineFactory(admission=admission, amount="1200.00")

    assert admission.fee_total == Decimal("1700.00")

    line.amount = Decimal("1500.00")
    line.save()

    assert admission.fee_total == Decimal("2000.00")


@pytest.mark.django_db
def test_fee_total_is_zero_with_no_lines():
    admission = DirectAdmissionFactory()

    assert admission.fee_total == Decimal("0")


@pytest.mark.django_db
def test_fee_total_in_words_reflects_the_current_total():
    admission = DirectAdmissionFactory()
    AdmissionFeeLineFactory(admission=admission, amount="25500.00")

    assert admission.fee_total_in_words == "Rupees Twenty Five Thousand Five Hundred only"
