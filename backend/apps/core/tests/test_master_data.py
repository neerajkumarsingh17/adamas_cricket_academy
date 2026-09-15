import pytest
from django.contrib import admin
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.core.models import (
    AgeCategory,
    AssessmentCriterion,
    DocumentType,
    EnquirySource,
    Programme,
    Season,
    TrainingType,
    Venue,
)
from apps.iam.tests.factories import UserFactory


@pytest.mark.django_db
def test_seed_master_data_creates_expected_counts():
    call_command("seed_master_data")

    assert Programme.objects.count() == 2
    # 10 single-year trial bands (u10..u19) + 6 admission-bracket
    # categories (under12/14/16/19/23, senior) — see ADMISSION_AGE_BRACKETS.
    assert AgeCategory.objects.count() == 16
    assert Venue.objects.count() == 2
    assert Season.objects.count() == 1
    assert EnquirySource.objects.count() == 9
    assert TrainingType.objects.count() == 5
    assert DocumentType.objects.count() == 6
    assert AssessmentCriterion.objects.count() == 9


@pytest.mark.django_db
def test_seed_master_data_matches_documented_enquiry_sources():
    """docs/01-data-model.md section 5, Enquiry.source — verbatim."""
    call_command("seed_master_data")

    assert set(EnquirySource.objects.values_list("code", flat=True)) == {
        "website",
        "social",
        "walk_in",
        "school",
        "club",
        "referral",
        "tournament",
        "trial",
        "advertisement",
    }


@pytest.mark.django_db
def test_seed_master_data_covers_all_nine_assessment_groups():
    call_command("seed_master_data")

    assert set(AssessmentCriterion.objects.values_list("group", flat=True)) == {
        "batting",
        "bowling",
        "fielding",
        "wicketkeeping",
        "fitness",
        "game_awareness",
        "discipline",
        "attitude",
        "potential",
    }


@pytest.mark.django_db
def test_seed_master_data_age_categories_span_u10_to_u19():
    call_command("seed_master_data")

    codes = set(AgeCategory.objects.values_list("code", flat=True))
    assert {f"u{n}" for n in range(10, 20)} <= codes


@pytest.mark.django_db
def test_seed_master_data_admission_age_brackets():
    """The coarser playing-group brackets AdmissionIntake.age_category
    snapshots against — distinct codes from the u10..u19 trial bands above,
    since they mean a different granularity (see seed_master_data.py's
    ADMISSION_AGE_BRACKETS comment).
    """
    call_command("seed_master_data")

    codes = set(AgeCategory.objects.values_list("code", flat=True))
    assert {"under12", "under14", "under16", "under19", "under23", "senior"} <= codes


@pytest.mark.django_db
def test_seed_master_data_is_idempotent():
    call_command("seed_master_data")
    counts_before = {
        model: model.objects.count()
        for model in [
            Programme,
            AgeCategory,
            Venue,
            Season,
            EnquirySource,
            TrainingType,
            DocumentType,
            AssessmentCriterion,
        ]
    }

    call_command("seed_master_data")

    for model, count in counts_before.items():
        assert model.objects.count() == count, f"{model.__name__} count changed on re-seed"


@pytest.mark.parametrize(
    "model",
    [
        Programme,
        AgeCategory,
        Venue,
        Season,
        EnquirySource,
        TrainingType,
        DocumentType,
        AssessmentCriterion,
    ],
)
def test_every_master_data_model_is_registered_in_admin(model):
    assert admin.site.is_registered(model), f"{model.__name__} is not registered in admin"


@pytest.mark.django_db
def test_admin_added_programme_appears_in_api_without_code_change(client):
    """The Check: an administrator adds a new programme through Django
    admin and it appears in the API without a code change.
    """
    admin_user = UserFactory(is_staff=True, is_superuser=True)
    admin_user.set_password("s3cret-pass")
    admin_user.save()

    client.force_login(admin_user)
    response = client.post(
        "/admin/core/programme/add/",
        {
            "code": "goalkeeper-academy",
            "name": "Goalkeeper Academy",
            "description": "",
            "is_active": "on",
        },
    )
    assert response.status_code == 302, response.content  # redirect on successful admin save
    assert Programme.objects.filter(code="goalkeeper-academy").exists()

    api_client = APIClient()
    api_client.force_authenticate(user=admin_user)
    api_response = api_client.get("/api/v1/master/programmes/")

    assert api_response.status_code == 200
    names = {row["name"] for row in api_response.data["results"]}
    assert "Goalkeeper Academy" in names


@pytest.mark.django_db
def test_master_data_read_endpoints_require_authentication():
    response = APIClient().get("/api/v1/master/age-categories/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_master_data_read_endpoint_is_read_only():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/master/venues/", {"code": "hack", "name": "Hack"})

    assert response.status_code == 405
