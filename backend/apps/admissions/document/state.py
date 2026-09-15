"""docs/04-state-machines.md section 4."""

from apps.core.state import StateMachine, Transition

from .models import DocumentStatus


class DocumentStateMachine(StateMachine):
    """Unlike `apps.admissions.student.state.StudentStatusMachine`, no
    transition here sets `roles=` — docs/03-rbac.md's `documents` row
    already grants exactly Administration and Academy Head `approve`, and
    Administration/Parent `add`, with nothing else needing a code-level
    override the way medical_hold/fee_hold or trial's Head-Coach-approve
    gap did. The view's `has_perm_for("documents", verb)` check is the
    only gate; adding a second, narrower one here would silently exclude
    Academy Head from verifying documents for no documented reason.
    """

    field_name = "status"
    transitions = [
        Transition(to=DocumentStatus.SUBMITTED, frm=frozenset({DocumentStatus.PENDING})),
        Transition(to=DocumentStatus.VERIFIED, frm=frozenset({DocumentStatus.SUBMITTED})),
        Transition(
            to=DocumentStatus.REJECTED,
            frm=frozenset({DocumentStatus.SUBMITTED}),
            reason_required=True,
        ),
        Transition(to=DocumentStatus.SUBMITTED, frm=frozenset({DocumentStatus.REJECTED})),
        Transition(to=DocumentStatus.EXPIRED, frm=frozenset({DocumentStatus.VERIFIED})),
        Transition(to=DocumentStatus.SUBMITTED, frm=frozenset({DocumentStatus.EXPIRED})),
    ]
