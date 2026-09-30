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


class PersonLookupResultSerializer(PersonSerializer):
    """GET /persons/lookup/ response — PersonSerializer plus, when the
    person is currently linked to a Student, that student's code.

    Why: this endpoint's own search (mobile/name substring, no fuzzy
    dedup warning the way PersonSearchView's admission-intake duplicate
    check has) can easily surface several people with the same name — a
    same-named sibling, or SOP §78's "one Person, one profile" broken in
    practice by an accidental duplicate Person row for the same human.
    Name + mobile alone doesn't tell those apart; the student code does,
    and is exactly what stops a coaching fee being recorded against the
    wrong "Neeraj Kumar" (confirmed the hard way against production data).

    Local import: apps.people sits before apps.admissions.student in
    docs/00-project-structure.md's dependency chain (people imports only
    core) — same narrow, function-scoped exception apps.finance.payment.
    views.CurrentFeeView already uses to read across that same boundary.
    """

    student_code = serializers.SerializerMethodField()

    class Meta(PersonSerializer.Meta):
        fields = [*PersonSerializer.Meta.fields, "student_code"]

    def get_student_code(self, obj) -> str | None:
        from apps.admissions.student.models import Student

        student = (
            Student.objects.filter(person=obj).order_by("-admission_date").first()
        )
        return student.student_code if student else None
