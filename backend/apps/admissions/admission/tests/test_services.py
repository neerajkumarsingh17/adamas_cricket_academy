import datetime

import pytest
from rest_framework.exceptions import ValidationError

from apps.admissions.admission import services
from apps.admissions.admission.models import AdmissionSource, AdmissionStep, PaymentStatus
from apps.admissions.admission.state import AdmissionStateMachine
from apps.admissions.trial.tests.factories import TrialRegistrationFactory, TrialResultFactory
from apps.core.models import ApprovalRule
from apps.core.services import approvals
from apps.core.state import InvalidTransition
from apps.core.tests.factories import DocumentTypeFactory, ProgrammeFactory
from apps.iam.models import Role
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory


@pytest.fixture
def selected_registration():
    registration = TrialRegistrationFactory(person=PersonFactory())
    TrialResultFactory(registration=registration, outcome="selected")
    return registration


@pytest.mark.django_db
def test_open_admission_requires_a_selected_result():
    registration = TrialRegistrationFactory()  # no TrialResult at all
    with pytest.raises(ValidationError):
        services.open_admission(trial_registration=registration, programme=ProgrammeFactory())


@pytest.mark.django_db
def test_open_admission_creates_a_checklist_from_document_types(
    selected_registration, seeded_roles
):
    DocumentTypeFactory(code="birth_certificate", is_mandatory_default=True, applies_to="admission")
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")

    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )

    assert admission.step == AdmissionStep.DRAFT
    items = list(admission.checklist_items.all())
    assert len(items) == 2
    assert any(i.is_mandatory for i in items)
    assert any(not i.is_mandatory for i in items)
    admission.enquiry.refresh_from_db()
    assert admission.enquiry.status == "converted"


@pytest.mark.django_db
def test_cannot_advance_past_documents_pending_with_unverified_mandatory_document(
    selected_registration, seeded_roles
):
    DocumentTypeFactory(code="birth_certificate", is_mandatory_default=True, applies_to="admission")
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_PENDING, user=UserFactory())

    with pytest.raises(InvalidTransition):
        services.advance(admission, to_step=AdmissionStep.DOCUMENTS_VERIFIED, user=UserFactory())


@pytest.mark.django_db
def test_full_chain_draft_to_fee_cleared(selected_registration, seeded_roles):
    # A non-mandatory type only, so the checklist is non-empty (satisfying
    # the draft -> documents_pending guard) while the documents_pending ->
    # documents_verified guard passes vacuously (no *mandatory* items).
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    user = UserFactory()

    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_PENDING, user=user)
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_VERIFIED, user=user)
    services.advance(admission, to_step=AdmissionStep.FEE_PENDING, user=user)

    with pytest.raises(InvalidTransition):
        services.advance(admission, to_step=AdmissionStep.FEE_CLEARED, user=user)

    # record_payment auto-advances fee_pending -> fee_cleared itself once
    # the fee is paid/waived (docs/04-state-machines.md section 1 names
    # Accounts as permitted on that transition, not only on recording the
    # payment — see services.record_payment's docstring).
    services.record_payment(
        admission, reference="UPI-REF-001", amount="5000.00", payment_method="upi", user=user
    )

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.FEE_CLEARED


@pytest.mark.django_db
def test_advance_rejects_skipping_a_step(selected_registration, seeded_roles):
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    with pytest.raises(InvalidTransition):
        services.advance(admission, to_step=AdmissionStep.FEE_CLEARED, user=UserFactory())


@pytest.mark.django_db
def test_reject_requires_a_reason(selected_registration, seeded_roles):
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    user = UserFactory()
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_PENDING, user=user)
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_VERIFIED, user=user)
    services.advance(admission, to_step=AdmissionStep.FEE_PENDING, user=user)
    services.record_payment(
        admission, reference="REF", amount="3500.00", payment_method="cash", user=user
    )

    with pytest.raises(ValidationError):
        services.reject_admission(admission, user=user, reason="")

    services.reject_admission(admission, user=user, reason="Ineligible age group.")
    admission.refresh_from_db()
    assert admission.step == AdmissionStep.REJECTED


@pytest.mark.django_db
def test_approved_guard_requires_a_decided_approval_request(selected_registration, seeded_roles):
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    # This test is about the `approved` guard specifically, not the full
    # step sequence (covered by test_full_chain_draft_to_fee_cleared) — set
    # the fields directly to reach `fee_cleared`, the state `approved` can
    # actually transition from. `_guard_approved` re-checks the fee guard
    # too (services.record_payment's docstring), so fee_payment_status has
    # to actually say paid/waived, not just the step saying cleared.
    admission.step = AdmissionStep.FEE_CLEARED
    admission.fee_payment_status = PaymentStatus.PAID
    admission.save(update_fields=["step", "fee_payment_status"])

    machine = AdmissionStateMachine(admission)
    assert not machine.can_apply(AdmissionStep.APPROVED)

    ApprovalRule.objects.update_or_create(
        module="admission",
        action="approve",
        defaults={"required_role": Role.objects.get(code="academy_head")},
    )
    requester = UserFactory()
    approval_request = approvals.request(admission, "admission", "approve", requester)
    approver = UserFactory()
    from apps.iam.models import UserRole

    UserRole.objects.create(
        user=approver,
        role=Role.objects.get(code="academy_head"),
        valid_from=datetime.date(2020, 1, 1),
    )
    approvals.decide(approval_request, approver, approve=True)

    machine = AdmissionStateMachine(admission)
    assert machine.can_apply(AdmissionStep.APPROVED)


def _direct_admission_kwargs(**overrides):
    kwargs = dict(
        first_name="Rohan",
        last_name="Verma",
        date_of_birth=datetime.date(2012, 5, 1),
        gender="M",
        mobile="9876500001",
        email="",
        address_line1="",
        city="",
        state="",
        pincode="",
        programme=ProgrammeFactory(),
        reason="Reputation admission — state-level player.",
        requested_by=UserFactory(),
    )
    kwargs.update(overrides)
    return kwargs


@pytest.mark.django_db
def test_open_direct_admission_skips_the_waiver_gate(seeded_roles):
    # Administration opens these directly — no Academy Head sign-off gate
    # at intake any more (product decision: the direct-admission feature).
    admission = services.open_direct_admission(**_direct_admission_kwargs())

    assert admission.step == AdmissionStep.DRAFT
    assert admission.source == AdmissionSource.DIRECT
    assert admission.person.first_name == "Rohan"

    # Fee first (step 2.1) is the *only* forward path for a direct
    # admission — the documents-first order stays trial-based only.
    machine = AdmissionStateMachine(admission)
    assert machine.can_apply(AdmissionStep.FEE_PENDING)
    assert not machine.can_apply(AdmissionStep.DOCUMENTS_PENDING)


@pytest.mark.django_db
def test_open_direct_admission_reuses_an_exact_person_match(seeded_roles):
    # CLAUDE.md rule 1: re-admitting/re-entering the same person reuses
    # their Person rather than creating a second one.
    existing = PersonFactory(
        first_name="Asha",
        last_name="Rao",
        date_of_birth=datetime.date(2011, 3, 4),
        mobile="+919876500002",
    )

    admission = services.open_direct_admission(
        **_direct_admission_kwargs(
            first_name="Asha", last_name="Rao", date_of_birth=datetime.date(2011, 3, 4),
            gender="F", mobile="9876500002",
        )
    )

    assert admission.person_id == existing.id


@pytest.mark.django_db
def test_direct_admission_reaching_fee_cleared_does_not_need_a_decided_approval(seeded_roles):
    from apps.core.models import ApprovalRequest

    # Mandatory, unlike this file's other direct-admission tests — needed
    # so the documents guard doesn't pass vacuously below, which would
    # defeat the point of this assertion.
    DocumentTypeFactory(code="birth_certificate", is_mandatory_default=True, applies_to="admission")
    admission = services.open_direct_admission(**_direct_admission_kwargs())
    user = UserFactory()
    services.advance(admission, to_step=AdmissionStep.FEE_PENDING, user=user)
    services.record_payment(
        admission, reference="UPI-REF-DIRECT", amount="5000.00", payment_method="upi", user=user
    )

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.FEE_CLEARED
    # Unlike test_record_payment_reaching_fee_cleared_raises_the_approval_
    # request (the trial-based path), nothing gets raised here — there is
    # no Academy Head sign-off for a direct admission to wait on.
    assert not ApprovalRequest.objects.filter(
        rule__module="admission", rule__action="approve", object_id=admission.id
    ).exists()

    # Fee's in, but the mandatory document hasn't been verified yet — this
    # path (step 2.1) collects documents *after* fee, so approval must
    # still refuse until that happens.
    machine = AdmissionStateMachine(admission)
    assert not machine.can_apply(AdmissionStep.APPROVED)


@pytest.mark.django_db
def test_direct_admission_can_go_fee_first_then_enable_portal_for_documents(seeded_roles):
    """Step 2.1: a direct admission can skip straight from draft to
    fee_pending, and once fee is cleared, `enable_portal_access` moves it
    on to `documents_pending` and provisions the candidate's own login —
    the order docs/04-state-machines.md's original documents-before-fee
    chain never allowed.
    """
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    admission = services.open_direct_admission(**_direct_admission_kwargs(mobile="9876500004"))
    user = UserFactory()

    services.advance(admission, to_step=AdmissionStep.FEE_PENDING, user=user)
    services.record_payment(
        admission, reference="UPI-REF-2-1", amount="5000.00", payment_method="upi", user=user
    )
    admission.refresh_from_db()
    assert admission.step == AdmissionStep.FEE_CLEARED

    from apps.iam.models import User

    assert not User.objects.filter(person_id=admission.person_id).exists()

    services.enable_portal_access(admission, user=user)

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.DOCUMENTS_PENDING
    assert User.objects.filter(person_id=admission.person_id, is_active=True).exists()

    # Administration marks the (self-uploaded) documents verified, then
    # this direct admission reaches `approved` from `documents_verified`
    # directly — there's no fee_cleared to come back through a second time.
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_VERIFIED, user=user)
    machine = AdmissionStateMachine(admission)
    assert machine.can_apply(AdmissionStep.APPROVED)


@pytest.mark.django_db
def test_trial_based_reversal_from_fee_cleared_still_requires_a_reason(
    selected_registration, seeded_roles
):
    """Regression check: splitting the fee_cleared -> documents_pending
    transition in two (one per path) must not loosen the trial-based
    reversal's `reason_required` behaviour.
    """
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    user = UserFactory()
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_PENDING, user=user)
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_VERIFIED, user=user)
    services.advance(admission, to_step=AdmissionStep.FEE_PENDING, user=user)
    services.record_payment(
        admission, reference="UPI-REF-REV", amount="5000.00", payment_method="upi", user=user
    )
    admission.refresh_from_db()
    assert admission.step == AdmissionStep.FEE_CLEARED

    with pytest.raises(ValidationError):
        services.advance(admission, to_step=AdmissionStep.DOCUMENTS_PENDING, user=user)

    services.advance(
        admission,
        to_step=AdmissionStep.DOCUMENTS_PENDING,
        user=user,
        reason="A verified document expired.",
    )
    admission.refresh_from_db()
    assert admission.step == AdmissionStep.DOCUMENTS_PENDING


@pytest.mark.django_db
def test_open_direct_admission_requires_a_reason(seeded_roles):
    with pytest.raises(ValidationError):
        services.open_direct_admission(**_direct_admission_kwargs(reason=""))


@pytest.mark.django_db
def test_record_payment_requires_a_method_alongside_a_reference(
    selected_registration, seeded_roles
):
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    with pytest.raises(ValidationError):
        services.record_payment(admission, reference="UPI-REF-002")


@pytest.mark.django_db
def test_mark_unpaid_reverts_fee_cleared_back_to_fee_pending(selected_registration, seeded_roles):
    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    user = UserFactory()
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_PENDING, user=user)
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_VERIFIED, user=user)
    services.advance(admission, to_step=AdmissionStep.FEE_PENDING, user=user)
    services.record_payment(
        admission, reference="UPI-REF-003", amount="5000.00", payment_method="upi", user=user
    )

    services.record_payment(admission, mark_unpaid=True, user=user)

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.FEE_PENDING
    assert admission.fee_payment_status == "pending"
    assert admission.fee_payment_reference == ""

    # And the approval guard now correctly refuses even if a decision was
    # already made while the fee still looked cleared.
    machine = AdmissionStateMachine(admission)
    assert not machine.can_apply(AdmissionStep.APPROVED)


@pytest.mark.django_db
def test_approved_guard_refuses_if_a_mandatory_document_becomes_unverified(
    selected_registration, seeded_roles
):
    """Belt-and-suspenders: even if the step never got reverted back to
    documents_pending for some reason, approval itself must still refuse
    once a mandatory document is no longer verified.
    """
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    DocumentTypeFactory(code="mandatory_doc", is_mandatory_default=True, applies_to="admission")
    services.create_checklist(admission)
    item = admission.checklist_items.get(document_type__code="mandatory_doc")
    item.status = "verified"
    item.save(update_fields=["status"])

    admission.step = AdmissionStep.FEE_CLEARED
    admission.fee_payment_status = PaymentStatus.PAID
    admission.save(update_fields=["step", "fee_payment_status"])

    ApprovalRule.objects.update_or_create(
        module="admission",
        action="approve",
        defaults={"required_role": Role.objects.get(code="academy_head")},
    )
    approval_request = approvals.request(admission, "admission", "approve", UserFactory())
    approver = UserFactory()
    from apps.iam.models import UserRole

    UserRole.objects.create(
        user=approver,
        role=Role.objects.get(code="academy_head"),
        valid_from=datetime.date(2020, 1, 1),
    )
    approvals.decide(approval_request, approver, approve=True)

    machine = AdmissionStateMachine(admission)
    assert machine.can_apply(AdmissionStep.APPROVED)  # sanity check: guard passes while verified

    item.status = "rejected"
    item.save(update_fields=["status"])

    machine = AdmissionStateMachine(admission)
    assert not machine.can_apply(AdmissionStep.APPROVED)


@pytest.mark.django_db
def test_record_payment_reaching_fee_cleared_raises_the_approval_request(
    selected_registration, seeded_roles
):
    """Regression: reaching fee_cleared via advance() always raised the
    (admission, "approve") request as a side effect of that specific
    transition — record_payment's own fee_pending -> fee_cleared
    auto-advance (added so Accounts doesn't need advance()'s edit-gated
    endpoint) initially didn't, leaving an admission at fee_cleared with no
    way for Academy Head to ever decide anything, and /approve permanently
    409ing.
    """
    from apps.core.models import ApprovalRequest

    DocumentTypeFactory(code="school_id", is_mandatory_default=False, applies_to="admission")
    ApprovalRule.objects.update_or_create(
        module="admission",
        action="approve",
        defaults={"required_role": Role.objects.get(code="academy_head")},
    )
    admission = services.open_admission(
        trial_registration=selected_registration, programme=ProgrammeFactory()
    )
    user = UserFactory()
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_PENDING, user=user)
    services.advance(admission, to_step=AdmissionStep.DOCUMENTS_VERIFIED, user=user)
    services.advance(admission, to_step=AdmissionStep.FEE_PENDING, user=user)

    services.record_payment(
        admission, reference="UPI-REF-777", amount="1000.00", payment_method="upi", user=user
    )

    admission.refresh_from_db()
    assert admission.step == AdmissionStep.FEE_CLEARED
    assert ApprovalRequest.objects.filter(
        rule__module="admission", rule__action="approve"
    ).exists()
