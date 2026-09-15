import factory
from factory.django import DjangoModelFactory

from apps.admissions.parent.models import ParentPortalAccess
from apps.people.tests.factories import GuardianFactory


class ParentPortalAccessFactory(DjangoModelFactory):
    class Meta:
        model = ParentPortalAccess

    guardian = factory.SubFactory(GuardianFactory)
