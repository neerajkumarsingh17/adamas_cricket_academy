"""docs/04-state-machines.md: "Every status in this system is a state
machine with guards and permitted roles, not a free text field. Never
assign a status field directly — call the transition method, which
validates the guard, checks the role, requires a reason where marked, and
writes the audit row."

The audit row itself needs no code here — `Admission`/`Student` are
`AuditedModel`, so `apps.audit.signals` already writes a diff the moment
the transition's `.save()` happens. This module is only the guard/role/
reason machinery in front of that save.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from rest_framework.exceptions import APIException, PermissionDenied, ValidationError


class InvalidTransition(APIException):
    status_code = 409
    default_code = "invalid_transition"
    default_detail = "This transition is not permitted from the current state."


@dataclass(frozen=True)
class Transition:
    """One row of a state machine's table.

    `frm`: source states this transition applies from. `None` means "no
    current value required" — used for the first transition into a new
    object, where the field may be blank/unset rather than one of the
    named states.
    `guard`: `(instance, **context) -> bool`. Raise inside it for an
    error message more specific than the generic 409; return `False` for
    the generic one.
    `roles`: role codes permitted to make this specific transition, beyond
    whatever module+verb the calling view already checked. `None` skips
    this layer — the view's permission check is the only gate.
    """

    to: str
    frm: frozenset[str] | None = None
    guard: Callable[..., bool] | None = None
    roles: frozenset[str] | None = None
    reason_required: bool = False


class StateMachine:
    """Subclass per status field:

        class AdmissionStateMachine(StateMachine):
            field_name = "step"
            transitions = [
                Transition(to="draft", frm=None, guard=_guard_draft),
                Transition(
                    to="documents_pending", frm=frozenset({"draft"}), guard=_guard_docs_ready
                ),
                ...
            ]

    Then, in a service function:

        machine = AdmissionStateMachine(admission)
        machine.apply("documents_pending", user=request.user)
        admission.save()
    """

    field_name: str
    transitions: Iterable[Transition] = ()

    def __init__(self, instance: Any) -> None:
        self.instance = instance

    @property
    def current(self) -> str:
        return getattr(self.instance, self.field_name)

    def _candidates(self, to: str) -> list[Transition]:
        return [
            t for t in self.transitions if t.to == to and (t.frm is None or self.current in t.frm)
        ]

    def can_apply(self, to: str, **guard_context: Any) -> bool:
        """Whether `to` is reachable from the current state *and* its
        guard (if any) currently passes — deliberately does not check
        `roles`/`reason_required`, which depend on who's asking and what
        they'd say, not on the object's own state. A `False` here means
        "the underlying condition isn't met yet"; `apply()` is still the
        one that enforces role/reason and raises specific errors.
        """
        transition = self.transition_for(to)
        if transition is None:
            return False
        if transition.guard is not None and not transition.guard(
            self.instance, user=None, reason="", **guard_context
        ):
            return False
        return True

    def transition_for(self, to: str) -> Transition | None:
        """The declared `Transition` that would fire for `to` from the
        current state, or `None` if none matches — for callers (like
        `apps.admissions.student.services.change_status`) that need to
        inspect a transition's guard/roles *before* deciding whether to
        call `apply()` at all, without reaching into the "private"
        `_candidates()`.
        """
        candidates = self._candidates(to)
        return candidates[0] if candidates else None

    def apply(self, to: str, *, user=None, reason: str = "", **guard_context: Any) -> None:
        """Validates and — on success — sets the field. Does **not** call
        `.save()`; the caller decides what else happens in the same
        transaction (e.g. admission approval also creates `Student`).
        """
        candidates = self._candidates(to)
        if not candidates:
            raise InvalidTransition(
                f"Cannot move {self.field_name!r} from {self.current!r} to {to!r}."
            )
        transition = candidates[0]

        if transition.roles is not None:
            held = {role.code for role in user.current_roles()} if user is not None else set()
            if not held & transition.roles:
                raise PermissionDenied("Your role is not permitted to make this transition.")

        if transition.reason_required and not reason:
            raise ValidationError({"reason": "A reason is required for this transition."})

        if transition.guard is not None and not transition.guard(
            self.instance, user=user, reason=reason, **guard_context
        ):
            raise InvalidTransition(
                f"The conditions for moving {self.field_name!r} to {to!r} are not met."
            )

        setattr(self.instance, self.field_name, to)
