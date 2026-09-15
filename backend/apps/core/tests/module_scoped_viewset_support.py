"""A minimal ModuleScopedViewSet subclass for exercising the base class's
own generic mechanics in isolation. Person just stands in for whatever
model a real module="enquiry" ViewSet would eventually serialize — the
point under test is ModuleScopedViewSet, not this fixture.
"""

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.views import ModuleScopedViewSet
from apps.people.models import Person


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            "id",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "mobile",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "pincode",
        ]


class EnquiryStandInViewSet(ModuleScopedViewSet):
    module = "enquiry"
    serializer_class = PersonSerializer
    queryset = Person.objects.all()

    def filter_to_own(self, queryset):
        return queryset.filter(user_accounts=self.request.user)

    @action(detail=True, methods=["post"], verb="approve")
    def approve(self, request, pk=None):
        return Response({"approved": True})
