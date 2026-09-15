import datetime

import pytest
from rest_framework.exceptions import ValidationError

from apps.admissions.admission import services
from apps.admissions.admission.models import AdmissionStep
from apps.admissions.document.models import DocumentStatus
from apps.admissions.document.tests.factories import DocumentFactory
from apps.core.models import DocumentRequiredStage
from apps.core.state import InvalidTransition
from apps.core.tests.factories import ConsentTypeFactory, DocumentTypeFactory, FeeHeadFactory
from apps.finance.fee.tests.factories import AdmissionFeeLineFactory
from apps.finance.payment.models import AdmissionPayment
from apps.iam.tests.factories import UserFactory

from .factories import AdmissionIntakeFactory, DirectAdmissionFactory


def _at_admission_document_type():
    return DocumentTypeFactory(
        applies_to="admission", required_stage=DocumentRequiredStage.AT_ADMISSION
    )


def _ready_for_payment_admission():
    """A DRAFT direct admission with everything _guard_ready_for_payment
    checks already satisfied: a valid intake, every mandatory consent
    granted, every mandatory fee head present.
    """
    admission = DirectAdmissionFactory()
    AdmissionIntakeFactory(admission=admission)

    mandatory_consent = ConsentTypeFactory(is_mandatory=True)
    services.record_consents(
        admission,
        decisions=[{"consent_type": mandatory_consent, "granted": True}],
        declared_by_name="Guardian Name",
    )

    mandatory_head = FeeHeadFactory(is_mandatory=True)
    AdmissionFeeLineFactory(admission=admission, fee_head=mandatory_head, amount="5000.00")

    return admission


@pytest.mark.django_db
def test_draft_to_payment_recorded_requires_a_complete_intake():
    admission = DirectAdmissionFactory()  # no intake at all
    user = UserFactory()

    with pytest.raises(InvalidTransition):
        services.record_direct_payment(
            admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
        )


@pytest.mark.django_db
def test_draft_to_payment_recorded_requires_mandatory_consents():
    admission = DirectAdmissionFactory()
    AdmissionIntakeFactory(admission=admission)
    mandatory_head = FeeHeadFactory(is_mandatory=True)
    AdmissionFeeLineFactory(admission=admission, fee_head=mandatory_head, amount="5000.00")
    ConsentTypeFactory(is_mandatory=True)  # exists, but never decided on
    user = UserFactory()

    with pytest.raises(InvalidTransition):
        services.record_direct_payment(
            admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
        )


@pytest.mark.django_db
def test_draft_to_payment_recorded_requires_mandatory_fee_heads():
    admission = DirectAdmissionFactory()
    AdmissionIntakeFactory(admission=admission)
    mandatory_consent = ConsentTypeFactory(is_mandatory=True)
    services.record_consents(
        admission,
        decisions=[{"consent_type": mandatory_consent, "granted": True}],
        declared_by_name="Guardian Name",
    )
    FeeHeadFactory(is_mandatory=True)  # exists, but no fee line covers it
    user = UserFactory()

    with pytest.raises(InvalidTransition):
        services.record_direct_payment(
            admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
        )


@pytest.mark.django_db
def test_draft_to_payment_recorded_succeeds_when_everything_is_ready():
    admission = _ready_for_payment_admission()
    user = UserFactory()

    result = services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )

    assert result.step == AdmissionStep.PAYMENT_RECORDED
    assert result.payment.receipt_no.startswith("RCP/")
    assert result.payment.recorded_by == user


@pytest.mark.django_db
def test_payment_recorded_to_payment_verified():
    admission = _ready_for_payment_admission()
    user = UserFactory()
    services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )

    result = services.verify_direct_payment(admission, approved=True, user=user)

    assert result.step == AdmissionStep.PAYMENT_VERIFIED
    assert result.payment.verified_by == user
    assert result.payment.verified_at is not None


@pytest.mark.django_db
def test_payment_rejection_returns_to_draft_and_requires_a_reason():
    admission = _ready_for_payment_admission()
    user = UserFactory()
    services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )

    with pytest.raises(ValidationError):
        services.verify_direct_payment(admission, approved=False, user=user)

    result = services.verify_direct_payment(
        admission, approved=False, user=user, reason="Receipt number does not match bank record."
    )

    assert result.step == AdmissionStep.DRAFT
    assert not AdmissionPayment.objects.filter(admission=admission).exists()


@pytest.mark.django_db
def test_payment_verified_to_documents_pending_requires_every_at_admission_type_submitted():
    doc_type = _at_admission_document_type()
    admission = _ready_for_payment_admission()
    user = UserFactory()
    services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )
    services.verify_direct_payment(admission, approved=True, user=user)

    with pytest.raises(InvalidTransition):
        services.submit_direct_documents(admission, user=user)

    DocumentFactory(owner=admission, document_type=doc_type, status=DocumentStatus.SUBMITTED)
    result = services.submit_direct_documents(admission, user=user)

    assert result.step == AdmissionStep.DOCUMENTS_PENDING


@pytest.mark.django_db
def test_documents_pending_to_ready_for_approval_when_all_verified():
    doc_type = _at_admission_document_type()
    admission = _ready_for_payment_admission()
    user = UserFactory()
    services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )
    services.verify_direct_payment(admission, approved=True, user=user)
    DocumentFactory(owner=admission, document_type=doc_type, status=DocumentStatus.VERIFIED)
    services.submit_direct_documents(admission, user=user)

    result = services.verify_direct_documents(admission, user=user)

    assert result.step == AdmissionStep.READY_FOR_APPROVAL


@pytest.mark.django_db
def test_documents_pending_to_documents_rejected_and_back_on_reupload():
    doc_type = _at_admission_document_type()
    admission = _ready_for_payment_admission()
    user = UserFactory()
    services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )
    services.verify_direct_payment(admission, approved=True, user=user)
    rejected_doc = DocumentFactory(
        owner=admission, document_type=doc_type, status=DocumentStatus.SUBMITTED
    )
    services.submit_direct_documents(admission, user=user)
    rejected_doc.status = DocumentStatus.REJECTED
    rejected_doc.save(update_fields=["status"])

    result = services.verify_direct_documents(admission, user=user)
    assert result.step == AdmissionStep.DOCUMENTS_REJECTED

    DocumentFactory(owner=admission, document_type=doc_type, status=DocumentStatus.SUBMITTED)
    result = services.submit_direct_documents(admission, user=user)
    assert result.step == AdmissionStep.DOCUMENTS_PENDING


@pytest.mark.django_db
@pytest.mark.parametrize(
    "reach_step",
    [
        AdmissionStep.DRAFT,
        AdmissionStep.PAYMENT_RECORDED,
        AdmissionStep.PAYMENT_VERIFIED,
    ],
)
def test_cancel_admission_requires_a_reason(reach_step):
    admission = _ready_for_payment_admission()
    user = UserFactory()
    if reach_step in (AdmissionStep.PAYMENT_RECORDED, AdmissionStep.PAYMENT_VERIFIED):
        services.record_direct_payment(
            admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
        )
    if reach_step == AdmissionStep.PAYMENT_VERIFIED:
        services.verify_direct_payment(admission, approved=True, user=user)

    with pytest.raises(ValidationError):
        services.cancel_admission(admission, user=user, reason="")

    result = services.cancel_admission(admission, user=user, reason="Candidate withdrew.")
    assert result.step == AdmissionStep.CANCELLED


@pytest.mark.django_db
def test_cancelling_a_direct_admission_keeps_its_payment_record():
    admission = _ready_for_payment_admission()
    user = UserFactory()
    services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )
    services.verify_direct_payment(admission, approved=True, user=user)

    services.cancel_admission(admission, user=user, reason="Candidate withdrew after paying.")

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.CANCELLED
    assert admission.payment is not None


@pytest.mark.django_db
def test_cancel_is_not_reachable_from_ready_for_approval():
    doc_type = _at_admission_document_type()
    admission = _ready_for_payment_admission()
    user = UserFactory()
    services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )
    services.verify_direct_payment(admission, approved=True, user=user)
    DocumentFactory(owner=admission, document_type=doc_type, status=DocumentStatus.VERIFIED)
    services.submit_direct_documents(admission, user=user)
    services.verify_direct_documents(admission, user=user)
    assert admission.step == AdmissionStep.READY_FOR_APPROVAL

    with pytest.raises(InvalidTransition):
        # A real reason, so this proves the *state machine's* own `frm`
        # set refuses cancellation from ready_for_approval — not merely
        # cancel_admission()'s separate "reason required" precheck.
        services.cancel_admission(admission, user=user, reason="Changed my mind.")
