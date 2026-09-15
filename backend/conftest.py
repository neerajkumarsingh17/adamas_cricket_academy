import pytest


@pytest.fixture(scope="session")
def seeded_roles(django_db_setup, django_db_blocker):
    """Seeds the 16 roles/RBAC matrix once per test database, not once per
    session unconditionally — if roles already exist (e.g. a `--reuse-db`
    run against a database a RolePermission row was deliberately deleted
    from, to verify a test actually catches it), leave it alone rather
    than silently re-seeding over the top and masking the deletion.
    """
    from django.core.management import call_command

    from apps.iam.models import Role

    with django_db_blocker.unblock():
        if not Role.objects.exists():
            call_command("seed_roles")
