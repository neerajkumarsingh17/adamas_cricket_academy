import hashlib
from datetime import date

import pytest
from django.utils.text import slugify

from apps.people.services import compute_dedupe_key, normalize_mobile_e164, resolve_person

from .factories import PersonFactory


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9876543210", "+919876543210"),
        ("09876543210", "+919876543210"),
        ("919876543210", "+919876543210"),
        ("+919876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("(+91) 98765-43210", "+919876543210"),
    ],
)
def test_normalize_mobile_e164(raw, expected):
    assert normalize_mobile_e164(raw) == expected


def test_normalize_mobile_e164_rejects_unparseable_input():
    with pytest.raises(ValueError):
        normalize_mobile_e164("12345")


def test_compute_dedupe_key_matches_documented_formula():
    """docs/01-data-model.md section 1:
    sha256(slugify(first+last) + "|" + dob.isoformat() + "|" + primary_guardian_mobile)
    """
    expected = hashlib.sha256(
        f"{slugify('RohanSharma')}|2015-06-15|+919876543210".encode()
    ).hexdigest()

    actual = compute_dedupe_key(
        first_name="Rohan",
        last_name="Sharma",
        date_of_birth=date(2015, 6, 15),
        mobile="+919876543210",
    )
    assert actual == expected


@pytest.mark.django_db
def test_resolve_person_finds_exact_match_on_same_name_dob_and_guardian_mobile():
    """SOP §78 — the most important test in the repo. A second attempt with
    the same name, DOB and guardian mobile must be pointed at the existing
    Person, not allowed to create a duplicate.
    """
    existing = PersonFactory(
        first_name="Rohan",
        last_name="Sharma",
        date_of_birth=date(2015, 6, 15),
        mobile="9876543210",
    )

    match = resolve_person(
        {
            "first_name": "Rohan",
            "last_name": "Sharma",
            "date_of_birth": date(2015, 6, 15),
            "guardian_mobile": "9876543210",
        }
    )

    assert match.exact == [existing]


@pytest.mark.django_db
def test_resolve_person_matches_despite_different_mobile_formatting():
    existing = PersonFactory(
        first_name="Rohan",
        last_name="Sharma",
        date_of_birth=date(2015, 6, 15),
        mobile="9876543210",
    )

    match = resolve_person(
        {
            "first_name": "Rohan",
            "last_name": "Sharma",
            "date_of_birth": date(2015, 6, 15),
            "guardian_mobile": "+91-98765-43210",
        }
    )

    assert match.exact == [existing]


@pytest.mark.django_db
def test_resolve_person_finds_fuzzy_match_on_similar_name_and_same_dob():
    # "Narayanan" vs "Narayan" scores ~0.88 trigram similarity — above the
    # 0.85 threshold and a realistic transliteration variant, not a coin flip.
    existing = PersonFactory(
        first_name="Aditya",
        last_name="Narayanan",
        date_of_birth=date(2015, 6, 15),
        mobile="9876543210",
    )

    match = resolve_person(
        {
            "first_name": "Aditya",
            "last_name": "Narayan",
            "date_of_birth": date(2015, 6, 15),
            "guardian_mobile": "9999999999",
        }
    )

    assert match.exact == []
    assert existing in match.fuzzy


@pytest.mark.django_db
def test_resolve_person_finds_fuzzy_match_on_similar_name_and_same_guardian_mobile():
    existing = PersonFactory(
        first_name="Aditya",
        last_name="Narayanan",
        date_of_birth=date(2015, 6, 15),
        mobile="9876543210",
    )

    match = resolve_person(
        {
            "first_name": "Aditya",
            "last_name": "Narayan",
            "date_of_birth": date(2001, 1, 1),
            "guardian_mobile": "9876543210",
        }
    )

    assert match.exact == []
    assert existing in match.fuzzy


@pytest.mark.django_db
def test_resolve_person_returns_no_match_when_nothing_matches():
    PersonFactory(
        first_name="Rohan",
        last_name="Sharma",
        date_of_birth=date(2015, 6, 15),
        mobile="9876543210",
    )

    match = resolve_person(
        {
            "first_name": "Priya",
            "last_name": "Iyer",
            "date_of_birth": date(2010, 1, 1),
            "guardian_mobile": "9999999999",
        }
    )

    assert not match.found


@pytest.mark.django_db
def test_resolve_person_excludes_exact_matches_from_fuzzy_list():
    existing = PersonFactory(
        first_name="Rohan",
        last_name="Sharma",
        date_of_birth=date(2015, 6, 15),
        mobile="9876543210",
    )

    match = resolve_person(
        {
            "first_name": "Rohan",
            "last_name": "Sharma",
            "date_of_birth": date(2015, 6, 15),
            "guardian_mobile": "9876543210",
        }
    )

    assert match.exact == [existing]
    assert existing not in match.fuzzy
