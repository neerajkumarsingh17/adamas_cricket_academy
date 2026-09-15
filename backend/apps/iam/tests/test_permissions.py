import datetime

import pytest

from .factories import PermissionFactory, RolePermissionFactory, UserFactory, UserRoleFactory


@pytest.mark.django_db
def test_has_perm_for_true_when_role_grants_it():
    permission = PermissionFactory(module="admission", verb="approve")
    role_permission = RolePermissionFactory(permission=permission)
    user = UserFactory()
    UserRoleFactory(user=user, role=role_permission.role)

    assert user.has_perm_for("admission", "approve") is True


@pytest.mark.django_db
def test_has_perm_for_false_when_no_role_grants_it():
    user = UserFactory()

    assert user.has_perm_for("admission", "approve") is False


@pytest.mark.django_db
def test_has_perm_for_false_for_wrong_verb():
    permission = PermissionFactory(module="admission", verb="view")
    role_permission = RolePermissionFactory(permission=permission)
    user = UserFactory()
    UserRoleFactory(user=user, role=role_permission.role)

    assert user.has_perm_for("admission", "approve") is False


@pytest.mark.django_db
def test_has_perm_for_ignores_expired_role_assignment():
    permission = PermissionFactory(module="admission", verb="approve")
    role_permission = RolePermissionFactory(permission=permission)
    user = UserFactory()
    UserRoleFactory(
        user=user,
        role=role_permission.role,
        valid_from=datetime.date(2020, 1, 1),
        valid_to=datetime.date(2020, 12, 31),
    )

    assert user.has_perm_for("admission", "approve") is False


@pytest.mark.django_db
def test_has_perm_for_ignores_not_yet_valid_role_assignment():
    permission = PermissionFactory(module="admission", verb="approve")
    role_permission = RolePermissionFactory(permission=permission)
    user = UserFactory()
    UserRoleFactory(
        user=user,
        role=role_permission.role,
        valid_from=datetime.date(2999, 1, 1),
        valid_to=None,
    )

    assert user.has_perm_for("admission", "approve") is False


@pytest.mark.django_db
def test_has_perm_for_unions_permissions_across_multiple_roles():
    view_permission = PermissionFactory(module="admission", verb="view")
    approve_permission = PermissionFactory(module="admission", verb="approve")
    view_grant = RolePermissionFactory(permission=view_permission)
    approve_grant = RolePermissionFactory(permission=approve_permission)

    user = UserFactory()
    UserRoleFactory(user=user, role=view_grant.role)
    UserRoleFactory(user=user, role=approve_grant.role)

    assert user.has_perm_for("admission", "view") is True
    assert user.has_perm_for("admission", "approve") is True


@pytest.mark.django_db
def test_has_perm_for_result_is_cached_on_the_instance():
    """ "Cached per request" — a UserRole added after the first check must
    not change the result on the same user instance.
    """
    permission = PermissionFactory(module="admission", verb="approve")
    role_permission = RolePermissionFactory(permission=permission)
    user = UserFactory()

    assert user.has_perm_for("admission", "approve") is False

    UserRoleFactory(user=user, role=role_permission.role)

    assert user.has_perm_for("admission", "approve") is False

    fresh = type(user).objects.get(pk=user.pk)
    assert fresh.has_perm_for("admission", "approve") is True


@pytest.mark.django_db
def test_scope_for_returns_none_when_not_granted():
    user = UserFactory()

    assert user.scope_for("admission", "approve") is None


@pytest.mark.django_db
def test_scope_for_returns_the_granted_scope():
    permission = PermissionFactory(module="students", verb="view")
    role_permission = RolePermissionFactory(permission=permission, scope="own")
    user = UserFactory()
    UserRoleFactory(user=user, role=role_permission.role)

    assert user.scope_for("students", "view") == "own"


@pytest.mark.django_db
def test_scope_for_widest_scope_wins_when_roles_disagree():
    """docs/03-rbac.md: "the widest scope among them" — a user holding one
    role scoped "own" and another scoped "all" for the same permission
    gets "all", regardless of which role's grant is resolved first.
    """
    permission = PermissionFactory(module="students", verb="view")
    own_grant = RolePermissionFactory(permission=permission, scope="own")
    all_grant = RolePermissionFactory(permission=permission, scope="all")

    user = UserFactory()
    UserRoleFactory(user=user, role=own_grant.role)
    UserRoleFactory(user=user, role=all_grant.role)

    assert user.scope_for("students", "view") == "all"
