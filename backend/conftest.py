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


@pytest.fixture
def fake_gateway(settings):
    """Online payments against apps.finance.payment.tests.fake_gateway
    instead of a real provider; yields the FakeGateway class so a test can
    set what the "gateway" reports."""
    from unittest import mock

    from apps.finance.payment.gateways import GATEWAYS
    from apps.finance.payment.tests.fake_gateway import FakeGateway

    settings.PAYMENT_GATEWAY = "fake"
    FakeGateway.statuses = {}
    FakeGateway.cancelled = []
    with mock.patch.dict(GATEWAYS, {"fake": FakeGateway}):
        yield FakeGateway
