import pytest

from apps.admissions.idcard import services
from apps.admissions.idcard.models import IDCardStatus
from apps.admissions.student.tests.factories import StudentFactory
from apps.iam.tests.factories import UserFactory


@pytest.mark.django_db
def test_issue_card_uses_the_documented_numbering_format():
    student = StudentFactory(student_code="ACA/2627/0001")
    card = services.issue_card(student, issued_by=UserFactory())
    assert card.card_no == "ACA/2627/0001-1"
    assert card.status == IDCardStatus.ACTIVE


@pytest.mark.django_db
def test_reissuing_supersedes_the_previous_card():
    student = StudentFactory(student_code="ACA/2627/0002")
    first = services.issue_card(student, issued_by=UserFactory())

    second = services.issue_card(student, issued_by=UserFactory())

    first.refresh_from_db()
    assert first.status == IDCardStatus.REPLACED
    assert second.replaces_id == first.id
    assert second.card_no == "ACA/2627/0002-2"


@pytest.mark.django_db
def test_qr_payload_encodes_card_no_not_the_raw_student_id():
    student = StudentFactory()
    card = services.issue_card(student, issued_by=UserFactory())
    assert str(student.id) not in card.qr_payload


@pytest.mark.django_db
def test_resolve_qr_unauthorized_returns_validity_only():
    student = StudentFactory()
    card = services.issue_card(student, issued_by=UserFactory())

    result = services.resolve_qr(card.qr_payload, authorized=False)

    assert result == {"valid": True}


@pytest.mark.django_db
def test_resolve_qr_authorized_returns_student_details():
    student = StudentFactory()
    card = services.issue_card(student, issued_by=UserFactory())

    result = services.resolve_qr(card.qr_payload, authorized=True)

    assert result["valid"] is True
    assert result["student_code"] == student.student_code


@pytest.mark.django_db
def test_resolve_qr_rejects_a_tampered_token():
    result = services.resolve_qr("not-a-real-token", authorized=True)
    assert result == {"valid": False}


@pytest.mark.django_db
def test_resolve_qr_reflects_a_replaced_card_as_invalid():
    student = StudentFactory()
    old_card = services.issue_card(student, issued_by=UserFactory())
    services.issue_card(student, issued_by=UserFactory())  # supersedes old_card

    result = services.resolve_qr(old_card.qr_payload, authorized=False)

    assert result == {"valid": False}
