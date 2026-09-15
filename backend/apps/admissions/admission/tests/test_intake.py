import datetime

import pytest
from django.core.exceptions import ValidationError

from apps.admissions.admission.models import AdmissionCategory, DaysPerWeek, PreferredSlot
from apps.core.services.age import category_for
from apps.core.tests.factories import AgeCategoryFactory, SeasonFactory

from .factories import AdmissionIntakeFactory


@pytest.mark.django_db
def test_residential_intake_with_days_per_week_fails_validation():
    intake = AdmissionIntakeFactory.build(
        admission_category=AdmissionCategory.RESIDENTIAL,
        days_per_week=DaysPerWeek.THREE,
        preferred_slot=PreferredSlot.EVENING,
        local_guardian_name="Local Guardian",
        local_guardian_mobile="+919800000003",
    )
    with pytest.raises(ValidationError, match="days_per_week"):
        intake.clean()


@pytest.mark.django_db
def test_residential_intake_requires_local_guardian():
    intake = AdmissionIntakeFactory.build(
        admission_category=AdmissionCategory.RESIDENTIAL,
        days_per_week=None,
        preferred_slot="",
        local_guardian_name="",
        local_guardian_mobile="",
    )
    with pytest.raises(ValidationError, match="local_guardian_name"):
        intake.clean()


@pytest.mark.django_db
def test_non_residential_intake_requires_days_per_week_and_slot():
    intake = AdmissionIntakeFactory.build(
        admission_category=AdmissionCategory.NON_RESIDENTIAL,
        days_per_week=None,
        preferred_slot="",
    )
    with pytest.raises(ValidationError, match="days_per_week"):
        intake.clean()


@pytest.mark.django_db
def test_non_residential_intake_rejects_local_guardian_fields():
    intake = AdmissionIntakeFactory.build(
        admission_category=AdmissionCategory.NON_RESIDENTIAL,
        local_guardian_name="Should not be here",
    )
    with pytest.raises(ValidationError, match="local_guardian_name"):
        intake.clean()


@pytest.mark.django_db
def test_emergency_contact_must_differ_from_guardian_mobile():
    intake = AdmissionIntakeFactory.build(
        guardian_mobile="+919800000001", emergency_contact="+919800000001"
    )
    with pytest.raises(ValidationError, match="emergency_contact"):
        intake.clean()


@pytest.mark.django_db
def test_student_mobile_must_differ_from_guardian_mobile():
    intake = AdmissionIntakeFactory.build(
        guardian_mobile="+919800000001", student_mobile="+919800000001"
    )
    with pytest.raises(ValidationError, match="student_mobile"):
        intake.clean()


@pytest.mark.django_db
def test_date_of_birth_must_be_in_the_past():
    intake = AdmissionIntakeFactory.build(date_of_birth=datetime.date.today())
    with pytest.raises(ValidationError, match="date_of_birth"):
        intake.clean()


@pytest.mark.django_db
def test_computed_age_must_be_between_5_and_45():
    intake = AdmissionIntakeFactory.build(date_of_birth=datetime.date(1970, 1, 1))
    with pytest.raises(ValidationError, match="date_of_birth"):
        intake.clean()


@pytest.mark.django_db
def test_age_category_resolves_from_real_age_category_rows():
    """DOB 2013-08-19 against a 2026-27 season cut off 2026-04-01 is a
    completed 12 years old — must resolve to whichever *seeded* AgeCategory
    row actually covers age 12, not a hardcoded U14 constant.
    """
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under12", min_age=5, max_age=11)
    u14 = AgeCategoryFactory(code="under14", min_age=12, max_age=13)
    AgeCategoryFactory(code="under16", min_age=14, max_age=15)

    resolved = category_for(datetime.date(2013, 8, 19), season)

    assert resolved == u14


@pytest.mark.django_db
def test_admission_intake_save_computes_age_category_not_accepted_as_input():
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", min_age=12, max_age=13)
    wrong_category = AgeCategoryFactory(code="under23", min_age=19, max_age=22)

    intake = AdmissionIntakeFactory(
        season=season,
        date_of_birth=datetime.date(2013, 8, 19),
        age_category=wrong_category,  # attempted override — save() must ignore this
    )

    assert intake.age_category.code == "under14"
