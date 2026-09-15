import io
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.exceptions import ValidationError

from apps.admissions.document import services
from apps.admissions.document.models import Document, DocumentStatus
from apps.core.tests.factories import DocumentTypeFactory
from apps.people.tests.factories import PersonFactory


def _mock_s3(*, size_bytes: int, content: bytes):
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://s3.example.com/presigned"
    client.head_object.return_value = {"ContentLength": size_bytes}
    client.get_object.return_value = {"Body": io.BytesIO(content)}
    return client


@pytest.mark.django_db
def test_presign_returns_an_upload_url_and_a_fresh_uuid_key():
    document_type = DocumentTypeFactory()
    person = PersonFactory()

    with patch(
        "apps.admissions.document.services._s3_client",
        return_value=_mock_s3(size_bytes=0, content=b""),
    ):
        result = services.presign_upload(
            document_type=document_type,
            owner_type="person",
            owner_id=person.id,
            filename="birth_certificate.pdf",
            mime_type="application/pdf",
        )

    assert result["upload_url"] == "https://s3.example.com/presigned"
    assert result["s3_key"].startswith(f"documents/person/{person.id}/")
    assert result["s3_key"].endswith(".pdf")
    assert "birth_certificate" not in result["s3_key"]  # never the user's filename


@pytest.mark.django_db
def test_presign_rejects_a_disallowed_mime_type():
    with pytest.raises(ValidationError):
        services.presign_upload(
            document_type=DocumentTypeFactory(),
            owner_type="person",
            owner_id=PersonFactory().id,
            filename="script.exe",
            mime_type="application/x-msdownload",
        )


@pytest.mark.django_db
def test_confirm_upload_creates_a_submitted_document():
    document_type = DocumentTypeFactory()
    person = PersonFactory()
    pdf_bytes = b"%PDF-1.4 rest of a real pdf"

    with patch(
        "apps.admissions.document.services._s3_client",
        return_value=_mock_s3(size_bytes=len(pdf_bytes), content=pdf_bytes),
    ):
        document = services.confirm_upload(
            document_type=document_type,
            owner_type="person",
            owner_id=person.id,
            s3_key="documents/person/x/y.pdf",
            original_filename="birth_certificate.pdf",
            mime_type="application/pdf",
        )

    assert document.status == DocumentStatus.SUBMITTED
    assert document.owner == person
    assert document.size_bytes == len(pdf_bytes)


@pytest.mark.django_db
def test_confirm_upload_rejects_an_oversized_file():
    document_type = DocumentTypeFactory()
    person = PersonFactory()
    client = _mock_s3(size_bytes=services.MAX_DOCUMENT_SIZE_BYTES + 1, content=b"%PDF")

    with patch("apps.admissions.document.services._s3_client", return_value=client):
        with pytest.raises(ValidationError):
            services.confirm_upload(
                document_type=document_type,
                owner_type="person",
                owner_id=person.id,
                s3_key="documents/person/x/y.pdf",
                original_filename="big.pdf",
                mime_type="application/pdf",
            )

    client.delete_object.assert_called_once()
    assert Document.objects.count() == 0


@pytest.mark.django_db
def test_confirm_upload_rejects_content_that_does_not_match_the_declared_type():
    """docs/07-storage.md: "An HTML file renamed .pdf is rejected on
    content sniffing."""
    document_type = DocumentTypeFactory()
    person = PersonFactory()
    html_bytes = b"<html><body>not a pdf</body></html>"
    client = _mock_s3(size_bytes=len(html_bytes), content=html_bytes)

    with patch("apps.admissions.document.services._s3_client", return_value=client):
        with pytest.raises(ValidationError):
            services.confirm_upload(
                document_type=document_type,
                owner_type="person",
                owner_id=person.id,
                s3_key="documents/person/x/fake.pdf",
                original_filename="fake.pdf",
                mime_type="application/pdf",
            )

    client.delete_object.assert_called_once()


@pytest.mark.django_db
def test_reject_requires_a_reason_and_notifies_the_owner():
    from apps.admissions.document.tests.factories import DocumentFactory
    from apps.engagement.communication.models import NotificationLog
    from apps.engagement.communication.tests.factories import NotificationTemplateFactory
    from apps.iam.tests.factories import UserFactory

    NotificationTemplateFactory(
        code="document_rejected", body="Your {{ document_name }} was rejected: {{ reason }}"
    )
    person = PersonFactory()
    document = DocumentFactory(owner=person, status=DocumentStatus.SUBMITTED)

    with pytest.raises(ValidationError):
        services.reject(document, reason="", user=UserFactory())

    services.reject(document, reason="Illegible scan.", user=UserFactory())

    document.refresh_from_db()
    assert document.status == DocumentStatus.REJECTED
    assert NotificationLog.objects.filter(recipient=person.mobile).exists()


@pytest.mark.django_db
def test_rejecting_a_verified_document_reopens_an_admission_already_past_fee_pending():
    """Regression: a mandatory document rejected after the admission had
    already advanced to fee_pending (not just documents_verified) must
    still reopen it — this used to only fire from documents_verified.
    """
    from apps.admissions.admission.models import AdmissionStep
    from apps.admissions.admission.tests.factories import (
        AdmissionChecklistItemFactory,
        AdmissionFactory,
    )
    from apps.admissions.document.tests.factories import DocumentFactory
    from apps.iam.tests.factories import UserFactory

    admission = AdmissionFactory(step=AdmissionStep.FEE_PENDING)
    document_type = DocumentTypeFactory()
    document = DocumentFactory(
        owner=admission, document_type=document_type, status=DocumentStatus.SUBMITTED
    )
    checklist_item = AdmissionChecklistItemFactory(
        admission=admission,
        document_type=document_type,
        is_mandatory=True,
        document=document,
        status="verified",
    )

    services.reject(document, reason="Expired document.", user=UserFactory())

    admission.refresh_from_db()
    checklist_item.refresh_from_db()
    assert admission.step == AdmissionStep.DOCUMENTS_PENDING
    assert checklist_item.status == DocumentStatus.REJECTED
