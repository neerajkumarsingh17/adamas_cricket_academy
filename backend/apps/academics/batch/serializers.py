from rest_framework import serializers

from .models import Batch, BatchEnrollment, Coach, TrainingSession


class CoachSerializer(serializers.ModelSerializer):
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = Coach
        fields = [
            "id",
            "person_name",
            "specialisation",
            "qualification",
            "experience_years",
            "is_available",
        ]
        read_only_fields = fields

    def get_person_name(self, obj) -> str:
        return f"{obj.staff.person.first_name} {obj.staff.person.last_name}".strip()


class BatchSerializer(serializers.ModelSerializer):
    coach = CoachSerializer(read_only=True)
    age_category_name = serializers.CharField(source="age_category.name", read_only=True)
    venue_name = serializers.CharField(source="venue.name", read_only=True)
    # GET /batches/ — "list with seats used vs capacity". Annotated on the
    # queryset (BatchViewSet.get_queryset), not recomputed per row here —
    # see that annotation's own comment for why.
    enrolled_count = serializers.IntegerField(read_only=True)
    seats_available = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = [
            "id",
            "name",
            "age_category",
            "age_category_name",
            "coach",
            "venue",
            "venue_name",
            "capacity",
            "weekdays",
            "start_time",
            "end_time",
            "monthly_fee",
            "residential_monthly_fee",
            "is_active",
            "enrolled_count",
            "seats_available",
        ]
        read_only_fields = fields

    def get_seats_available(self, obj) -> int:
        return obj.capacity - obj.enrolled_count


class BatchWriteSerializer(serializers.ModelSerializer):
    """POST /batches/ and PUT/PATCH /batches/{id}/ body — distinct from
    BatchSerializer, which is entirely read_only_fields (nested Coach,
    computed enrolled_count/seats_available) and so can't be reused here.
    """

    class Meta:
        model = Batch
        fields = [
            "name",
            "age_category",
            "coach",
            "venue",
            "capacity",
            "weekdays",
            "start_time",
            "end_time",
            "monthly_fee",
            "residential_monthly_fee",
            "is_active",
        ]

    def validate_weekdays(self, value: str) -> str:
        # Matches services.generate_sessions()'s own parsing contract
        # ({int(d) for d in batch.weekdays.split(",")}) — a malformed
        # value here wouldn't fail loudly there, just silently generate no
        # sessions for that day.
        tokens = [t.strip() for t in value.split(",") if t.strip()]
        if not tokens:
            raise serializers.ValidationError("At least one weekday is required.")
        for token in tokens:
            if not token.isdigit() or not (1 <= int(token) <= 7):
                raise serializers.ValidationError(
                    "Each weekday must be 1 (Monday) through 7 (Sunday)."
                )
        return value

    def validate(self, attrs):
        capacity = attrs.get("capacity", getattr(self.instance, "capacity", None))
        if self.instance is not None and capacity is not None:
            active_enrollments = self.instance.enrollments.filter(is_active=True).count()
            if capacity < active_enrollments:
                raise serializers.ValidationError(
                    {
                        "capacity": (
                            f"Cannot be less than {active_enrollments}, the current enrolment."
                        )
                    }
                )
        return attrs


class EnrolSerializer(serializers.Serializer):
    """POST /batches/{id}/enrol/ body."""

    student = serializers.UUIDField()
    from_date = serializers.DateField()


class TransferSerializer(serializers.Serializer):
    """POST /enrollments/{id}/transfer/ body."""

    to_batch = serializers.UUIDField()
    effective_date = serializers.DateField()


class BatchEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_code = serializers.CharField(source="student.student_code", read_only=True)
    batch_name = serializers.CharField(source="batch.name", read_only=True)
    # "each with... a fee status pill" — whether this month's recurring
    # fee is paid, per apps.finance.payment.services.is_current_month_paid
    # (the same check the payment ledger's own portal view uses; not a
    # second definition of "paid").
    fee_status = serializers.SerializerMethodField()

    class Meta:
        model = BatchEnrollment
        fields = [
            "id",
            "student",
            "student_name",
            "student_code",
            "batch",
            "batch_name",
            "from_date",
            "to_date",
            "is_active",
            "fee_status",
        ]
        read_only_fields = fields

    def get_student_name(self, obj) -> str:
        person = obj.student.person
        return f"{person.first_name} {person.last_name}".strip()

    def get_fee_status(self, obj) -> str:
        from apps.finance.payment.services import is_current_month_paid

        return "paid" if is_current_month_paid(obj.student.person) else "due"


class TrainingSessionSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source="batch.name", read_only=True)
    training_type_name = serializers.SerializerMethodField()

    class Meta:
        model = TrainingSession
        fields = [
            "id",
            "batch",
            "batch_name",
            "date",
            "start_time",
            "end_time",
            "coach",
            "training_type",
            "training_type_name",
            "objective",
            "is_conducted",
            "cancel_reason",
            "report",
        ]
        read_only_fields = fields

    def get_training_type_name(self, obj) -> str | None:
        return obj.training_type.name if obj.training_type_id else None


class CancelSessionSerializer(serializers.Serializer):
    """POST /sessions/{id}/cancel/ body."""

    reason = serializers.CharField()
