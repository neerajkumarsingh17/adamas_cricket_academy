"""The generic approval engine (docs/01-data-model.md section 4). Reused
as-is by admission approval, trial waivers, fee waivers, status changes,
discounts/scholarships (Phase 3), disciplinary action (Phase 11) and
contracts (Phase 9) — nothing here knows about any specific one of them.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.models import ApprovalRequest, ApprovalRule, ApprovalStatus


class NoApprovalRuleConfigured(Exception):
    """No ApprovalRule exists for this (module, action) pair."""


def request(subject: models.Model, module: str, action: str, requested_by) -> ApprovalRequest:
    """Open a pending approval request for `subject` (any model instance)."""
    try:
        rule = ApprovalRule.objects.get(module=module, action=action)
    except ApprovalRule.DoesNotExist:
        raise NoApprovalRuleConfigured(
            f"No ApprovalRule for module={module!r} action={action!r}. "
            f"Add one before requesting this kind of approval."
        ) from None

    return ApprovalRequest.objects.create(
        rule=rule,
        content_type=ContentType.objects.get_for_model(subject),
        object_id=subject.pk,
        requested_by=requested_by,
    )


def can_decide(approval_request: ApprovalRequest, user) -> bool:
    """docs/02-api-spec.md: "module of the subject / approve" — the user
    needs the module's "approve" verb AND to hold the rule's required_role.
    Two different roles can both have "approve" on a module (e.g. grievance)
    while only one of them is who this specific rule routes to.
    """
    if not user.has_perm_for(approval_request.rule.module, "approve"):
        return False
    held_role_ids = {role.id for role in user.current_roles()}
    return approval_request.rule.required_role_id in held_role_ids


def decidable_by(user) -> models.QuerySet[ApprovalRequest]:
    """Pending requests `user` is permitted to decide — GET /approvals.

    A real QuerySet (not a Python-filtered list), so DRF's cursor
    pagination — which needs .order_by() — still works. The "approve"
    verb check is expressed as rule__module__in against the modules
    user.resolved_permissions() already says grant "approve", rather than
    calling has_perm_for() per row, so this stays one query.
    """
    held_role_ids = {role.id for role in user.current_roles()}
    approvable_modules = {
        module for (module, verb) in user.resolved_permissions() if verb == "approve"
    }
    return ApprovalRequest.objects.filter(
        status=ApprovalStatus.PENDING,
        rule__required_role_id__in=held_role_ids,
        rule__module__in=approvable_modules,
    ).select_related("rule", "content_type")


def decide(
    approval_request: ApprovalRequest, user, approve: bool, reason: str = ""
) -> ApprovalRequest:
    """Approve or reject. Rejection always requires a reason. A requester
    can never approve their own request (rejecting/withdrawing your own
    request is fine — that's not the conflict of interest this guards
    against).
    """
    if approval_request.status != ApprovalStatus.PENDING:
        raise ValidationError("This request has already been decided.")

    if not can_decide(approval_request, user):
        raise PermissionDenied("You are not permitted to decide this request.")

    if approve and approval_request.requested_by_id == user.id:
        raise PermissionDenied("You cannot approve your own request.")

    if not approve and not reason:
        raise ValidationError({"reason": "A reason is required to reject a request."})

    approval_request.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
    approval_request.decided_by = user
    approval_request.decided_at = timezone.now()
    approval_request.reason = reason
    approval_request.save(
        update_fields=["status", "decided_by", "decided_at", "reason", "updated_at"]
    )
    return approval_request
