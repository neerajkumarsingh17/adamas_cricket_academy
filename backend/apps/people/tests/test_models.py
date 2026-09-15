import pytest

from apps.people.services import compute_dedupe_key

from .factories import PersonFactory


@pytest.mark.django_db
def test_save_normalises_mobile_to_e164():
    person = PersonFactory(mobile="9876543210")

    assert person.mobile == "+919876543210"


@pytest.mark.django_db
def test_save_computes_dedupe_key():
    person = PersonFactory(
        first_name="Rohan",
        last_name="Sharma",
        mobile="9876543210",
    )

    expected = compute_dedupe_key(
        first_name="Rohan",
        last_name="Sharma",
        date_of_birth=person.date_of_birth,
        mobile="+919876543210",
    )
    assert person.dedupe_key == expected


@pytest.mark.django_db
def test_dedupe_key_recomputed_on_update():
    person = PersonFactory(first_name="Rohan")
    original_key = person.dedupe_key

    person.first_name = "Mohan"
    person.save()

    assert person.dedupe_key != original_key
