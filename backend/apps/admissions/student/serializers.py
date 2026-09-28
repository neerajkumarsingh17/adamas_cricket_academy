from rest_framework import serializers

from apps.people.models import BloodGroup, Gender, Relationship
from apps.people.serializers import PersonSerializer

from .models import Student, StudentProfile, StudentStatusHistory


class StudentSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    programme_name = serializers.CharField(source="programme.name", read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "student_code",
            "person",
            "admission",
            "admission_date",
            "programme",
            "programme_name",
            "residential",
            "status",
            "withdrawn_on",
            "completed_on",
            "created_at",
        ]
        read_only_fields = fields


class StudentWriteSerializer(serializers.ModelSerializer):
    """Phase 1 has no "cricket" fields yet (those are Phase 2+ — batch,
    attendance, performance) so there is nothing field-level to restrict a
    coach to editing per docs/02-api-spec.md's "a coach may edit cricket
    fields only" — flagged as a gap to revisit once those fields exist,
    rather than fabricated here. `programme` and `residential` are the only
    fields on `Student` itself that are ever legitimately re-editable after
    creation.
    """

    class Meta:
        model = Student
        fields = ["programme", "residential"]


class StudentStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_login_id = serializers.CharField(source="changed_by.login_id", read_only=True)

    class Meta:
        model = StudentStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "reason",
            "changed_by",
            "changed_by_login_id",
            "approval",
            "changed_at",
        ]
        read_only_fields = fields


class ChangeStatusSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(
        choices=list(Student._meta.get_field("status").choices or [])
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ReAdmissionSerializer(serializers.Serializer):
    person = serializers.UUIDField()
    programme = serializers.UUIDField()
    residential = serializers.BooleanField(required=False, default=False)


class ApproveAdmissionResponseSerializer(serializers.Serializer):
    student = StudentSerializer()


class StudentGuardianSerializer(serializers.Serializer):
    """Read shape for GET /students/{id}/guardians — the management
    counterpart to composite_profile()'s already-existing read-only
    "parent" tab block, same field shape so the frontend can share one
    row renderer between the two.
    """

    id = serializers.UUIDField()
    guardian_id = serializers.UUIDField()
    relationship = serializers.CharField()
    is_primary = serializers.BooleanField()
    is_emergency_contact = serializers.BooleanField()
    person = PersonSerializer()


class LinkGuardianSerializer(serializers.Serializer):
    """POST /students/{id}/guardians — either `person_id` (an existing
    Person, e.g. picked from /persons/search/) or the new-person fields,
    never both. services.link_guardian() trusts this split once validated
    here.
    """

    person_id = serializers.UUIDField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.ChoiceField(choices=Gender.choices, required=False)
    mobile = serializers.CharField(required=False)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    relationship = serializers.ChoiceField(choices=Relationship.choices)
    is_primary = serializers.BooleanField(required=False, default=False)
    is_emergency_contact = serializers.BooleanField(required=False, default=False)
    grant_portal_access = serializers.BooleanField(required=False, default=True)

    _NEW_PERSON_FIELDS = ("first_name", "last_name", "date_of_birth", "gender", "mobile")

    def validate(self, attrs):
        has_person_id = "person_id" in attrs
        given_new_person_fields = [f for f in self._NEW_PERSON_FIELDS if f in attrs]
        if has_person_id and given_new_person_fields:
            raise serializers.ValidationError(
                "Provide either person_id or a new guardian's details, not both."
            )
        if not has_person_id:
            missing = [f for f in self._NEW_PERSON_FIELDS if f not in attrs]
            if missing:
                raise serializers.ValidationError(
                    {field: "Required when not linking an existing person_id." for field in missing}
                )
        return attrs


class GrantLoginSerializer(serializers.Serializer):
    mobile = serializers.CharField(required=False, allow_blank=False)


class StudentProfileSerializer(serializers.ModelSerializer):
    """GET /students/{id}/profile/ — read shape. `blood_group`/`email`
    aren't `StudentProfile` fields (see its docstring — both already live
    on `Person`) so they're pulled in here as plain source= lookups
    instead, letting the client treat this as one flat profile object.
    """

    blood_group = serializers.CharField(source="student.person.blood_group", allow_blank=True)
    student_email = serializers.EmailField(source="student.person.email", allow_blank=True)
    percent_complete = serializers.SerializerMethodField()
    next_field = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            "blood_group",
            "student_email",
            "nationality",
            "aadhaar_number",
            "permanent_address",
            "occupation",
            "annual_income",
            "guardian_email",
            "second_guardian",
            "school_name",
            "board",
            "class_or_course",
            "medium_of_instruction",
            "academic_session",
            "playing_experience_years",
            "previous_academy",
            "achievements",
            "food_preference",
            "room_preference",
            "local_guardian_address",
            "allergies",
            "existing_conditions",
            "past_injuries",
            "family_doctor_contact",
            "percent_complete",
            "next_field",
        ]
        read_only_fields = [f for f in fields if f not in ("blood_group", "student_email")]

    def get_percent_complete(self, obj: StudentProfile) -> int:
        from . import services

        return services.profile_completeness(obj.student)["percent"]

    def get_next_field(self, obj: StudentProfile) -> str | None:
        from . import services

        return services.profile_completeness(obj.student)["next_field"]


class StudentProfileWriteSerializer(serializers.ModelSerializer):
    """PATCH /students/{id}/profile/ — the student/parent-editable subset
    only; `blood_group`/`student_email` write through to `Person` in the
    view (services.update_profile), not through this ModelSerializer's
    own `.save()`, since they aren't fields on this model at all.
    """

    blood_group = serializers.ChoiceField(
        choices=BloodGroup.choices, required=False, allow_blank=True
    )
    student_email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = StudentProfile
        fields = [
            "blood_group",
            "student_email",
            "nationality",
            "aadhaar_number",
            "permanent_address",
            "occupation",
            "annual_income",
            "guardian_email",
            "second_guardian",
            "school_name",
            "board",
            "class_or_course",
            "medium_of_instruction",
            "academic_session",
            "playing_experience_years",
            "previous_academy",
            "achievements",
            "food_preference",
            "room_preference",
            "local_guardian_address",
            "allergies",
            "existing_conditions",
            "past_injuries",
            "family_doctor_contact",
        ]


class StudentAccommodationSerializer(serializers.ModelSerializer):
    """GET /students/{id}/accommodation/ — read shape, own module
    (`residential`) from `students`/`student_profile` for the same reason
    StudentProfileViewSet's docstring gives: a Coach holds `students:view`
    but docs/03-rbac.md's Residential / Transport row gives Coach no
    access to this at all, so this can't be folded into StudentSerializer
    (visible to anyone who can see a Student at all) without leaking past
    that boundary.
    """

    building_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "residential", "building", "building_name", "room_number"]
        read_only_fields = fields

    def get_building_name(self, obj) -> str | None:
        return obj.building.name if obj.building_id else None


class StudentAccommodationWriteSerializer(serializers.Serializer):
    """PATCH /students/{id}/accommodation/ body — Hostel/Admin only
    (enforced by the `residential:edit` grant itself, not scope logic:
    Student/Parent hold own-scope `view` only on this module, so they
    never reach this action). Plain Serializer, not a ModelSerializer,
    since `building` needs to resolve from id to instance in the view
    (services.update_accommodation expects a real Building instance or
    None), same convention as apps.academics.attendance.serializers'
    TrainingSessionUpdateSerializer.
    """

    building = serializers.UUIDField(required=False, allow_null=True)
    room_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
