import datetime

import factory
from factory.django import DjangoModelFactory

from apps.iam.models import Permission, Role, RolePermission, Scope, User, UserRole, Verb


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    login_id = factory.Sequence(lambda n: f"user{n}@example.com")
    person = None
    is_active = True
    is_staff = False


class RoleFactory(DjangoModelFactory):
    class Meta:
        model = Role

    code = factory.Sequence(lambda n: f"role_{n}")
    name = factory.Sequence(lambda n: f"Role {n}")
    is_system = False


class PermissionFactory(DjangoModelFactory):
    class Meta:
        model = Permission
        # get_or_create on (module, verb): many tests call this with a
        # real seeded module name ("admission", "students", "enquiry", ...)
        # rather than the default sequence. `seeded_roles` (session-scoped,
        # seeds outside any per-test transaction) may have already created
        # that exact row by the time such a test runs in the same session
        # — without this, a plain .create() hits
        # unique_permission_module_verb depending on test ordering.
        django_get_or_create = ("module", "verb")

    module = factory.Sequence(lambda n: f"module_{n}")
    verb = Verb.VIEW


class RolePermissionFactory(DjangoModelFactory):
    class Meta:
        model = RolePermission

    role = factory.SubFactory(RoleFactory)
    permission = factory.SubFactory(PermissionFactory)
    scope = Scope.ALL


class UserRoleFactory(DjangoModelFactory):
    class Meta:
        model = UserRole

    user = factory.SubFactory(UserFactory)
    role = factory.SubFactory(RoleFactory)
    valid_from = datetime.date(2020, 1, 1)
    valid_to = None
