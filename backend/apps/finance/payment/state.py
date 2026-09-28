"""Payment.status transitions for the unified ledger — see models.py's
Payment docstring for the two-stage confirmation/invoice design.
"""

from apps.core.state import StateMachine, Transition

from .models import PaymentLedgerStatus


class PaymentStateMachine(StateMachine):
    """No `roles=` on any transition, same reasoning as
    apps.admissions.document.state.DocumentStateMachine: the `payment`
    RBAC row's verbs (record vs settle) are the only gate a
    module+verb check already enforces at the view layer.
    """

    field_name = "status"
    transitions = [
        # A brand-new Payment is created directly at CONFIRMED by
        # services.record_payment (status has its own model default) —
        # this transition exists so PaymentStateMachine.can_apply() can
        # still answer "is CONFIRMED reachable" for a not-yet-saved
        # instance, consistent with every other machine in this codebase.
        Transition(to=PaymentLedgerStatus.CONFIRMED, frm=None),
        Transition(to=PaymentLedgerStatus.SETTLED, frm=frozenset({PaymentLedgerStatus.CONFIRMED})),
        Transition(
            to=PaymentLedgerStatus.VOID,
            frm=frozenset({PaymentLedgerStatus.CONFIRMED}),
            reason_required=True,
        ),
    ]
