"""docs/04-state-machines.md section 2 — the 7 statuses actually reachable
as a *transition* on an existing `Student` row.

`enquiry`, `trial` and `admission_pending` are excluded even though they're
named `StudentStatus` choices: the doc itself calls the first two
"conceptually pre-student ... never written to this field", and a
`Student` row is only ever created already `active` (docs/04
section 1: admission approval "creates the Student record and sets status
to Active") — there is no existing row to transition *into*
`admission_pending`, so it can never be a real `StateMachine` transition
either. `Student.status` defaulting to `active` at creation time is that
initial value, not a transition — consistent with `Document.status`
defaulting to `pending` and `Admission.step` defaulting to `draft`
elsewhere in this codebase, neither of which goes through a transition
call for its very first value.
"""

from django.contrib.contenttypes.models import ContentType

from apps.core.models import ApprovalStatus
from apps.core.state import StateMachine, Transition

from .models import Student, StudentStatus


def _approved_request_exists(student: Student, action: str) -> bool:
    from apps.core.models import ApprovalRequest

    return ApprovalRequest.objects.filter(
        content_type=ContentType.objects.get_for_model(Student),
        object_id=student.id,
        rule__module="students",
        rule__action=action,
        status=ApprovalStatus.APPROVED,
    ).exists()


def _guard_suspended(student: Student, **_) -> bool:
    return _approved_request_exists(student, StudentStatus.SUSPENDED)


def _guard_withdrawn(student: Student, **_) -> bool:
    return _approved_request_exists(student, StudentStatus.WITHDRAWN)


class StudentStatusMachine(StateMachine):
    """docs/03-rbac.md's "Rules that override the matrix": medical_team and
    accounts hold only `view` on the general `students` module row, yet the
    SOP is explicit that only they may set medical_hold/fee_hold. That
    override is enforced entirely through `Transition.roles` here, not
    through `has_perm_for` — deliberately: this is documented as one of the
    cases the RBAC *data* doesn't cover and code must.
    """

    field_name = "status"
    transitions = [
        Transition(
            to=StudentStatus.MEDICAL_HOLD,
            frm=frozenset({StudentStatus.ACTIVE}),
            roles=frozenset({"medical_team"}),
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.ACTIVE,
            frm=frozenset({StudentStatus.MEDICAL_HOLD}),
            roles=frozenset({"medical_team"}),
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.FEE_HOLD,
            frm=frozenset({StudentStatus.ACTIVE}),
            roles=frozenset({"accounts"}),
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.ACTIVE,
            frm=frozenset({StudentStatus.FEE_HOLD}),
            roles=frozenset({"accounts"}),
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.LEAVE,
            frm=frozenset({StudentStatus.ACTIVE}),
            roles=frozenset({"administration"}),
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.ACTIVE,
            frm=frozenset({StudentStatus.LEAVE}),
            roles=frozenset({"administration"}),
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.SUSPENDED,
            frm=frozenset({StudentStatus.ACTIVE}),
            roles=frozenset({"academy_head", "administration", "sports_ops"}),
            guard=_guard_suspended,
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.ACTIVE,
            frm=frozenset({StudentStatus.SUSPENDED}),
            roles=frozenset({"academy_head", "administration"}),
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.WITHDRAWN,
            frm=frozenset(
                {
                    StudentStatus.ACTIVE,
                    StudentStatus.LEAVE,
                    StudentStatus.SUSPENDED,
                    StudentStatus.FEE_HOLD,
                }
            ),
            roles=frozenset({"academy_head", "administration", "sports_ops"}),
            guard=_guard_withdrawn,
            reason_required=True,
        ),
        Transition(
            to=StudentStatus.COMPLETED,
            frm=frozenset({StudentStatus.ACTIVE}),
            roles=frozenset({"administration"}),
            reason_required=True,
        ),
    ]


APPROVAL_GATED_TARGETS = frozenset({StudentStatus.SUSPENDED, StudentStatus.WITHDRAWN})
