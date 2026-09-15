import datetime

import pytest

from apps.admissions.admission import services as admission_services
from apps.admissions.admission.models import AdmissionStep
from apps.admissions.admission.tests.factories import AdmissionIntakeFactory, DirectAdmissionFactory
from apps.admissions.document.models import DocumentStatus
from apps.admissions.document.tests.factories import DocumentFactory
from apps.admissions.student import services
from apps.core.models import DocumentRequiredStage
from apps.core.tests.factories import ConsentTypeFactory, DocumentTypeFactory, FeeHeadFactory
from apps.finance.fee.tests.factories import AdmissionFeeLineFactory
from apps.iam.tests.factories import UserFactory
from apps.people.models import Relationship
from apps.people.tests.factories import PersonFactory


def _ready_for_approval_admission(*, full_name: str, date_of_birth, guardian_mobile: str):
    admission = DirectAdmissionFactory()
    AdmissionIntakeFactory(
        admission=admission,
        full_name=full_name,
        date_of_birth=date_of_birth,
        guardian_mobile=guardian_mobile,
        guardian_relationship=Relationship.FATHER,
    )
    mandatory_consent = ConsentTypeFactory(is_mandatory=True)
    admission_services.record_consents(
        admission,
        decisions=[{"consent_type": mandatory_consent, "granted": True}],
        declared_by_name="Guardian Name",
    )
    mandatory_head = FeeHeadFactory(is_mandatory=True)
    AdmissionFeeLineFactory(admission=admission, fee_head=mandatory_head, amount="5000.00")
    doc_type = DocumentTypeFactory(
        applies_to="admission", required_stage=DocumentRequiredStage.AT_ADMISSION
    )

    user = UserFactory()
    admission_services.record_direct_payment(
        admission, payment_mode="upi", payment_date=datetime.date.today(), user=user
    )
    admission_services.verify_direct_payment(admission, approved=True, user=user)
    DocumentFactory(owner=admission, document_type=doc_type, status=DocumentStatus.VERIFIED)
    admission_services.submit_direct_documents(admission, user=user)
    admission_services.verify_direct_documents(admission, user=user)
    assert admission.step == AdmissionStep.READY_FOR_APPROVAL
    return admission


@pytest.mark.django_db
def test_approving_a_direct_admission_creates_person_and_student():
    admission = _ready_for_approval_admission(
        full_name="Rohan Das",
        date_of_birth=datetime.date(2013, 8, 19),
        guardian_mobile="+919800000001",
    )
    # Matches AdmissionIntakeFactory's guardian_name/guardian_date_of_birth
    # defaults exactly — _link_direct_admission_guardian's dedupe key needs
    # name+DOB+mobile all matching to reuse this Person rather than create
    # a second one.
    guardian_person = PersonFactory(
        first_name="Guardian",
        last_name="Name",
        date_of_birth=datetime.date(1985, 3, 10),
        mobile="+919800000001",
    )
    approver = UserFactory()

    student = services.approve_admission(admission, user=approver)

    assert student.person.first_name == "Rohan"
    assert student.person.last_name == "Das"
    assert student.programme is None  # assigned later, by the Head Coach
    assert student.status == "active"
    assert student.guardians.filter(guardian__person=guardian_person, is_primary=True).exists()


@pytest.mark.django_db
def test_approving_a_direct_admission_for_a_returning_person_reuses_the_person():
    """The most important test in this feature: a candidate whose Person
    already exists (matching name, DOB, guardian mobile from a prior
    enrolment) must reuse that Person, never create a second one.
    """
    existing_person = PersonFactory(
        first_name="Rohan",
        last_name="Das",
        date_of_birth=datetime.date(2013, 8, 19),
        mobile="+919800000001",
    )
    # A distinct Person record for the guardian, matching AdmissionIntake-
    # Factory's guardian_name/guardian_date_of_birth defaults exactly (the
    # dedupe key needs all three of name+DOB+mobile) — otherwise
    # _link_direct_admission_guardian would create a second Person instead
    # of reusing this one, and the count assertion below would fail.
    PersonFactory(
        first_name="Guardian",
        last_name="Name",
        date_of_birth=datetime.date(1985, 3, 10),
        mobile="+919800000001",
    )
    from apps.people.models import Person

    persons_before = Person.objects.count()

    admission = _ready_for_approval_admission(
        full_name="Rohan Das",
        date_of_birth=datetime.date(2013, 8, 19),
        guardian_mobile="+919800000001",
    )
    approver = UserFactory()

    student = services.approve_admission(admission, user=approver)

    assert student.person_id == existing_person.id
    assert Person.objects.count() == persons_before


@pytest.mark.django_db
def test_approval_creates_a_new_guardian_person_for_a_first_time_family():
    """The primary scenario the fee-first wizard exists for: a walk-in
    family with no prior record at all. AdmissionIntake now collects
    guardian_date_of_birth/guardian_gender precisely so this doesn't
    dead-end — see _link_direct_admission_guardian's docstring.
    """
    admission = _ready_for_approval_admission(
        full_name="New Candidate",
        date_of_birth=datetime.date(2014, 1, 1),
        guardian_mobile="+919800009999",
    )
    approver = UserFactory()
    # No Person exists with this guardian's mobile at all.

    student = services.approve_admission(admission, user=approver)

    guardian_link = student.guardians.get(is_primary=True)
    guardian_person = guardian_link.guardian.person
    assert guardian_person.first_name == "Guardian"
    assert guardian_person.last_name == "Name"
    assert guardian_person.date_of_birth == datetime.date(1985, 3, 10)
    assert guardian_person.gender == "F"
    assert guardian_person.mobile == "+919800009999"
