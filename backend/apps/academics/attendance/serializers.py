from rest_framework import serializers

from apps.people.serializers import PersonSerializer

from .models import Attendance, AttendanceCorrection


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "session", "student", "status", "remarks", "marked_by", "marked_at"]
        read_only_fields = fields


class AttendanceMarkSerializer(serializers.Serializer):
    """One entry of the POST /sessions/{id}/attendance/ bulk-marking body
    — the request is a JSON array of these.
    """

    student = serializers.UUIDField()
    status = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CancelSessionSerializer(serializers.Serializer):
    reason = serializers.CharField()


class TrainingSessionUpdateSerializer(serializers.Serializer):
    """POST /sessions/{id}/update-details/ body. Every field optional —
    only the ones provided are changed — same plain-Serializer-for-an-
    action-body convention as apps.academics.batch.serializers'
    EnrolSerializer/TransferSerializer, not a ModelSerializer, since
    coach/training_type need to resolve from id to instance in the view
    (services.update_session_details expects real model instances, same
    as every other write path in this app).
    """

    date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    coach = serializers.UUIDField(required=False)
    training_type = serializers.UUIDField(required=False, allow_null=True)
    objective = serializers.CharField(required=False, allow_blank=True)
    report = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field is required.")
        return attrs


class AttendanceMarkResultSerializer(serializers.Serializer):
    """One entry of the POST /sessions/{id}/attendance/ response — schema
    documentation for services.mark_bulk's plain-dict return shape.
    """

    student = serializers.UUIDField()
    ok = serializers.BooleanField()
    status = serializers.CharField(required=False)
    error = serializers.CharField(required=False)


class RosterMarkSerializer(serializers.Serializer):
    status = serializers.CharField()
    remarks = serializers.CharField()


class RosterEntrySerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    student_code = serializers.CharField()
    person = PersonSerializer()
    mark = RosterMarkSerializer(allow_null=True)


class RosterResponseSerializer(serializers.Serializer):
    """GET /sessions/{id}/roster/ response — schema documentation for
    services.roster's plain-dict return shape.
    """

    session_id = serializers.UUIDField()
    students = RosterEntrySerializer(many=True)


class RequestCorrectionSerializer(serializers.Serializer):
    """POST /attendance/{id}/corrections/ body — reason required."""

    to_status = serializers.CharField()
    reason = serializers.CharField()


class AttendanceCorrectionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_code = serializers.CharField(source="attendance.student.student_code", read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceCorrection
        fields = [
            "id",
            "attendance",
            "student_name",
            "student_code",
            "from_status",
            "to_status",
            "reason",
            "status",
            "requested_by",
            "requested_by_name",
            "approved_by",
            "approved_by_name",
            "approved_at",
        ]
        read_only_fields = fields

    def get_student_name(self, obj) -> str:
        person = obj.attendance.student.person
        return f"{person.first_name} {person.last_name}".strip()

    @staticmethod
    def _user_name(user) -> str:
        # `User.person` is null only for the system/IT admin account
        # (apps.iam.models.User's own docstring) — every real staff member
        # who can request/decide a correction has one.
        if user.person_id:
            return f"{user.person.first_name} {user.person.last_name}".strip()
        return user.login_id

    def get_requested_by_name(self, obj) -> str:
        return self._user_name(obj.requested_by)

    def get_approved_by_name(self, obj) -> str | None:
        return self._user_name(obj.approved_by) if obj.approved_by_id else None


class MonthlyReportRowSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    student_code = serializers.CharField()
    person = PersonSerializer()
    marks = serializers.DictField(child=serializers.CharField(allow_null=True))
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)


class MonthlyReportSessionSerializer(serializers.Serializer):
    date = serializers.DateField()
    is_conducted = serializers.BooleanField()


class MonthlyReportSerializer(serializers.Serializer):
    """GET /batches/{id}/attendance-report/ response — schema
    documentation for services.monthly_report's plain-dict return shape.
    """

    batch_id = serializers.UUIDField()
    batch_name = serializers.CharField()
    month = serializers.CharField()
    sessions = MonthlyReportSessionSerializer(many=True)
    rows = MonthlyReportRowSerializer(many=True)
