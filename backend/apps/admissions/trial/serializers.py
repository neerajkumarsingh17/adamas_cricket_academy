from rest_framework import serializers

from apps.people.serializers import PersonSerializer

from .models import (
    TrialAssessment,
    TrialAssessmentScore,
    TrialRegistration,
    TrialResult,
    TrialSlot,
)


class TrialSlotSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source="venue.name", read_only=True)
    age_category_name = serializers.CharField(source="age_category.name", read_only=True)
    remaining_capacity = serializers.SerializerMethodField()

    class Meta:
        model = TrialSlot
        fields = [
            "id",
            "date",
            "venue",
            "venue_name",
            "reporting_time",
            "age_category",
            "age_category_name",
            "capacity",
            "booked_count",
            "remaining_capacity",
        ]
        read_only_fields = ["id", "booked_count"]

    def get_remaining_capacity(self, obj: TrialSlot) -> int:
        return max(obj.capacity - obj.booked_count, 0)


class TrialSlotBookSerializer(serializers.Serializer):
    enquiry_id = serializers.UUIDField()


class TrialAssessmentScoreSerializer(serializers.ModelSerializer):
    criterion_code = serializers.CharField(source="criterion.code", read_only=True)
    criterion_name = serializers.CharField(source="criterion.name", read_only=True)

    class Meta:
        model = TrialAssessmentScore
        fields = ["criterion", "criterion_code", "criterion_name", "score"]


class TrialAssessmentSerializer(serializers.ModelSerializer):
    scores = TrialAssessmentScoreSerializer(many=True, read_only=True)
    assessed_by_name = serializers.CharField(source="assessed_by.person", read_only=True)

    class Meta:
        model = TrialAssessment
        fields = [
            "id",
            "assessed_by",
            "assessed_by_name",
            "assessed_at",
            "overall_remarks",
            "is_locked",
            "scores",
        ]
        read_only_fields = fields


class SubmitAssessmentScoreSerializer(serializers.Serializer):
    criterion = serializers.UUIDField()
    score = serializers.DecimalField(max_digits=5, decimal_places=2)


class SubmitAssessmentSerializer(serializers.Serializer):
    overall_remarks = serializers.CharField(required=False, allow_blank=True, default="")
    scores = SubmitAssessmentScoreSerializer(many=True)


class TrialResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrialResult
        fields = [
            "id",
            "registration",
            "outcome",
            "declared_by",
            "declared_at",
            "review_on",
            "notes",
        ]
        read_only_fields = fields


class DeclareResultSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(
        choices=list(TrialResult._meta.get_field("outcome").choices or [])
    )
    review_on = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class TrialRegistrationSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    slot = TrialSlotSerializer(read_only=True)
    assessment = TrialAssessmentSerializer(read_only=True)
    result = TrialResultSerializer(read_only=True)
    enquiry_student_name = serializers.CharField(source="enquiry.student_name", read_only=True)
    admission_id = serializers.SerializerMethodField()

    class Meta:
        model = TrialRegistration
        fields = [
            "id",
            "trial_id",
            "enquiry",
            "enquiry_student_name",
            "person",
            "slot",
            "trial_fee",
            "payment_status",
            "payment_reference",
            "attended",
            "assessment",
            "result",
            "admission_id",
        ]
        read_only_fields = fields

    def get_admission_id(self, obj) -> str | None:
        """Lets the frontend show "Open Admission" vs "View Admission" on a
        selected trial's row (docs/02-api-spec.md's own Admissions section
        never names this field — added so the UI has something to open an
        admission *from*, which nothing exposed before).
        """
        admission = obj.admissions.first()
        return str(admission.id) if admission else None


class AttendanceSerializer(serializers.Serializer):
    attended = serializers.BooleanField()


class BulkNotifySerializer(serializers.Serializer):
    registration_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
