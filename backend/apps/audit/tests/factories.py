import factory
from factory.django import DjangoModelFactory

from apps.audit.models import AuditAction, AuditLog
from apps.iam.tests.factories import UserFactory


class AuditLogFactory(DjangoModelFactory):
    class Meta:
        model = AuditLog

    actor = factory.SubFactory(UserFactory)
    action = AuditAction.UPDATE
    model_label = "people.Person"
    object_id = factory.Sequence(lambda n: f"object-{n}")
    changes = factory.LazyFunction(lambda: {"first_name": {"from": "A", "to": "B"}})
