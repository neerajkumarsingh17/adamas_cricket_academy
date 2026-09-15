import datetime

import pytest
from django.core.exceptions import ValidationError

from .factories import AdmissionPaymentFactory


@pytest.mark.django_db
def test_payment_date_cannot_be_in_the_future():
    payment = AdmissionPaymentFactory.build(
        payment_date=datetime.date.today() + datetime.timedelta(days=1)
    )
    with pytest.raises(ValidationError, match="payment_date"):
        payment.clean()


@pytest.mark.django_db
def test_payment_date_today_is_valid():
    payment = AdmissionPaymentFactory.build(payment_date=datetime.date.today())
    payment.clean()  # must not raise
