import datetime

import pytest
from django.core.management import call_command

from apps.iam.models import Permission, Role, RolePermission, User, UserRole


@pytest.mark.django_db
def test_seed_roles_creates_16_roles():
    call_command("seed_roles")

    assert Role.objects.count() == 16
    assert set(Role.objects.values_list("code", flat=True)) == {
        "academy_management",
        "academy_head",
        "sports_ops",
        "administration",
        "accounts",
        "head_coach",
        "coach",
        "strength_conditioning",
        "medical_team",
        "physiotherapist",
        "hostel",
        "transport",
        "athlete_management",
        "student",
        "parent",
        "it_admin",
    }


@pytest.mark.django_db
def test_seed_roles_is_idempotent():
    call_command("seed_roles")
    role_count = Role.objects.count()
    permission_count = Permission.objects.count()
    grant_count = RolePermission.objects.count()

    call_command("seed_roles")

    assert Role.objects.count() == role_count
    assert Permission.objects.count() == permission_count
    assert RolePermission.objects.count() == grant_count


@pytest.mark.django_db
def test_academy_head_can_approve_admission_but_coach_cannot():
    """The Check: has_perm_for("admission", "approve") is True for
    academy_head and False for coach — read from database rows seeded by
    seed_roles, not from any hardcoded role name.
    """
    call_command("seed_roles")

    academy_head = User.objects.create_user(login_id="head@example.com", password="x")
    UserRole.objects.create(
        user=academy_head,
        role=Role.objects.get(code="academy_head"),
        valid_from=datetime.date(2020, 1, 1),
    )

    coach = User.objects.create_user(login_id="coach@example.com", password="x")
    UserRole.objects.create(
        user=coach,
        role=Role.objects.get(code="coach"),
        valid_from=datetime.date(2020, 1, 1),
    )

    assert academy_head.has_perm_for("admission", "approve") is True
    assert coach.has_perm_for("admission", "approve") is False
