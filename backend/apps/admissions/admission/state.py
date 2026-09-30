"""docs/04-state-machines.md section 1 — the admission chain, collapsed
into the 7 persisted `Admission.step` states.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from apps.core.models import ApprovalStatus
from apps.core.state import StateMachine, Transition

from .models import Admission, AdmissionStep, PaymentStatus


def _guard_draft(admission: Admission, **_) -> bool:
    if admission.trial_registration_id:
        result = getattr(admission.trial_registration, "result", None)
        return result is not None and result.outcome == "selected"
    # Direct admission (no trial): Administration opens these on its own,
    # no Academy Head sign-off gate here (product decision — the
    # direct-admission feature). `direct_admission_reason` being set,
    # enforced by `services.open_direct_admission`, is the traceability
    # record in place of an approval.
    return bool(admission.direct_admission_reason)


def _guard_documents_pending(admission: Admission, **_) -> bool:
    # Trial-based only: a direct admission collects fee first (product
    # decision — step 2.1), via the parallel `FEE_PENDING, frm={DRAFT}`
    # transition guarded by `_guard_direct_only` below — this is the
    # documents-first order's own guard, so it has to refuse a direct
    # admission rather than just leaving it unreachable through the UI.
    # Re-checks the `draft` entry condition, not just "has checklist items"
    # — belt and braces in case a trial's result is later reversed after
    # checklist items were already created.
    return (
        admission.trial_registration_id is not None
        and _guard_draft(admission)
        and admission.checklist_items.exists()
    )


def _guard_documents_verified(admission: Admission, **_) -> bool:
    # "Every mandatory item is verified" is vacuously true if there are no
    # mandatory items at all — requiring at least one to exist would wrongly
    # block a programme with no mandatory document types configured.
    mandatory = admission.checklist_items.filter(is_mandatory=True)
    return not mandatory.exclude(status="verified").exists()


def _guard_fee_cleared(admission: Admission, **_) -> bool:
    return admission.fee_payment_status in (PaymentStatus.PAID, PaymentStatus.WAIVED)


def _guard_direct_only(admission: Admission, **_) -> bool:
    """Gates the direct-admission path's fee-before-documents shortcut
    (product decision — step 2.1: payment first, then the candidate's own
    portal upload). A trial-based admission always has `trial_registration`
    set, so this refuses it — that path keeps the original
    documents-before-fee order below.
    """
    return admission.trial_registration_id is None


def _guard_fee_cleared_to_documents_pending(admission: Admission, *, reason: str = "", **_) -> bool:
    """One transition serves two different callers, distinguished by path
    rather than by two competing `Transition` rows (which `StateMachine.
    _candidates()` would resolve by declaration order, not by which one
    actually applies — see the transitions list below for why they can't
    just be separate entries with overlapping `frm`).

    Direct admission: this *is* the forward flow onto step 2.1 (fee
    cleared, now collect documents through the candidate's own portal
    upload) — no reason needed. Trial-based: fee was already cleared via
    the documents-first path, so landing back on `documents_pending` from
    here only happens because a verified document was later rejected or
    expired — the same reversal as the documents_verified/fee_pending
    transition below, and it still needs a reason.
    """
    if admission.trial_registration_id is None:
        return admission.checklist_items.exists()
    if not reason:
        raise ValidationError({"reason": "A reason is required for this transition."})
    return True


def _guard_approved(admission: Admission, **_) -> bool:
    from apps.core.models import ApprovalRequest

    # Re-checks the fee guard *and* the documents guard, not only the
    # approval decision: if a payment was marked unpaid, or a previously
    # verified mandatory document was later rejected/expired, after the
    # admission had already moved past that gate but before the step
    # itself got reverted, approval must still refuse. Money and identity
    # are transactional (CLAUDE.md rule 7) — "the approval was already
    # granted" isn't a reason to let an unpaid or undocumented admission
    # through because a step-regression signal happened to arrive late or
    # not at all.
    if not _guard_fee_cleared(admission) or not _guard_documents_verified(admission):
        return False
    if admission.trial_registration_id is None:
        # Direct admission: Administration/Accounts already confirmed
        # payment themselves reaching this point — no separate Academy
        # Head sign-off for this path (product decision — the
        # direct-admission feature). Trial-based admissions still require
        # the ApprovalRequest below.
        return True
    return ApprovalRequest.objects.filter(
        content_type=ContentType.objects.get_for_model(Admission),
        object_id=admission.id,
        rule__module="admission",
        rule__action="approve",
        status=ApprovalStatus.APPROVED,
    ).exists()


class AdmissionStateMachine(StateMachine):
    field_name = "step"
    transitions = [
        Transition(to=AdmissionStep.DRAFT, frm=None, guard=_guard_draft),
        Transition(
            to=AdmissionStep.DOCUMENTS_PENDING,
            frm=frozenset({AdmissionStep.DRAFT}),
            guard=_guard_documents_pending,
        ),
        Transition(
            to=AdmissionStep.DOCUMENTS_VERIFIED,
            frm=frozenset({AdmissionStep.DOCUMENTS_PENDING}),
            guard=_guard_documents_verified,
        ),
        Transition(to=AdmissionStep.FEE_PENDING, frm=frozenset({AdmissionStep.DOCUMENTS_VERIFIED})),
        Transition(
            # Direct admission only (product decision — step 2.1): payment
            # is collected *before* documents, straight out of `draft`.
            # `_guard_direct_only` refuses this for a trial-based
            # admission, which still has to earn `documents_verified`
            # first via the transition above.
            to=AdmissionStep.FEE_PENDING,
            frm=frozenset({AdmissionStep.DRAFT}),
            guard=_guard_direct_only,
        ),
        Transition(
            to=AdmissionStep.FEE_CLEARED,
            frm=frozenset({AdmissionStep.FEE_PENDING}),
            guard=_guard_fee_cleared,
        ),
        Transition(
            to=AdmissionStep.APPROVED,
            frm=frozenset({AdmissionStep.FEE_CLEARED}),
            guard=_guard_approved,
        ),
        Transition(
            # Direct admission only: documents come *after* fee_cleared on
            # this path (see the fee_cleared -> documents_pending
            # transition below), so `approved` is reached from
            # `documents_verified` instead of `fee_cleared`. `_guard_
            # approved` already re-checks both the fee and documents
            # guards regardless of which state it's called from, so this
            # is safe to add without touching that guard.
            to=AdmissionStep.APPROVED,
            frm=frozenset({AdmissionStep.DOCUMENTS_VERIFIED}),
            guard=_guard_approved,
        ),
        Transition(
            to=AdmissionStep.REJECTED,
            frm=frozenset({AdmissionStep.FEE_CLEARED}),
            reason_required=True,
        ),
        Transition(
            # A mandatory document can be invalidated (rejected/expired)
            # at any point before final approval, not only while the
            # admission happens to still be sitting at documents_verified
            # — it may have already moved on to fee collection. Both land
            # back at documents_pending; `_guard_approved` above is the
            # backstop if this reversal is somehow never triggered. The
            # `fee_cleared` source lives in its own transition right below
            # — it also has to serve the direct-admission forward flow,
            # which this one (always `reason_required`) doesn't.
            to=AdmissionStep.DOCUMENTS_PENDING,
            frm=frozenset({AdmissionStep.DOCUMENTS_VERIFIED, AdmissionStep.FEE_PENDING}),
            reason_required=True,
        ),
        Transition(
            to=AdmissionStep.DOCUMENTS_PENDING,
            frm=frozenset({AdmissionStep.FEE_CLEARED}),
            guard=_guard_fee_cleared_to_documents_pending,
        ),
        Transition(
            # A payment marked unpaid after the admission reached
            # fee_cleared (services.record_payment's `mark_unpaid`
            # correction) reopens fee collection — the same
            # "something got invalidated after the gate passed" shape as
            # documents_verified -> documents_pending above.
            to=AdmissionStep.FEE_PENDING,
            frm=frozenset({AdmissionStep.FEE_CLEARED}),
            reason_required=True,
        ),
    ]


# ---------------------------------------------------------------------- #
# Direct admission (fee-first) — an entirely separate transition table,
# scoped to source=DIRECT rows. Shares the `step` field and three state
# names (draft, documents_pending, approved) with AdmissionStateMachine
# above where the meaning genuinely lines up, but never shares a
# Transition row — the two chains run in a different order (fee before
# documents) and mixing their guards the way the old trial-waiver
# implementation did made each one harder to reason about on its own.
# ---------------------------------------------------------------------- #


def _required_at_admission_document_type_ids() -> set:
    from apps.core.models import DocumentRequiredStage, DocumentType

    return set(
        DocumentType.objects.filter(
            required_stage=DocumentRequiredStage.AT_ADMISSION, applies_to="admission"
        ).values_list("id", flat=True)
    )


def _admission_documents(admission: Admission, **filters):
    from apps.admissions.document.models import Document

    return Document.objects.filter(
        owner_content_type=ContentType.objects.get_for_model(Admission),
        owner_object_id=admission.id,
        **filters,
    )


def _guard_ready_for_payment(admission: Admission, **_) -> bool:
    """draft -> payment_recorded, via services.record_direct_payment():
    the intake is complete and valid, every mandatory consent is granted,
    and at least the mandatory fee heads are present among the fee lines.

    Raises a field-level ValidationError naming exactly what's missing
    instead of returning False — StateMachine.apply()'s generic "conditions
    ... are not met" fallback (apps/core/state.py) gave no clue which of
    these three unrelated things was the actual problem.
    """
    intake = getattr(admission, "intake", None)
    if intake is None:
        raise ValidationError({"detail": "Intake details haven't been saved yet."})
    try:
        intake.clean()
    except DjangoValidationError as exc:
        raise ValidationError({"intake": exc.messages}) from exc

    from . import services

    if not services.mandatory_consents_granted(admission):
        from .models import ConsentType

        granted_ids = set(admission.consent_records.filter(granted=True).values_list(
            "consent_type_id", flat=True
        ))
        missing = ConsentType.objects.filter(is_mandatory=True, is_active=True).exclude(
            id__in=granted_ids
        )
        raise ValidationError(
            {
                "consents": (
                    "Missing required consent(s): "
                    + ", ".join(c.label for c in missing)
                )
            }
        )

    from apps.core.models import FeeHead

    mandatory_heads = FeeHead.objects.filter(is_mandatory=True, is_active=True)
    present_head_ids = set(admission.fee_lines.values_list("fee_head_id", flat=True))
    missing_heads = mandatory_heads.exclude(id__in=present_head_ids)
    if missing_heads.exists():
        raise ValidationError(
            {
                "fee_lines": (
                    "Missing required fee line(s): "
                    + ", ".join(h.label for h in missing_heads)
                )
            }
        )
    return True


def _guard_payment_verified(admission: Admission, **_) -> bool:
    """payment_recorded -> payment_verified, via
    services.verify_direct_payment(approved=True)."""
    return hasattr(admission, "payment")


def _guard_documents_submitted(admission: Admission, **_) -> bool:
    """payment_verified -> documents_pending (first submission) and
    documents_rejected -> documents_pending (re-upload): one Document per
    AT_ADMISSION DocumentType, none of them rejected or expired. A
    just-uploaded Document is always `submitted` in this codebase's
    vocabulary — there's no pre-created "pending" placeholder row the way
    AdmissionChecklistItem has, since these attach straight to the
    Admission via the generic FK.
    """
    from apps.admissions.document.models import DocumentStatus

    required_type_ids = _required_at_admission_document_type_ids()
    if not required_type_ids:
        return True
    submitted_type_ids = set(
        _admission_documents(
            admission,
            document_type_id__in=required_type_ids,
            status__in=[DocumentStatus.SUBMITTED, DocumentStatus.VERIFIED],
        ).values_list("document_type_id", flat=True)
    )
    return required_type_ids <= submitted_type_ids


def _guard_documents_all_verified(admission: Admission, **_) -> bool:
    """documents_pending -> ready_for_approval, via
    services.verify_direct_documents(): every AT_ADMISSION document is
    verified. Vacuously true if no AT_ADMISSION document type is
    configured at all — same reasoning as the trial chain's
    _guard_documents_verified above.
    """
    from apps.admissions.document.models import DocumentStatus

    required_type_ids = _required_at_admission_document_type_ids()
    if not required_type_ids:
        return True
    verified_type_ids = set(
        _admission_documents(
            admission, document_type_id__in=required_type_ids, status=DocumentStatus.VERIFIED
        ).values_list("document_type_id", flat=True)
    )
    return required_type_ids <= verified_type_ids


def _guard_documents_any_rejected(admission: Admission, **_) -> bool:
    """documents_pending -> documents_rejected: at least one AT_ADMISSION
    document has been rejected (through the existing, unchanged
    apps.admissions.document verify/reject actions — this guard just
    reflects that state onto the admission)."""
    from apps.admissions.document.models import DocumentStatus

    required_type_ids = _required_at_admission_document_type_ids()
    if not required_type_ids:
        return False
    return _admission_documents(
        admission, document_type_id__in=required_type_ids, status=DocumentStatus.REJECTED
    ).exists()


def _guard_ready_for_approval_to_approved(admission: Admission, **_) -> bool:
    """ready_for_approval -> approved: re-checks the documents guard
    defensively, same reasoning as the trial chain's _guard_approved — a
    verified document later rejected/expired must still refuse approval
    even if the step itself hasn't been reverted yet."""
    return _guard_documents_all_verified(admission)


_PRE_APPROVAL_DIRECT_STATES = frozenset(
    {
        AdmissionStep.DRAFT,
        AdmissionStep.PAYMENT_RECORDED,
        AdmissionStep.PAYMENT_VERIFIED,
        AdmissionStep.DOCUMENTS_PENDING,
        AdmissionStep.DOCUMENTS_REJECTED,
    }
)


class DirectAdmissionStateMachine(StateMachine):
    field_name = "step"
    transitions = [
        # Not `frm=None` — `Admission.step` always has a real value
        # ("draft", the field default), never a genuinely blank one, and
        # `frm=None` matches *any* current state, not just "no state yet".
        # With a second transition below also targeting `draft` (the
        # payment-rejection regression), an unconditional wildcard here
        # would always win `_candidates()`'s first-match-by-declaration-
        # order resolution and silently swallow that one's reason_required
        # check. `frm={DRAFT}` only ever matches the real "already in
        # draft" case open_direct_admission_intake() calls this for.
        Transition(to=AdmissionStep.DRAFT, frm=frozenset({AdmissionStep.DRAFT})),
        Transition(
            to=AdmissionStep.PAYMENT_RECORDED,
            frm=frozenset({AdmissionStep.DRAFT}),
            guard=_guard_ready_for_payment,
        ),
        Transition(
            to=AdmissionStep.PAYMENT_VERIFIED,
            frm=frozenset({AdmissionStep.PAYMENT_RECORDED}),
            guard=_guard_payment_verified,
        ),
        Transition(
            # A payment verifier can reject too — verify_direct_payment()
            # covers both outcomes of the same review, same shape as the
            # trial chain's mark_unpaid correction below.
            to=AdmissionStep.DRAFT,
            frm=frozenset({AdmissionStep.PAYMENT_RECORDED}),
            reason_required=True,
        ),
        Transition(
            to=AdmissionStep.DOCUMENTS_PENDING,
            frm=frozenset({AdmissionStep.PAYMENT_VERIFIED}),
            guard=_guard_documents_submitted,
        ),
        Transition(
            to=AdmissionStep.READY_FOR_APPROVAL,
            frm=frozenset({AdmissionStep.DOCUMENTS_PENDING}),
            guard=_guard_documents_all_verified,
        ),
        Transition(
            to=AdmissionStep.DOCUMENTS_REJECTED,
            frm=frozenset({AdmissionStep.DOCUMENTS_PENDING}),
            guard=_guard_documents_any_rejected,
        ),
        Transition(
            to=AdmissionStep.DOCUMENTS_PENDING,
            frm=frozenset({AdmissionStep.DOCUMENTS_REJECTED}),
            guard=_guard_documents_submitted,
        ),
        Transition(
            to=AdmissionStep.APPROVED,
            frm=frozenset({AdmissionStep.READY_FOR_APPROVAL}),
            guard=_guard_ready_for_approval_to_approved,
        ),
        Transition(
            to=AdmissionStep.CANCELLED,
            frm=_PRE_APPROVAL_DIRECT_STATES,
            reason_required=True,
        ),
    ]
