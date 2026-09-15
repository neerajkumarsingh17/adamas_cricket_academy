import pytest
from django.db import IntegrityError

from apps.people.models import StaffType

from .factories import StaffFactory


@pytest.mark.django_db
def test_staff_factory_creates_valid_staff():
    staff = StaffFactory(staff_type=StaffType.COACH)

    assert staff.person_id is not None
    assert staff.is_active is True


@pytest.mark.django_db
def test_employee_code_is_unique():
    StaffFactory(employee_code="EMP00001")

    with pytest.raises(IntegrityError):
        StaffFactory(employee_code="EMP00001")
