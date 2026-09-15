import datetime

import pytest
from rest_framework.test import APIClient

from apps.admissions.admission import services
from apps.admissions.trial.tests.factories import TrialRegistrationFactory, TrialResultFactory
from apps.core.tests.factories import DocumentTypeFactory, ProgrammeFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory


def _user_with_role(role_code: str):
    user = UserFactory()
    role = Role.objects.get(code=role_code)
    UserRole.objects.create(user=user, role=role, valid_from=datetime.date(2020, 1, 1))
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_open_an_admission_from_a_selected_trial(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    registration = TrialRegistrationFactory(person=PersonFactory())
    TrialResultFactory(registration=registration, outcome="selected")
    programme = ProgrammeFactory()

    response = api_client.post(
        "/api/v1/admissions/",
        {"trial_registration": str(registration.id), "programme": str(programme.id)},
    )

    assert response.status_code == 201, response.data
    assert response.data["application_no"].startswith("ADM/")
    assert response.data["step"] == "draft"


@pytest.mark.django_db
def test_opening_admission_from_a_non_selected_trial_is_rejected(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    registration = TrialRegistrationFactory()
    TrialResultFactory(registration=registration, outcome="waitlisted", review_on="2026-12-01")

    response = api_client.post(
        "/api/v1/admissions/",
        {"trial_registration": str(registration.id), "programme": str(ProgrammeFactory().id)},
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_accounts_role_cannot_open_an_admission(api_client, seeded_roles):
    # docs/03-rbac.md: accounts has only "V" on enquiry/trial/admission.
    user = _user_with_role("accounts")
    api_client.force_authenticate(user)
    registration = TrialRegistrationFactory()
    TrialResultFactory(registration=registration, outcome="selected")

    response = api_client.post(
        "/api/v1/admissions/",
        {"trial_registration": str(registration.id), "programme": str(ProgrammeFactory().id)},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_patch_can_only_touch_residential_not_step(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    registration = TrialRegistrationFactory(person=PersonFactory())
    TrialResultFactory(registration=registration, outcome="selected")
    open_response = api_client.post(
        "/api/v1/admissions/",
        {"trial_registration": str(registration.id), "programme": str(ProgrammeFactory().id)},
    )
    admission_id = open_response.data["id"]

    response = api_client.patch(
        f"/api/v1/admissions/{admission_id}/", {"residential": True, "step": "approved"}
    )

    assert response.status_code == 200, response.data
    assert response.data["residential"] is True
    assert response.data["step"] == "draft"


@pytest.mark.django_db
def test_accounts_can_record_a_payment_despite_lacking_admission_edit(api_client, seeded_roles):
    # docs/04-state-machines.md section 1 explicitly names Accounts as
    # permitted on fee_pending -> fee_cleared, even though docs/03-rbac.md's
    # matrix gives Accounts only "V" on this module — the override this
    # endpoint's own view implements.
    admin_user = _user_with_role("administration")
    api_client.force_authenticate(admin_user)
    registration = TrialRegistrationFactory(person=PersonFactory())
    TrialResultFactory(registration=registration, outcome="selected")
    admission_id = api_client.post(
        "/api/v1/admissions/",
        {"trial_registration": str(registration.id), "programme": str(ProgrammeFactory().id)},
    ).data["id"]
    advance_url = f"/api/v1/admissions/{admission_id}/advance/"
    api_client.post(advance_url, {"to_step": "documents_pending"})
    api_client.post(advance_url, {"to_step": "documents_verified"})
    api_client.post(advance_url, {"to_step": "fee_pending"})

    accounts_user = _user_with_role("accounts")
    api_client.force_authenticate(accounts_user)
    response = api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"reference": "UPI-REF-999", "amount": "4200.00", "payment_method": "upi"},
    )

    assert response.status_code == 200, response.data
    assert response.data["fee_payment_status"] == "paid"
    assert response.data["fee_payment_method"] == "upi"
    assert response.data["fee_amount"] == "4200.00"


def _direct_admission_payload(**overrides):
    payload = {
        "first_name": "Rohan",
        "last_name": "Verma",
        "date_of_birth": "2012-05-01",
        "gender": "M",
        "mobile": "9876500001",
        "programme": str(ProgrammeFactory().id),
        "reason": "Reputation admission — state-level player.",
    }
    payload.update(overrides)
    return payload


def _create_old_style_direct_admission(*, requested_by, **overrides):
    """The pre-existing trial-waiver direct-admission service call, used
    directly rather than through `POST /admissions/direct/` — that URL
    now serves the new fee-first wizard's intake-based creation instead
    (Prompt D). `open_direct_admission` itself, and everything downstream
    of it (`/advance`, `/record-payment`, `/enable-portal`, `/approve`,
    `/mine`), is untouched — only the HTTP entry point for *creating* one
    moved.
    """
    defaults = {
        "first_name": "Rohan",
        "last_name": "Verma",
        "date_of_birth": datetime.date(2012, 5, 1),
        "gender": "M",
        "mobile": "9876500001",
        "email": "",
        "address_line1": "",
        "city": "",
        "state": "",
        "pincode": "",
        "programme": ProgrammeFactory(),
        "reason": "Reputation admission — state-level player.",
        "residential": False,
    }
    defaults.update(overrides)
    return services.open_direct_admission(requested_by=requested_by, **defaults)


# test_administration_can_open_a_direct_admission used to live here,
# posting to POST /admissions/direct/ — that URL now serves the new
# fee-first wizard's intake-based creation (Prompt D), and the assertions
# this made (step=draft, source=direct, person.first_name) are exactly
# what apps.admissions.admission.tests.test_services.py's
# test_open_direct_admission_skips_the_waiver_gate already covers at the
# service level — removed as a redundant duplicate rather than kept
# under a misleading name for an HTTP path that no longer does this.


@pytest.mark.django_db
def test_accounts_cannot_open_a_direct_admission(api_client, seeded_roles):
    # docs/03-rbac.md: accounts has only "V" on admission, not "add".
    user = _user_with_role("accounts")
    api_client.force_authenticate(user)

    response = api_client.post("/api/v1/admissions/direct/", _direct_admission_payload())

    assert response.status_code == 403


@pytest.mark.django_db
def test_administration_can_finalize_a_direct_admission_without_academy_head(
    api_client, seeded_roles
):
    # Step 2.1 is the *only* forward path for a direct admission now — fee
    # first, then documents (admission/state.py's `_guard_documents_pending`
    # refuses the old documents-first order for one of these).
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    admission_id = str(_create_old_style_direct_admission(requested_by=user).id)
    api_client.post(f"/api/v1/admissions/{admission_id}/advance/", {"to_step": "fee_pending"})
    api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"reference": "UPI-REF-DIRECT", "amount": "5000.00", "payment_method": "upi"},
    )
    api_client.post(f"/api/v1/admissions/{admission_id}/enable-portal/")
    api_client.post(
        f"/api/v1/admissions/{admission_id}/advance/", {"to_step": "documents_verified"}
    )

    response = api_client.post(f"/api/v1/admissions/{admission_id}/approve/")

    assert response.status_code == 201, response.data
    assert response.data["student"]["status"] == "active"


@pytest.mark.django_db
def test_administration_can_enable_portal_access_after_payment(api_client, seeded_roles):
    """Step 2.1: fee first, then Administration switches on the
    candidate's own login and the admission moves straight to document
    collection in one action.
    """
    from apps.iam.models import User

    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    admission_id = str(
        _create_old_style_direct_admission(requested_by=user, mobile="9876500005").id
    )
    api_client.post(
        f"/api/v1/admissions/{admission_id}/advance/", {"to_step": "fee_pending"}
    )
    api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"reference": "UPI-REF-PORTAL", "amount": "5000.00", "payment_method": "upi"},
    )

    response = api_client.post(f"/api/v1/admissions/{admission_id}/enable-portal/")

    assert response.status_code == 200, response.data
    assert response.data["step"] == "documents_pending"
    assert response.data["portal_enabled"] is True
    assert User.objects.filter(person_id=response.data["person"]["id"]).exists()


@pytest.mark.django_db
def test_enabling_portal_access_on_a_trial_based_admission_is_rejected(api_client, seeded_roles):
    admin_user = _user_with_role("administration")
    api_client.force_authenticate(admin_user)
    registration = TrialRegistrationFactory(person=PersonFactory())
    TrialResultFactory(registration=registration, outcome="selected")
    admission_id = api_client.post(
        "/api/v1/admissions/",
        {"trial_registration": str(registration.id), "programme": str(ProgrammeFactory().id)},
    ).data["id"]

    response = api_client.post(f"/api/v1/admissions/{admission_id}/enable-portal/")

    assert response.status_code == 400


@pytest.mark.django_db
def test_candidate_can_fetch_their_own_in_progress_admission(api_client, seeded_roles):
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    admin_user = _user_with_role("administration")
    api_client.force_authenticate(admin_user)
    admission_id = str(
        _create_old_style_direct_admission(requested_by=admin_user, mobile="9876500006").id
    )
    api_client.post(f"/api/v1/admissions/{admission_id}/advance/", {"to_step": "fee_pending"})
    api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"reference": "UPI-REF-MINE", "amount": "5000.00", "payment_method": "upi"},
    )
    api_client.post(f"/api/v1/admissions/{admission_id}/enable-portal/")
    person_id = api_client.get(f"/api/v1/admissions/{admission_id}/").data["person"]["id"]

    from apps.iam.models import User

    candidate_user = User.objects.get(person_id=person_id)
    api_client.force_authenticate(candidate_user)

    response = api_client.get("/api/v1/admissions/mine/")

    assert response.status_code == 200, response.data
    assert response.data["id"] == admission_id


@pytest.mark.django_db
def test_administration_cannot_finalize_a_trial_based_admission(api_client, seeded_roles):
    # The direct-admission bypass is scoped to admissions with no
    # trial_registration — a trial-based admission still needs Academy
    # Head's `approve` verb (docs/03-rbac.md), not Administration's `edit`.
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    admin_user = _user_with_role("administration")
    api_client.force_authenticate(admin_user)
    registration = TrialRegistrationFactory(person=PersonFactory())
    TrialResultFactory(registration=registration, outcome="selected")
    admission_id = api_client.post(
        "/api/v1/admissions/",
        {"trial_registration": str(registration.id), "programme": str(ProgrammeFactory().id)},
    ).data["id"]
    advance_url = f"/api/v1/admissions/{admission_id}/advance/"
    api_client.post(advance_url, {"to_step": "documents_pending"})
    api_client.post(advance_url, {"to_step": "documents_verified"})
    api_client.post(advance_url, {"to_step": "fee_pending"})
    api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"reference": "UPI-REF-TRIAL", "amount": "5000.00", "payment_method": "upi"},
    )

    response = api_client.post(f"/api/v1/admissions/{admission_id}/approve/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_coach_cannot_record_a_payment(api_client, seeded_roles):
    admin_user = _user_with_role("administration")
    api_client.force_authenticate(admin_user)
    registration = TrialRegistrationFactory(person=PersonFactory())
    TrialResultFactory(registration=registration, outcome="selected")
    admission_id = api_client.post(
        "/api/v1/admissions/",
        {"trial_registration": str(registration.id), "programme": str(ProgrammeFactory().id)},
    ).data["id"]

    coach_user = _user_with_role("coach")
    api_client.force_authenticate(coach_user)
    response = api_client.post(
        f"/api/v1/admissions/{admission_id}/record-payment/",
        {"reference": "UPI-REF-998", "payment_method": "upi"},
    )

    assert response.status_code == 403
