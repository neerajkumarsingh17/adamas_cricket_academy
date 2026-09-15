import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .factories import AdmissionFeeLineFactory


@pytest.mark.django_db
def test_fee_line_amount_cannot_be_negative():
    line = AdmissionFeeLineFactory.build(amount="-1.00")
    with pytest.raises(ValidationError):
        line.full_clean()


@pytest.mark.django_db
def test_fee_line_is_unique_per_admission_and_fee_head():
    line = AdmissionFeeLineFactory()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AdmissionFeeLineFactory(admission=line.admission, fee_head=line.fee_head)
