"""category_for(dob, season) — the direct-admission intake's age-category
snapshot (docs/01-data-model.md section 5, AdmissionIntake.age_category).

Deliberately reads AgeCategory rows rather than a hardcoded band table —
adding a new category (or moving U14's upper bound) changes what this
returns without a release. The category is computed once, at intake save
time, and stored — never recomputed on read, since recomputing next season
would silently move a student out of the group their seat was sold against.
"""

import datetime

from django.core.exceptions import ValidationError

from apps.core.models import AgeCategory, Season


def age_in_completed_years(dob: datetime.date, as_on: datetime.date) -> int:
    years = as_on.year - dob.year
    if (as_on.month, as_on.day) < (dob.month, dob.day):
        years -= 1
    return years


def category_for(dob: datetime.date, season: Season) -> AgeCategory:
    if season.age_cutoff_date is None:
        raise ValidationError(
            {"season": f"{season.code!r} has no age_cutoff_date configured."}
        )

    age = age_in_completed_years(dob, season.age_cutoff_date)
    category = (
        AgeCategory.objects.filter(is_active=True, min_age__lte=age, max_age__gte=age)
        .order_by("min_age")
        .first()
    )
    if category is None:
        raise ValidationError(
            {
                "date_of_birth": (
                    f"No active age category covers age {age} as on {season.age_cutoff_date}."
                )
            }
        )
    return category
