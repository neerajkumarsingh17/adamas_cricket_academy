import datetime

import pytest
from rest_framework.test import APIClient

from apps.admissions.enquiry.tests.factories import EnquiryFactory
from apps.core.tests.factories import AssessmentCriterionFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory, StaffFactory

from .factories import TrialRegistrationFactory, TrialSlotFactory


def _user_with_role(role_code: str):
    user = UserFactory()
    role = Role.objects.get(code=role_code)
    UserRole.objects.create(user=user, role=role, valid_from=datetime.date(2020, 1, 1))
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_book_a_slot_from_an_enquiry(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    enquiry = EnquiryFactory()
    slot = TrialSlotFactory(capacity=5, booked_count=0)

    response = api_client.post(
        f"/api/v1/trials/slots/{slot.id}/book/", {"enquiry_id": str(enquiry.id)}
    )

    assert response.status_code == 201, response.data
    assert response.data["trial_id"].startswith("TRL/")


@pytest.mark.django_db
def test_booking_a_full_slot_returns_409(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    enquiry = EnquiryFactory()
    slot = TrialSlotFactory(capacity=1, booked_count=1)

    response = api_client.post(
        f"/api/v1/trials/slots/{slot.id}/book/", {"enquiry_id": str(enquiry.id)}
    )

    assert response.status_code == 409


@pytest.mark.django_db
def test_convert_to_trial_endpoint_matches_the_documented_enquiry_shaped_path(
    api_client, seeded_roles
):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    enquiry = EnquiryFactory()
    slot = TrialSlotFactory(capacity=5, booked_count=0)

    response = api_client.post(
        f"/api/v1/enquiries/{enquiry.id}/convert-to-trial/", {"slot_id": str(slot.id)}
    )

    assert response.status_code == 201, response.data


@pytest.mark.django_db
def test_coach_can_submit_an_assessment(api_client, seeded_roles):
    coach_user = _user_with_role("coach")
    coach_user.person = PersonFactory()
    coach_user.save()
    StaffFactory(person=coach_user.person)
    api_client.force_authenticate(coach_user)

    registration = TrialRegistrationFactory()
    criterion = AssessmentCriterionFactory()

    response = api_client.post(
        f"/api/v1/trials/registrations/{registration.id}/assess/",
        {
            "overall_remarks": "Solid all-rounder.",
            "scores": [{"criterion": str(criterion.id), "score": "7.5"}],
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["assessment"]["scores"][0]["score"] == "7.50"


@pytest.mark.django_db
def test_a_student_cannot_declare_a_trial_result(api_client, seeded_roles):
    # docs/03-rbac.md: `student` has no access at all to enquiry/trial/admission.
    student_user = _user_with_role("student")
    api_client.force_authenticate(student_user)
    registration = TrialRegistrationFactory()

    response = api_client.post(
        f"/api/v1/trials/registrations/{registration.id}/result/",
        {"outcome": "selected"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_head_coach_can_declare_a_result(api_client, seeded_roles):
    head_coach = _user_with_role("head_coach")
    api_client.force_authenticate(head_coach)
    registration = TrialRegistrationFactory()

    response = api_client.post(
        f"/api/v1/trials/registrations/{registration.id}/result/",
        {"outcome": "selected"},
    )

    assert response.status_code == 201, response.data
    assert response.data["result"]["outcome"] == "selected"
