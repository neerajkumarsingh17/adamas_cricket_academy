import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.core.tests.factories import PaymentTypeFactory
from apps.people.tests.factories import PersonFactory

from .factories import AdmissionPaymentFactory, PaymentFactory


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


@pytest.mark.django_db
def test_recurring_payment_type_requires_billing_period():
    recurring = PaymentTypeFactory(is_recurring=True)
    payment = PaymentFactory.build(payment_type=recurring, billing_period=None)
    with pytest.raises(ValidationError, match="billing_period"):
        payment.clean()


@pytest.mark.django_db
def test_billing_period_must_be_the_first_of_the_month():
    recurring = PaymentTypeFactory(is_recurring=True)
    payment = PaymentFactory.build(
        payment_type=recurring, billing_period=datetime.date(2026, 1, 15)
    )
    with pytest.raises(ValidationError, match="billing_period"):
        payment.clean()


@pytest.mark.django_db
def test_one_off_payment_type_does_not_require_billing_period():
    one_off = PaymentTypeFactory(is_recurring=False)
    payment = PaymentFactory.build(payment_type=one_off, billing_period=None)
    payment.clean()  # must not raise


@pytest.mark.django_db
def test_same_person_type_month_cannot_be_recorded_twice():
    """The partial unique index (Meta.constraints) — prevents double-
    charging the same recurring month for the same person+type."""
    recurring = PaymentTypeFactory(is_recurring=True)
    person = PersonFactory()
    period = datetime.date(2026, 1, 1)
    PaymentFactory(person=person, payment_type=recurring, billing_period=period)
    with pytest.raises(IntegrityError):
        PaymentFactory(person=person, payment_type=recurring, billing_period=period)


@pytest.mark.django_db
def test_one_off_type_may_have_multiple_null_period_rows():
    """The unique constraint's partial condition only bites when
    billing_period is set — a one-off type isn't limited to one row."""
    one_off = PaymentTypeFactory(is_recurring=False)
    person = PersonFactory()
    PaymentFactory(person=person, payment_type=one_off, billing_period=None)
    PaymentFactory(person=person, payment_type=one_off, billing_period=None)  # must not raise
