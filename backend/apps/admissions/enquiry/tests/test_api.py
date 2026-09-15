import datetime

import pytest
from rest_framework.test import APIClient

from apps.core.tests.factories import EnquirySourceFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory

from .factories import EnquiryFactory


def _user_with_role(role_code: str) -> "UserFactory":
    user = UserFactory()
    role = Role.objects.get(code=role_code)
    UserRole.objects.create(user=user, role=role, valid_from=datetime.date(2020, 1, 1))
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_administration_can_create_an_enquiry(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    source = EnquirySourceFactory()

    response = api_client.post(
        "/api/v1/enquiries/",
        {
            "student_name": "Rohan Das",
            "date_of_birth": "2013-06-15",
            "gender": "M",
            "guardian_name": "Suman Das",
            "guardian_mobile": "9876500000",
            "source": str(source.id),
        },
    )

    assert response.status_code == 201, response.data
    assert response.data["enquiry_no"].startswith("ENQ/")
    assert "duplicate_candidates" in response.data


@pytest.mark.django_db
def test_a_role_without_enquiry_add_is_forbidden(api_client, seeded_roles):
    user = _user_with_role("medical_team")  # docs/03-rbac.md: "-" on enquiry
    api_client.force_authenticate(user)
    source = EnquirySourceFactory()

    response = api_client.post(
        "/api/v1/enquiries/",
        {
            "student_name": "Rohan Das",
            "date_of_birth": "2013-06-15",
            "gender": "M",
            "guardian_name": "Suman Das",
            "guardian_mobile": "9876500001",
            "source": str(source.id),
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_anonymous_request_is_rejected(api_client, seeded_roles):
    response = api_client.get("/api/v1/enquiries/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_list_can_be_filtered_by_status(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    EnquiryFactory(status="new")
    EnquiryFactory(status="lost")

    response = api_client.get("/api/v1/enquiries/", {"status": "lost"})

    assert response.status_code == 200
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["status"] == "lost"


@pytest.mark.django_db
def test_public_enquiry_endpoint_requires_no_auth_and_defaults_the_source(api_client):
    EnquirySourceFactory(code="website", name="Website")

    response = api_client.post(
        "/api/v1/public/enquiries/",
        {
            "student_name": "Public Visitor Kid",
            "date_of_birth": "2013-05-01",
            "gender": "M",
            "guardian_name": "Public Guardian",
            "guardian_mobile": "9876500002",
        },
    )

    assert response.status_code == 201, response.data
    assert response.data["source_code"] == "website"


@pytest.mark.django_db
def test_public_enquiry_endpoint_ignores_client_supplied_owner_and_status(api_client):
    EnquirySourceFactory(code="website", name="Website")
    staff = UserFactory()

    response = api_client.post(
        "/api/v1/public/enquiries/",
        {
            "student_name": "Sneaky Kid",
            "date_of_birth": "2013-05-01",
            "gender": "M",
            "guardian_name": "Guardian",
            "guardian_mobile": "9876500003",
            "owner": str(staff.id),
            "status": "converted",
        },
    )

    assert response.status_code == 201, response.data
    assert response.data["owner"] is None
    assert response.data["status"] == "new"


@pytest.mark.django_db
def test_follow_up_creation_requires_enquiry_add_permission(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    enquiry = EnquiryFactory(status="new")

    response = api_client.post(
        f"/api/v1/enquiries/{enquiry.id}/follow-ups/",
        {
            "contacted_on": "2026-01-10T10:00:00Z",
            "mode": "call",
            "notes": "Called, will visit next week.",
            "next_action_on": "2026-01-20",
        },
    )

    assert response.status_code == 201, response.data
    enquiry.refresh_from_db()
    assert enquiry.status == "contacted"
