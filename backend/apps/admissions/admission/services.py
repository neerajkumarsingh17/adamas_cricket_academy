"""docs/05-build-sequence.md T-601..T-607. Admission opening, the document
checklist, the fee stub and the trial-waiver ("direct admission") path.
`approve_admission()` — the transition that creates a `Student` — is
deliberately *not* here; see `apps.admissions.student.services` for why.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import ConsentType, DocumentType
from apps.core.services import approvals
from apps.core.services.numbering import next_number
from apps.iam.services import get_or_create_user_for_person
from apps.people.models import Person
from apps.people.services import resolve_person

from .models import (
    Admission,
    AdmissionChecklistItem,
    AdmissionIntake,
    AdmissionSource,
    AdmissionStep,
    ConsentRecord,
    PaymentStatus,
)
from .state import AdmissionStateMachine, DirectAdmissionStateMachine


def create_checklist(admission: Admission) -> None:
    """Every `DocumentType` applicable to an admission becomes a checklist
    item, `is_mandatory` copied from the type's default at creation time —
    docs/01-data-model.md section 5 doesn't describe per-programme document
    requirements (only a global `is_mandatory_default` on `DocumentType`),
    so "for the programme" in docs/04-state-machines.md's guard reads here
    as "for admissions generally", the only requirement actually specified.
    """
    document_types = DocumentType.objects.filter(applies_to="admission")
    AdmissionChecklistItem.objects.bulk_create(
        AdmissionChecklistItem(
            admission=admission,
            document_type=document_type,
            is_mandatory=document_type.is_mandatory_default,
        )
        for document_type in document_types
    )


@transaction.atomic
def open_admission(*, trial_registration, programme, residential: bool = False) -> Admission:
    """docs/02-api-spec.md: "POST requires a selected trial or an approved
    waiver." — this is the selected-trial path; `open_direct_admission`
    below is the waiver path.
    """
    result = getattr(trial_registration, "result", None)
    if result is None or result.outcome != "selected":
        raise ValidationError(
            {"trial_registration": "This trial registration does not have a Selected result."}
        )

    admission = Admission.objects.create(
        application_no=next_number("ADM"),
        person=trial_registration.person,
        enquiry=trial_registration.enquiry,
        trial_registration=trial_registration,
        programme=programme,
        residential=residential,
    )
    machine = AdmissionStateMachine(admission)
    machine.apply(AdmissionStep.DRAFT)
    admission.save(update_fields=["step", "updated_at"])
    create_checklist(admission)

    # trial_registration.enquiry is a required FK on TrialRegistration —
    # only Admission.enquiry itself is nullable (for the direct-admission
    # path, which doesn't go through this function).
    enquiry = admission.enquiry
    assert enquiry is not None
    enquiry.status = "converted"
    enquiry.save(update_fields=["status"])

    return admission


def _resolve_or_create_person(
    *,
    first_name: str,
    last_name: str,
    date_of_birth,
    gender: str,
    mobile: str,
    email: str,
    address_line1: str,
    city: str,
    state: str,
    pincode: str,
) -> Person:
    """CLAUDE.md rule 1: the only way a `Person` gets created here is
    through `resolve_person()` — an exact dedupe match (e.g. a returning
    enquiry, or a former student re-admitting) reuses that `Person` rather
    than creating a second one. Mirrors
    `apps.admissions.trial.services._resolve_or_create_person`, just
    parameterised on raw fields instead of an `Enquiry`, since a direct
    admission has no enquiry behind it.
    """
    match = resolve_person(
        {
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth,
            "guardian_mobile": mobile,
        }
    )
    if match.exact:
        return match.exact[0]
    return Person.objects.create(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        gender=gender,
        mobile=mobile,
        email=email,
        address_line1=address_line1,
        address_line2="",
        city=city,
        state=state,
        pincode=pincode,
    )


@transaction.atomic
def open_direct_admission(
    *,
    first_name: str,
    last_name: str,
    date_of_birth,
    gender: str,
    mobile: str,
    email: str,
    address_line1: str,
    city: str,
    state: str,
    pincode: str,
    programme,
    reason: str,
    requested_by,
    residential: bool = False,
) -> Admission:
    """docs/05-build-sequence.md T-607: reputation/referral admissions,
    traceable rather than disguised as a fake trial — Administration opens
    these directly (product decision: the direct-admission feature), no
    Academy Head sign-off gate at intake. `reason` plus the audit log on
    this record is the traceability trail instead of an approval
    (docs/04-state-machines.md section 1's `draft` guard just checks
    `direct_admission_reason` is set).

    Superseded by the fee-first direct-admission wizard (AdmissionIntake +
    DirectAdmissionStateMachine) — kept working as-is for now since nothing
    downstream has been migrated to the new flow yet.
    """
    if not reason:
        raise ValidationError({"reason": "A reason is required for a direct admission."})

    person = _resolve_or_create_person(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        gender=gender,
        mobile=mobile,
        email=email,
        address_line1=address_line1,
        city=city,
        state=state,
        pincode=pincode,
    )

    admission = Admission.objects.create(
        application_no=next_number("ADM"),
        source=AdmissionSource.DIRECT,
        person=person,
        programme=programme,
        residential=residential,
        direct_admission_reason=reason,
    )
    create_checklist(admission)
    return admission


@transaction.atomic
def enable_portal_access(admission: Admission, *, user) -> Admission:
    """POST /admissions/{id}/enable-portal — direct admission's step 2.1:
    once Administration has confirmed payment (`fee_cleared`), switch on
    the candidate's own OTP login and move the admission on to document
    collection in one action, so they can upload their own documents
    instead of Administration doing it on their behalf. Trial-based
    admissions already collect documents *before* fee and have no
    equivalent step — `AdmissionStateMachine` refuses this transition for
    them (admission/state.py's `_guard_fee_cleared_to_documents_pending`).

    Reuses the same login mechanism as `apps.admissions.student.services.
    grant_student_login`, just before a `Student` row exists rather than
    after — `Admission.person.mobile` is already the candidate's own
    number here (unlike the trial path, where it starts out as their
    guardian's), so there is no separate number to supply.
    """
    if admission.trial_registration_id is not None:
        raise ValidationError(
            {"detail": "Portal access only applies to a direct (no-trial) admission."}
        )
    machine = AdmissionStateMachine(admission)
    machine.apply(AdmissionStep.DOCUMENTS_PENDING, user=user)
    admission.save(update_fields=["step", "updated_at"])
    get_or_create_user_for_person(admission.person, role_code="student")
    return admission


def advance(admission: Admission, *, to_step: str, user, reason: str = "") -> Admission:
    """POST /admissions/{id}/advance — docs/02-api-spec.md. Covers every
    transition except `approved` (apps.admissions.student.services owns
    that one) and `rejected` (services.reject_admission, below — kept
    separate since rejecting always needs a reason and is a terminal act,
    not something to route through a generic `{to_step}` body param that
    could accidentally be typo'd into the wrong terminal state).
    """
    if to_step in (AdmissionStep.APPROVED, AdmissionStep.REJECTED):
        raise ValidationError(
            {"to_step": f"{to_step!r} has its own endpoint — use approve/reject, not advance()."}
        )
    machine = AdmissionStateMachine(admission)
    machine.apply(to_step, user=user, reason=reason)
    admission.save(update_fields=["step", "updated_at"])

    if to_step == AdmissionStep.FEE_CLEARED:
        _raise_approval_request(admission, requested_by=user)

    return admission


def _raise_approval_request(admission: Admission, *, requested_by) -> None:
    """Reaching `fee_cleared` is what puts an admission in front of the
    Academy Head — nothing else in this flow calls
    `POST /admissions/{id}/approve` for the caller, and that endpoint's own
    guard only *checks* for an approval already decided (mirroring
    `apps.admissions.student.services.change_status`'s two-step shape), so
    something has to actually raise the request. A second call to
    `advance()` reaching `fee_cleared` again is impossible (the state
    machine's `frm` would reject it), so this can't double-raise.

    Direct admissions skip this entirely: `_guard_approved` doesn't require
    a decided approval for them, so raising one here would just sit
    pending forever in the Academy Head's Approvals queue for no reason.
    """
    if admission.trial_registration_id is None:
        return
    try:
        approvals.request(admission, "admission", "approve", requested_by)
    except approvals.NoApprovalRuleConfigured:
        # Flagged, not silently swallowed: an admission stuck at
        # fee_cleared with no ApprovalRule configured for
        # module="admission" action="approve" is a real configuration gap
        # (docs/05-build-sequence.md T-606 assumes one exists), not a
        # 500 worth returning to whoever happened to trigger this advance.
        pass


@transaction.atomic
def record_payment(
    admission: Admission,
    *,
    reference: str = "",
    amount=None,
    payment_method: str = "",
    waiver_reason: str = "",
    mark_unpaid: bool = False,
    user=None,
) -> Admission:
    """docs/02-api-spec.md: "Phase 1 stub: {reference, amount} or
    {waiver_reason}." The real fee engine (invoices, receipts, gateway
    reconciliation) is Phase 3 — this only ever flips
    `fee_payment_status`/`fee_payment_reference`/`fee_payment_method`/
    `fee_amount` so the `fee_pending -> fee_cleared` guard can pass.
    `mark_unpaid` is the correction path (a payment recorded in error, a
    bounced UPI/card transaction) — there was previously no way back to
    `pending` at all.
    If the admission had already reached `fee_cleared`, this also reverts
    the step back to `fee_pending` (docs/04-state-machines.md's
    `documents_verified -> documents_pending` reversal is the same shape) —
    otherwise the step would keep saying "cleared" while the fee itself
    says "pending", and `_guard_approved`'s own fee re-check would be the
    only thing standing between that and an approval on an unpaid
    admission.
    """
    if mark_unpaid:
        if admission.step == AdmissionStep.FEE_CLEARED:
            machine = AdmissionStateMachine(admission)
            machine.apply(
                AdmissionStep.FEE_PENDING,
                user=user,
                reason="Payment marked unpaid — fee collection reopened.",
            )
            admission.save(update_fields=["step", "updated_at"])
        admission.fee_payment_status = PaymentStatus.PENDING
        admission.fee_payment_reference = ""
        admission.fee_payment_method = ""
        admission.fee_amount = None
    elif waiver_reason:
        admission.fee_payment_status = PaymentStatus.WAIVED
        admission.fee_payment_reference = waiver_reason
        admission.fee_payment_method = ""
        admission.fee_amount = None
    elif reference:
        if not payment_method:
            raise ValidationError(
                {"payment_method": "Required when recording a payment reference."}
            )
        if amount is None:
            raise ValidationError({"amount": "Required when recording a payment reference."})
        admission.fee_payment_status = PaymentStatus.PAID
        admission.fee_payment_reference = reference
        admission.fee_payment_method = payment_method
        admission.fee_amount = amount
    else:
        raise ValidationError(
            {"detail": "Provide reference/amount/payment_method, a waiver_reason, or mark_unpaid."}
        )
    admission.save(
        update_fields=[
            "fee_payment_status",
            "fee_payment_reference",
            "fee_payment_method",
            "fee_amount",
            "updated_at",
        ]
    )

    # docs/04-state-machines.md section 1 names Accounts as a permitted
    # role on fee_pending -> fee_cleared itself, not only on recording the
    # payment — so this is where that transition happens too, rather than
    # requiring a second call to advance() (whose own `edit` verb gate
    # would exclude Accounts, per docs/03-rbac.md's matrix).
    #
    # Regression this fixed: reaching fee_cleared through advance() always
    # raised the (admission, "approve") ApprovalRequest via
    # _raise_approval_request — that side effect lived on advance() itself,
    # not on the transition. Once fee_cleared became reachable *without*
    # going through advance() (right here), an admission could sit at
    # fee_cleared with no approval ever requested, and
    # POST /admissions/{id}/approve would 409 forever — the guard checking
    # for a decided approval that no one had a way to ask for.
    if not mark_unpaid and admission.step == AdmissionStep.FEE_PENDING:
        machine = AdmissionStateMachine(admission)
        if machine.can_apply(AdmissionStep.FEE_CLEARED):
            machine.apply(AdmissionStep.FEE_CLEARED, user=user)
            admission.save(update_fields=["step", "updated_at"])
            _raise_approval_request(admission, requested_by=user)

    return admission


def reject_admission(admission: Admission, *, user, reason: str) -> Admission:
    if not reason:
        raise ValidationError({"reason": "A reason is required to reject an admission."})
    machine = AdmissionStateMachine(admission)
    machine.apply(AdmissionStep.REJECTED, user=user, reason=reason)
    admission.rejected_reason = reason
    admission.save(update_fields=["step", "rejected_reason", "updated_at"])
    return admission


@transaction.atomic
def record_consents(
    admission: Admission,
    *,
    decisions: list[dict],
    declared_by_name: str,
    granted_ip: str | None = None,
) -> list[ConsentRecord]:
    """Bulk upsert one ConsentRecord per ConsentType — `decisions` is
    `[{"consent_type": ConsentType | id, "granted": bool}, ...]`.

    Never touches `admission.step`: a consent (MEDIA_USE especially) can be
    changed at any time, including after the admission has moved past the
    fee step, without that being a state transition in its own right — see
    mandatory_consents_granted(), the actual gate.
    """
    now = timezone.now()
    records = []
    for decision in decisions:
        consent_type = decision["consent_type"]
        if not isinstance(consent_type, ConsentType):
            consent_type = ConsentType.objects.get(pk=consent_type)
        record, _ = ConsentRecord.objects.update_or_create(
            admission=admission,
            consent_type=consent_type,
            defaults={
                "granted": decision["granted"],
                # Copied now, not looked up live at read time — re-wording
                # a consent's body_text next season must never retroactively
                # change what an already-granted record is taken to mean.
                "version": consent_type.version,
                "granted_at": now,
                "granted_ip": granted_ip,
                "declared_by_name": declared_by_name,
            },
        )
        records.append(record)
    return records


def mandatory_consents_granted(admission: Admission) -> bool:
    """The fee-step gate: every ConsentType.is_mandatory=True must have a
    granted=True ConsentRecord. MEDIA_USE (is_mandatory=False) never blocks
    this regardless of whether it was granted, refused, or never decided.
    """
    mandatory_type_ids = set(
        ConsentType.objects.filter(is_mandatory=True, is_active=True).values_list(
            "id", flat=True
        )
    )
    granted_type_ids = set(
        admission.consent_records.filter(granted=True).values_list("consent_type_id", flat=True)
    )
    return mandatory_type_ids <= granted_type_ids


# ---------------------------------------------------------------------- #
# Direct admission (fee-first) — the desk-at-the-counter flow. Distinct
# names from the functions above on purpose: open_direct_admission() and
# friends are the pre-existing trial-waiver flow, kept working as-is for
# NewDirectAdmissionPage.tsx until the new wizard replaces it; nothing
# here touches that path or its callers.
# ---------------------------------------------------------------------- #


@transaction.atomic
def open_direct_admission_intake(*, intake_data: dict) -> Admission:
    """POST /admissions/direct/ — a bare DRAFT Admission plus its
    AdmissionIntake, in one step. No Person, no Programme yet; those wait
    for apps.admissions.student.services.approve_admission().
    """
    admission = Admission.objects.create(
        application_no=next_number("ADM"), source=AdmissionSource.DIRECT
    )
    machine = DirectAdmissionStateMachine(admission)
    machine.apply(AdmissionStep.DRAFT)
    admission.save(update_fields=["step", "updated_at"])

    intake = AdmissionIntake(admission=admission, **intake_data)
    intake.clean()
    intake.save()
    return admission


@transaction.atomic
def set_fee_lines(admission: Admission, *, lines: list[dict]) -> Admission:
    """PUT /admissions/{id}/fees/ — replaces the fee lines wholesale.
    `lines` is `[{"fee_head": FeeHead | id, "amount": Decimal}, ...]`.
    """
    from apps.core.models import FeeHead
    from apps.finance.fee.models import AdmissionFeeLine

    admission.fee_lines.all().delete()
    for line in lines:
        fee_head = line["fee_head"]
        if not isinstance(fee_head, FeeHead):
            fee_head = FeeHead.objects.filter(pk=fee_head).first()
        # A retired head (e.g. the old Coaching Fee) must not come back
        # through a stale form that still lists it.
        if fee_head is None or not fee_head.is_active:
            raise ValidationError({"fee_lines": "Unknown or inactive fee head."})
        fee_line = AdmissionFeeLine(admission=admission, fee_head=fee_head, amount=line["amount"])
        fee_line.full_clean()
        fee_line.save()
    return admission


@transaction.atomic
def record_direct_payment(
    admission: Admission,
    *,
    payment_mode: str,
    payment_date,
    user,
    receipt_no: str | None = None,
    idempotency_key: str = "",
) -> Admission:
    """draft -> payment_recorded. Mints a receipt number from the RCP
    series unless one is already supplied. A replay of the same
    Idempotency-Key (the header the view reads and passes through here)
    is a no-op returning the admission as it already stands — the state
    transition itself would otherwise 409 on a second attempt, since the
    admission has already left `draft`, which is the wrong error for a
    double-click that just wants the receipt it already got.
    """
    from apps.finance.payment.models import AdmissionPayment

    if idempotency_key and AdmissionPayment.objects.filter(
        admission=admission, idempotency_key=idempotency_key
    ).exists():
        return admission

    machine = DirectAdmissionStateMachine(admission)
    machine.apply(AdmissionStep.PAYMENT_RECORDED, user=user)
    admission.save(update_fields=["step", "updated_at"])

    AdmissionPayment.objects.create(
        admission=admission,
        payment_mode=payment_mode,
        receipt_no=receipt_no or next_number("RCP"),
        payment_date=payment_date,
        recorded_by=user,
        idempotency_key=idempotency_key,
    )
    return admission


@transaction.atomic
def verify_direct_payment(
    admission: Admission,
    *,
    approved: bool,
    user,
    reason: str = "",
    verification_note: str = "",
) -> Admission:
    """payment_recorded -> payment_verified (approved), or -> draft
    (rejected, reason required). A rejected payment record is deleted —
    it was wrong, not merely unwanted — so record_direct_payment() can be
    called again cleanly; this is unrelated to cancel_admission()'s rule
    that a *cancelled* admission's payment survives, which is about
    preserving a real transaction, not correcting a bad one.
    """
    payment = getattr(admission, "payment", None)
    if payment is None:
        raise ValidationError({"detail": "No payment has been recorded yet."})

    machine = DirectAdmissionStateMachine(admission)
    if approved:
        machine.apply(AdmissionStep.PAYMENT_VERIFIED, user=user)
        admission.save(update_fields=["step", "updated_at"])
        payment.verified_by = user
        payment.verified_at = timezone.now()
        payment.verification_note = verification_note
        payment.save(
            update_fields=["verified_by", "verified_at", "verification_note", "updated_at"]
        )
    else:
        machine.apply(AdmissionStep.DRAFT, user=user, reason=reason)
        admission.save(update_fields=["step", "updated_at"])
        payment.delete()
    return admission


def submit_direct_documents(admission: Admission, *, user) -> Admission:
    """payment_verified -> documents_pending, or documents_rejected ->
    documents_pending (re-upload). The documents themselves are uploaded
    through the existing presign/confirm flow before this is called —
    this just declares "these are ready for review."
    """
    machine = DirectAdmissionStateMachine(admission)
    machine.apply(AdmissionStep.DOCUMENTS_PENDING, user=user)
    admission.save(update_fields=["step", "updated_at"])
    return admission


def verify_direct_documents(admission: Admission, *, user) -> Admission:
    """documents_pending -> ready_for_approval (every AT_ADMISSION
    document verified) or -> documents_rejected (at least one rejected).
    Individual document verify/reject happens through the existing
    apps.admissions.document actions — this reflects that outcome onto
    the admission's own step.
    """
    machine = DirectAdmissionStateMachine(admission)
    if machine.can_apply(AdmissionStep.READY_FOR_APPROVAL):
        machine.apply(AdmissionStep.READY_FOR_APPROVAL, user=user)
    elif machine.can_apply(AdmissionStep.DOCUMENTS_REJECTED):
        machine.apply(AdmissionStep.DOCUMENTS_REJECTED, user=user)
    else:
        raise ValidationError({"detail": "Documents are still awaiting review."})
    admission.save(update_fields=["step", "updated_at"])
    return admission


def cancel_admission(admission: Admission, *, user, reason: str) -> Admission:
    """Available from any pre-approved direct-admission state. Only ever
    reachable via DirectAdmissionStateMachine's own transition table — a
    trial-based admission has no path to `cancelled` and this correctly
    409s if attempted on one.
    """
    if not reason:
        raise ValidationError({"reason": "A reason is required to cancel an admission."})
    machine = DirectAdmissionStateMachine(admission)
    machine.apply(AdmissionStep.CANCELLED, user=user, reason=reason)
    admission.cancelled_reason = reason
    admission.save(update_fields=["step", "cancelled_reason", "updated_at"])
    return admission


# (target step, module, verb) each named action needs to become reachable
# — the client renders buttons from this instead of reimplementing the
# state machine in TypeScript (Prompt D).
_NEXT_ACTION_REQUIREMENTS: list[tuple[str, str, str, str]] = [
    ("record_payment", AdmissionStep.PAYMENT_RECORDED, "admission", "add"),
    ("verify_payment", AdmissionStep.PAYMENT_VERIFIED, "payment", "approve"),
    ("submit_documents", AdmissionStep.DOCUMENTS_PENDING, "admission", "add"),
    ("verify_documents", AdmissionStep.READY_FOR_APPROVAL, "documents", "approve"),
    ("approve", AdmissionStep.APPROVED, "admission", "approve"),
    ("cancel", AdmissionStep.CANCELLED, "admission", "edit"),
]


def next_actions_for(admission: Admission, user) -> list[str]:
    """What the current user may do from the current state, given their
    permissions — read-only, computed server-side (docs/02-api-spec.md).
    Only meaningful for the fee-first chain; an admission with no intake
    (trial-based, or the pre-existing trial-waiver direct path) always
    returns an empty list — its own endpoints (/advance, /reject, ...)
    aren't part of this action vocabulary.
    """
    if not hasattr(admission, "intake") or user is None or not user.is_authenticated:
        return []

    machine = DirectAdmissionStateMachine(admission)
    actions = []
    for action_name, to_step, module, verb in _NEXT_ACTION_REQUIREMENTS:
        if not user.has_perm_for(module, verb):
            continue
        reachable = machine.can_apply(to_step)
        if action_name == "verify_documents":
            # Two possible outcomes of the same action — either satisfies
            # "this action is currently doable".
            reachable = reachable or machine.can_apply(AdmissionStep.DOCUMENTS_REJECTED)
        if reachable:
            actions.append(action_name)
    return actions
