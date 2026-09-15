import datetime
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.core.tests.factories import DocumentTypeFactory, ProgrammeFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory

from .factories import DocumentFactory


def _user_with_role(role_code: str):
    user = UserFactory()
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=role_code), valid_from=datetime.date(2020, 1, 1)
    )
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_presign_then_confirm_over_the_api(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    document_type = DocumentTypeFactory()
    person = PersonFactory()

    client = MagicMock()
    client.generate_presigned_url.return_value = "https://s3.example.com/presigned"
    with patch("apps.admissions.document.services._s3_client", return_value=client):
        presign_response = api_client.post(
            "/api/v1/documents/presign/",
            {
                "document_type": str(document_type.id),
                "owner_type": "person",
                "owner_id": str(person.id),
                "filename": "aadhaar.pdf",
                "mime": "application/pdf",
            },
        )
    assert presign_response.status_code == 200, presign_response.data
    s3_key = presign_response.data["s3_key"]

    pdf_bytes = b"%PDF-1.4 test"
    client.head_object.return_value = {"ContentLength": len(pdf_bytes)}
    import io

    client.get_object.return_value = {"Body": io.BytesIO(pdf_bytes)}
    with patch("apps.admissions.document.services._s3_client", return_value=client):
        confirm_response = api_client.post(
            "/api/v1/documents/confirm/",
            {
                "document_type": str(document_type.id),
                "owner_type": "person",
                "owner_id": str(person.id),
                "s3_key": s3_key,
                "filename": "aadhaar.pdf",
                "mime": "application/pdf",
            },
        )

    assert confirm_response.status_code == 201, confirm_response.data
    assert confirm_response.data["status"] == "submitted"


@pytest.mark.django_db
def test_a_parent_can_only_see_their_own_documents(api_client, seeded_roles):
    parent_user = _user_with_role("parent")
    parent_user.person = PersonFactory()
    parent_user.save()
    own_document = DocumentFactory(owner=parent_user.person)
    someone_elses_document = DocumentFactory(owner=PersonFactory())

    api_client.force_authenticate(parent_user)

    response = api_client.get("/api/v1/documents/")
    ids = {row["id"] for row in response.data["results"]}
    assert str(own_document.id) in ids
    assert str(someone_elses_document.id) not in ids

    other_detail = api_client.get(f"/api/v1/documents/{someone_elses_document.id}/download/")
    assert other_detail.status_code == 404


@pytest.mark.django_db
def test_a_parent_cannot_presign_a_document_for_someone_elses_child(api_client, seeded_roles):
    parent_user = _user_with_role("parent")
    parent_user.person = PersonFactory()
    parent_user.save()
    api_client.force_authenticate(parent_user)
    document_type = DocumentTypeFactory()
    someone_elses_child = PersonFactory()

    response = api_client.post(
        "/api/v1/documents/presign/",
        {
            "document_type": str(document_type.id),
            "owner_type": "person",
            "owner_id": str(someone_elses_child.id),
            "filename": "aadhaar.pdf",
            "mime": "application/pdf",
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_a_candidate_can_upload_to_their_own_in_progress_admission(api_client, seeded_roles):
    """Direct-admission step 2.1: once Administration enables portal
    access, the candidate (role=student, no Student row yet) uploads to
    their own Admission's checklist the same way a parent already
    uploads for a child.
    """
    from apps.admissions.admission import services as admission_services
    from apps.admissions.admission.models import Admission, AdmissionSource, AdmissionStep

    # Created before create_checklist() — it queries DocumentType at call
    # time, so the checklist would come back empty (and the fee_cleared ->
    # documents_pending guard's `checklist_items.exists()` check would
    # fail) if this ran after.
    document_type = DocumentTypeFactory(applies_to="admission")

    person = PersonFactory()
    admission = Admission.objects.create(
        application_no="ADM/2627/TEST01",
        person=person,
        programme=ProgrammeFactory(),
        step=AdmissionStep.FEE_CLEARED,
        fee_payment_status="paid",
        source=AdmissionSource.DIRECT,
        direct_admission_reason="Reputation admission.",
    )
    admission_services.create_checklist(admission)
    admin_user = _user_with_role("administration")
    admission_services.enable_portal_access(admission, user=admin_user)

    from apps.iam.models import User

    candidate_user = User.objects.get(person=person)
    api_client.force_authenticate(candidate_user)

    client = MagicMock()
    client.generate_presigned_url.return_value = "https://s3.example.com/presigned"
    with patch("apps.admissions.document.services._s3_client", return_value=client):
        response = api_client.post(
            "/api/v1/documents/presign/",
            {
                "document_type": str(document_type.id),
                "owner_type": "admission",
                "owner_id": str(admission.id),
                "filename": "birth_certificate.pdf",
                "mime": "application/pdf",
            },
        )

    assert response.status_code == 200, response.data


@pytest.mark.django_db
def test_a_candidate_cannot_upload_to_someone_elses_admission(api_client, seeded_roles):
    from apps.admissions.admission import services as admission_services
    from apps.admissions.admission.models import Admission, AdmissionSource, AdmissionStep
    from apps.iam.models import User

    document_type = DocumentTypeFactory(applies_to="admission")

    person = PersonFactory()
    admission = Admission.objects.create(
        application_no="ADM/2627/TEST02",
        person=person,
        programme=ProgrammeFactory(),
        step=AdmissionStep.FEE_CLEARED,
        fee_payment_status="paid",
        source=AdmissionSource.DIRECT,
        direct_admission_reason="Reputation admission.",
    )
    admission_services.create_checklist(admission)
    admin_user = _user_with_role("administration")
    admission_services.enable_portal_access(admission, user=admin_user)
    candidate_user = User.objects.get(person=person)
    api_client.force_authenticate(candidate_user)

    someone_elses_admission = Admission.objects.create(
        application_no="ADM/2627/TEST03",
        person=PersonFactory(),
        programme=ProgrammeFactory(),
        step=AdmissionStep.FEE_CLEARED,
        fee_payment_status="paid",
        source=AdmissionSource.DIRECT,
        direct_admission_reason="Reputation admission.",
    )

    response = api_client.post(
        "/api/v1/documents/presign/",
        {
            "document_type": str(document_type.id),
            "owner_type": "admission",
            "owner_id": str(someone_elses_admission.id),
            "filename": "birth_certificate.pdf",
            "mime": "application/pdf",
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_reject_requires_a_reason_over_the_api(api_client, seeded_roles):
    user = _user_with_role("administration")
    api_client.force_authenticate(user)
    document = DocumentFactory(status="submitted")

    response = api_client.patch(f"/api/v1/documents/{document.id}/reject/", {})

    assert response.status_code == 400
