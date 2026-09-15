"""End-to-end demonstration of the generic approval engine on one dummy
model (Person stands in for whatever real subject — Admission,
TrialRegistration, ... — a future module will actually request approval
for; the engine itself knows nothing about any of them).
"""

import datetime

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.core.models import ApprovalStatus
from apps.core.services import approvals
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import PermissionFactory, RolePermissionFactory, UserFactory
from apps.people.tests.factories import PersonFactory

from .factories import ApprovalRequestFactory, ApprovalRuleFactory


def _user_with_role(role, **user_kwargs):
    user = UserFactory(**user_kwargs)
    UserRole.objects.create(user=user, role=role, valid_from=datetime.date(2020, 1, 1))
    return user


@pytest.mark.django_db
def test_request_then_decide_end_to_end():
    """The full lifecycle on a dummy subject: open a request, an eligible
    decider approves it, and the record reflects the decision.
    """
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    requester = UserFactory()
    decider = _user_with_role(role_permission.role)
    person = PersonFactory()

    approval_request = approvals.request(
        subject=person, module="students", action="status_change", requested_by=requester
    )

    assert approval_request.rule == rule
    assert approval_request.status == ApprovalStatus.PENDING
    assert approval_request.subject == person

    decided = approvals.decide(approval_request, decider, approve=True, reason="Looks right.")

    assert decided.status == ApprovalStatus.APPROVED
    assert decided.decided_by == decider
    assert decided.decided_at is not None


@pytest.mark.django_db
def test_user_without_approve_verb_gets_403_via_http():
    """The Check: a user without the approve verb gets 403."""
    view_permission = PermissionFactory(module="students", verb="view")
    view_only_grant = RolePermissionFactory(permission=view_permission, scope="all")
    # view_only_grant.role now holds ONLY "view" on students — no approve
    # grant at all. required_role below is a completely separate role.
    approve_permission = PermissionFactory(module="students", verb="approve")
    someone_elses_role = RolePermissionFactory(permission=approve_permission, scope="all").role

    rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=someone_elses_role
    )
    approval_request = ApprovalRequestFactory(rule=rule)
    view_only_user = _user_with_role(view_only_grant.role)

    client = APIClient()
    client.force_authenticate(user=view_only_user)
    response = client.post(f"/api/v1/approvals/{approval_request.pk}/approve/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_requester_cannot_approve_own_request():
    """The Check: the requester cannot approve their own request."""
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    requester = _user_with_role(role_permission.role)
    approval_request = ApprovalRequestFactory(rule=rule, requested_by=requester)

    with pytest.raises(PermissionDenied):
        approvals.decide(approval_request, requester, approve=True, reason="")

    approval_request.refresh_from_db()
    assert approval_request.status == ApprovalStatus.PENDING


@pytest.mark.django_db
def test_requester_cannot_approve_own_request_via_http():
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    requester = _user_with_role(role_permission.role)
    approval_request = ApprovalRequestFactory(rule=rule, requested_by=requester)

    client = APIClient()
    client.force_authenticate(user=requester)
    response = client.post(f"/api/v1/approvals/{approval_request.pk}/approve/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_rejection_without_a_reason_is_refused():
    """The Check: a rejection without a reason is refused."""
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    decider = _user_with_role(role_permission.role)
    approval_request = ApprovalRequestFactory(rule=rule)

    with pytest.raises(ValidationError):
        approvals.decide(approval_request, decider, approve=False, reason="")

    approval_request.refresh_from_db()
    assert approval_request.status == ApprovalStatus.PENDING


@pytest.mark.django_db
def test_rejection_without_a_reason_is_refused_via_http():
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    decider = _user_with_role(role_permission.role)
    approval_request = ApprovalRequestFactory(rule=rule)

    client = APIClient()
    client.force_authenticate(user=decider)
    response = client.post(f"/api/v1/approvals/{approval_request.pk}/reject/", {"reason": ""})

    assert response.status_code == 400

    approval_request.refresh_from_db()
    assert approval_request.status == ApprovalStatus.PENDING


@pytest.mark.django_db
def test_rejection_with_a_reason_succeeds_via_http():
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    decider = _user_with_role(role_permission.role)
    approval_request = ApprovalRequestFactory(rule=rule)

    client = APIClient()
    client.force_authenticate(user=decider)
    response = client.post(
        f"/api/v1/approvals/{approval_request.pk}/reject/",
        {"reason": "Missing documentation."},
    )

    assert response.status_code == 200
    approval_request.refresh_from_db()
    assert approval_request.status == ApprovalStatus.REJECTED
    assert approval_request.reason == "Missing documentation."


@pytest.mark.django_db
def test_deciding_an_already_decided_request_is_refused():
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    decider = _user_with_role(role_permission.role)
    approval_request = ApprovalRequestFactory(rule=rule)

    approvals.decide(approval_request, decider, approve=True, reason="")

    with pytest.raises(ValidationError):
        approvals.decide(approval_request, decider, approve=True, reason="")


@pytest.mark.django_db
def test_decidable_by_only_returns_requests_the_user_may_decide():
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    matching_rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    other_role = RolePermissionFactory(permission=approve_permission, scope="all").role
    other_rule = ApprovalRuleFactory(
        module="students", action="withdrawal", required_role=other_role
    )

    decider = _user_with_role(role_permission.role)
    mine = ApprovalRequestFactory(rule=matching_rule)
    not_mine = ApprovalRequestFactory(rule=other_rule)

    decidable = approvals.decidable_by(decider)

    assert mine in decidable
    assert not_mine not in decidable


@pytest.mark.django_db
def test_approvals_list_endpoint_returns_only_decidable_requests():
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    matching_rule = ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )
    other_role = RolePermissionFactory(permission=approve_permission, scope="all").role
    other_rule = ApprovalRuleFactory(
        module="students", action="withdrawal", required_role=other_role
    )

    decider = _user_with_role(role_permission.role)
    mine = ApprovalRequestFactory(rule=matching_rule)
    ApprovalRequestFactory(rule=other_rule)

    client = APIClient()
    client.force_authenticate(user=decider)
    response = client.get("/api/v1/approvals/")

    assert response.status_code == 200
    returned_ids = {row["id"] for row in response.data["results"]}
    assert returned_ids == {str(mine.pk)}


@pytest.mark.django_db
def test_request_raises_when_no_rule_configured():
    person = PersonFactory()
    requester = UserFactory()

    with pytest.raises(approvals.NoApprovalRuleConfigured):
        approvals.request(
            subject=person, module="nonexistent", action="nope", requested_by=requester
        )


@pytest.mark.django_db
def test_role_can_be_deleted_without_deleting_approval_requests():
    """PROTECT on required_role/requested_by/decided_by/rule — approval
    history must survive role/user bookkeeping changes.
    """
    approve_permission = PermissionFactory(module="students", verb="approve")
    role_permission = RolePermissionFactory(permission=approve_permission, scope="all")
    ApprovalRuleFactory(
        module="students", action="status_change", required_role=role_permission.role
    )

    with pytest.raises(Exception):  # noqa: B017 - ProtectedError, avoiding an extra import
        Role.objects.filter(pk=role_permission.role.pk).delete()
