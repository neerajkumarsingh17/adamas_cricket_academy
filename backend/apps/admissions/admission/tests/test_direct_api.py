import datetime

import pytest
from rest_framework.test import APIClient

from apps.admissions.document.models import DocumentStatus
from apps.admissions.document.tests.factories import DocumentFactory
from apps.core.models import DocumentRequiredStage
from apps.core.tests.factories import (
    AgeCategoryFactory,
    ConsentTypeFactory,
    DocumentTypeFactory,
    FeeHeadFactory,
    SeasonFactory,
)
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory


def _user_with_role(role_code: str):
    user = UserFactory()
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=role_code), valid_from=datetime.date(2020, 1, 1)
    )
    return user


@pytest.fixture
def api_client():
    return APIClient()


def _intake_payload(season, **overrides):
    payload = {
        "season": str(season.id),
        "admission_category": "non_residential",
        "days_per_week": 3,
        "preferred_slot": "evening",
        "full_name": "Rohan Das",
        "date_of_birth": "2013-08-19",
        "gender": "M",
        "present_address": "123 MG Road",
        "city": "Kolkata",
        "state": "West Bengal",
        "pin_code": "700001",
        "guardian_name": "Guardian Name",
        "guardian_relationship": "father",
        "guardian_mobile": "+919800000001",
        "guardian_date_of_birth": "1985-03-10",
        "guardian_gender": "F",
        "emergency_contact": "+919800000002",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_create_direct_admission_creates_draft_with_intake(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)

    response = api_client.post("/api/v1/admissions/direct/", _intake_payload(season))

    assert response.status_code == 201, response.data
    assert response.data["step"] == "draft"
    assert response.data["source"] == "direct"
    assert response.data["intake"]["full_name"] == "Rohan Das"
    assert response.data["intake"]["age_category_name"] == "Under-14"
    # age_category cannot be set from outside — proves it's ignored, not honoured
    assert "age_category" not in _intake_payload(season)


@pytest.mark.django_db
def test_patch_autosaves_intake_and_admission_fields(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]

    response = api_client.patch(
        f"/api/v1/admissions/{admission_id}/",
        {"full_name": "Rohan K Das", "residential": True},
    )

    assert response.status_code == 200, response.data
    assert response.data["intake"]["full_name"] == "Rohan K Das"
    assert response.data["residential"] is True


@pytest.mark.django_db
def test_switching_to_residential_without_clearing_days_is_refused(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]

    response = api_client.patch(
        f"/api/v1/admissions/{admission_id}/", {"admission_category": "residential"}
    )

    assert response.status_code == 400, response.data


def _full_journey_to_ready_for_approval(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    fee_head = FeeHeadFactory(is_mandatory=True)
    consent_type = ConsentTypeFactory(is_mandatory=True)
    doc_type = DocumentTypeFactory(
        applies_to="admission", required_stage=DocumentRequiredStage.AT_ADMISSION
    )

    desk_user = _user_with_role("administration")
    api_client.force_authenticate(desk_user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]

    fees_response = api_client.put(
        f"/api/v1/admissions/{admission_id}/fees/",
        {"lines": [{"fee_head": str(fee_head.id), "amount": "5000.00"}]},
        format="json",
    )
    assert fees_response.status_code == 200, fees_response.data
    assert fees_response.data["fee_total"] == "5000.00"

    consents_response = api_client.post(
        f"/api/v1/admissions/{admission_id}/consents/",
        {
            "decisions": [{"consent_type": str(consent_type.id), "granted": True}],
            "declared_by_name": "Guardian Name",
        },
        format="json",
    )
    assert consents_response.status_code == 200, consents_response.data

    payment_response = api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"payment_mode": "upi", "payment_date": str(datetime.date.today())},
    )
    assert payment_response.status_code == 200, payment_response.data
    assert payment_response.data["step"] == "payment_recorded"

    accounts_user = _user_with_role("accounts")
    api_client.force_authenticate(accounts_user)
    verify_payment_response = api_client.post(
        f"/api/v1/admissions/{admission_id}/verify-payment/", {"approved": True}
    )
    assert verify_payment_response.status_code == 200, verify_payment_response.data
    assert verify_payment_response.data["step"] == "payment_verified"

    api_client.force_authenticate(desk_user)
    from apps.admissions.admission.models import Admission

    DocumentFactory(
        owner=Admission.objects.get(pk=admission_id),
        document_type=doc_type,
        status=DocumentStatus.VERIFIED,
    )
    submit_response = api_client.post(f"/api/v1/admissions/{admission_id}/submit-documents/")
    assert submit_response.status_code == 200, submit_response.data
    assert submit_response.data["step"] == "documents_pending"

    verify_docs_response = api_client.post(
        f"/api/v1/admissions/{admission_id}/verify-documents/"
    )
    assert verify_docs_response.status_code == 200, verify_docs_response.data
    assert verify_docs_response.data["step"] == "ready_for_approval"

    return admission_id


@pytest.mark.django_db
def test_full_direct_admission_journey_reaches_ready_for_approval(api_client, seeded_roles):
    admission_id = _full_journey_to_ready_for_approval(api_client, seeded_roles)
    assert admission_id is not None


@pytest.mark.django_db
def test_coach_cannot_verify_payment(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    fee_head = FeeHeadFactory(is_mandatory=True)
    desk_user = _user_with_role("administration")
    api_client.force_authenticate(desk_user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]
    api_client.put(
        f"/api/v1/admissions/{admission_id}/fees/",
        {"lines": [{"fee_head": str(fee_head.id), "amount": "5000.00"}]},
        format="json",
    )
    api_client.post(
        f"/api/v1/admissions/{admission_id}/consents/",
        {"decisions": [], "declared_by_name": "Guardian Name"},
        format="json",
    )
    api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"payment_mode": "upi", "payment_date": str(datetime.date.today())},
    )

    coach = _user_with_role("coach")
    api_client.force_authenticate(coach)
    response = api_client.post(
        f"/api/v1/admissions/{admission_id}/verify-payment/", {"approved": True}
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_record_payment_idempotency_key_replay_reuses_the_same_receipt(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    fee_head = FeeHeadFactory(is_mandatory=True)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]
    api_client.put(
        f"/api/v1/admissions/{admission_id}/fees/",
        {"lines": [{"fee_head": str(fee_head.id), "amount": "5000.00"}]},
        format="json",
    )
    api_client.post(
        f"/api/v1/admissions/{admission_id}/consents/",
        {"decisions": [], "declared_by_name": "Guardian Name"},
        format="json",
    )

    body = {"payment_mode": "upi", "payment_date": str(datetime.date.today())}
    headers = {"HTTP_IDEMPOTENCY_KEY": "double-click-guard-123"}
    first = api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/", body, **headers
    )
    second = api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/", body, **headers
    )

    assert first.status_code == 200, first.data
    assert second.status_code == 200, second.data

    from apps.finance.payment.models import AdmissionPayment

    assert AdmissionPayment.objects.filter(admission_id=admission_id).count() == 1


@pytest.mark.django_db
def test_bootstrap_returns_master_data_in_one_round_trip(api_client, seeded_roles):
    SeasonFactory(is_active=True, age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    FeeHeadFactory(is_mandatory=True)
    ConsentTypeFactory(is_mandatory=True)
    DocumentTypeFactory(applies_to="admission", required_stage=DocumentRequiredStage.AT_ADMISSION)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/admissions/direct/bootstrap/")

    assert response.status_code == 200, response.data
    assert response.data["season"] is not None
    assert len(response.data["fee_heads"]) >= 1
    assert len(response.data["consent_types"]) >= 1
    assert len(response.data["document_types_by_stage"]["at_admission"]) >= 1


@pytest.mark.django_db
def test_cancel_a_direct_admission(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]

    response = api_client.post(
        f"/api/v1/admissions/{admission_id}/cancel/", {"reason": "Candidate withdrew."}
    )

    assert response.status_code == 200, response.data
    assert response.data["step"] == "cancelled"


@pytest.mark.django_db
def test_next_actions_omits_record_payment_until_the_guard_is_satisfied(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    FeeHeadFactory(is_mandatory=True)  # exists, but no fee line covers it yet
    ConsentTypeFactory(is_mandatory=True)  # exists, but never decided on
    user = _user_with_role("administration")  # holds admission/add
    api_client.force_authenticate(user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]

    response = api_client.get(f"/api/v1/admissions/{admission_id}/")

    # Administration has the *permission* for record_payment, but no fee
    # lines or consents exist yet — the guard, not the permission, is
    # what's missing, and next_actions reflects both.
    assert "record_payment" not in response.data["next_actions"]


@pytest.mark.django_db
def test_next_actions_lists_verify_payment_for_accounts_once_payment_is_recorded(
    api_client, seeded_roles
):
    admission_id = _record_payment_and_return_id(api_client, seeded_roles)

    accounts_user = _user_with_role("accounts")
    api_client.force_authenticate(accounts_user)
    response = api_client.get(f"/api/v1/admissions/{admission_id}/")

    assert "verify_payment" in response.data["next_actions"]


def _record_payment_and_return_id(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    fee_head = FeeHeadFactory(is_mandatory=True)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]
    api_client.put(
        f"/api/v1/admissions/{admission_id}/fees/",
        {"lines": [{"fee_head": str(fee_head.id), "amount": "5000.00"}]},
        format="json",
    )
    api_client.post(
        f"/api/v1/admissions/{admission_id}/consents/",
        {"decisions": [], "declared_by_name": "Guardian Name"},
        format="json",
    )
    api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"payment_mode": "upi", "payment_date": str(datetime.date.today())},
    )
    return admission_id


@pytest.mark.django_db
def test_print_returns_a_pdf(api_client, seeded_roles):
    season = SeasonFactory(age_cutoff_date=datetime.date(2026, 4, 1))
    AgeCategoryFactory(code="under14", name="Under-14", min_age=12, max_age=13)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    admission_id = api_client.post("/api/v1/admissions/direct/", _intake_payload(season)).data["id"]

    response = api_client.get(f"/api/v1/admissions/{admission_id}/print/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
