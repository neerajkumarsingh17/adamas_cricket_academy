"""SOP §78 — one athlete, one digital profile.

Every code path that creates a Person must call resolve_person() first
(CLAUDE.md rule 1). This module owns duplicate detection: normalising
mobile numbers, computing the dedupe_key, and matching against it.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from typing import TypedDict

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, Value
from django.db.models.functions import Concat, Lower
from django.utils.text import slugify

NAME_SIMILARITY_THRESHOLD = 0.85

_INDIA_COUNTRY_CODE = "91"


def normalize_mobile_e164(raw: str) -> str:
    """Normalise an Indian mobile number to E.164, e.g. "+919876543210".

    Accepts a bare 10-digit number, a leading-0 domestic form, a "91"-
    prefixed form, or anything already carrying a "+".
    """
    digits = re.sub(r"\D", "", raw)
    if raw.strip().startswith("+"):
        return f"+{digits}"
    if digits.startswith(_INDIA_COUNTRY_CODE) and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 11:
        return f"+{_INDIA_COUNTRY_CODE}{digits[1:]}"
    if len(digits) == 10:
        return f"+{_INDIA_COUNTRY_CODE}{digits}"
    raise ValueError(f"Cannot normalise mobile number to E.164: {raw!r}")


def compute_dedupe_key(*, first_name: str, last_name: str, date_of_birth: date, mobile: str) -> str:
    """docs/01-data-model.md section 1:
    sha256(slugify(first+last) + "|" + dob.isoformat() + "|" + primary_guardian_mobile)

    `mobile` must already be E.164-normalised — callers hash the same
    representation that gets stored, or matches silently stop working.
    """
    name_slug = slugify(f"{first_name}{last_name}")
    raw = f"{name_slug}|{date_of_birth.isoformat()}|{mobile}"
    return hashlib.sha256(raw.encode()).hexdigest()


class _PersonResolveRequired(TypedDict):
    first_name: str
    last_name: str
    date_of_birth: date
    guardian_mobile: str


class PersonResolveInput(_PersonResolveRequired, total=False):
    middle_name: str


@dataclass
class PersonMatch:
    exact: list = field(default_factory=list)
    fuzzy: list = field(default_factory=list)

    @property
    def found(self) -> bool:
        return bool(self.exact or self.fuzzy)


def split_name(full_name: str) -> tuple[str, str]:
    """ "Arjun Ganguly" -> ("Arjun", "Ganguly"). Every intake form in this
    system (Enquiry, the /persons/search duplicate check, ...) captures a
    single free-text name field, not separate first/last inputs, but
    resolve_person() and Person itself need them split — this is the one
    place that split happens, so every caller splits a name the same way.
    """
    first, _, rest = full_name.strip().partition(" ")
    return first, rest


def resolve_person_by_name(
    *, full_name: str, date_of_birth: date, guardian_mobile: str
) -> PersonMatch:
    """resolve_person(), taking the single free-text name intake forms
    actually capture instead of pre-split first/last fields.
    """
    first_name, last_name = split_name(full_name)
    return resolve_person(
        {
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth,
            "guardian_mobile": guardian_mobile,
        }
    )


def resolve_person(data: PersonResolveInput) -> PersonMatch:
    """The one and only duplicate-detection entry point (CLAUDE.md rule 1).

    Returns exact matches on dedupe_key, plus fuzzy candidates scoring on
    (name similarity >= 0.85) AND (DOB exact OR guardian mobile exact).
    """
    from .models import Person

    mobile = normalize_mobile_e164(data["guardian_mobile"])
    dedupe_key = compute_dedupe_key(
        first_name=data["first_name"],
        last_name=data["last_name"],
        date_of_birth=data["date_of_birth"],
        mobile=mobile,
    )

    exact = list(Person.objects.filter(dedupe_key=dedupe_key))

    candidate_name = f"{data['first_name']} {data['last_name']}".lower()
    fuzzy = list(
        Person.objects.annotate(full_name=Lower(Concat("first_name", Value(" "), "last_name")))
        .annotate(similarity=TrigramSimilarity("full_name", candidate_name))
        .filter(similarity__gte=NAME_SIMILARITY_THRESHOLD)
        .filter(Q(date_of_birth=data["date_of_birth"]) | Q(mobile=mobile))
        .exclude(pk__in=[person.pk for person in exact])
    )

    return PersonMatch(exact=exact, fuzzy=fuzzy)
