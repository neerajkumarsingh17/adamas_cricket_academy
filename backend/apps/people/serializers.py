from rest_framework import serializers

from .models import Person


class PersonSerializer(serializers.ModelSerializer):
    """Read shape (docs/06-conventions.md: one serializer per read shape —
    dedupe_key never appears here, it's an internal detail).
    """

    class Meta:
        model = Person
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "gender",
            "mobile",
            "email",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "pincode",
            "blood_group",
        ]
