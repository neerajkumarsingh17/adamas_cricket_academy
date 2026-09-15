from rest_framework import serializers

from apps.people.serializers import PersonSerializer

from .models import Enquiry, EnquiryFollowUp


class EnquiryReadSerializer(serializers.ModelSerializer):
    """docs/06-conventions.md: one serializer per read shape. `person` is
    nested here (read-only) because a caller viewing an enquiry wants to
    see who it resolved to, but never sets it directly — that only ever
    happens through `services.create_enquiry`/`convert_to_trial`.
    """

    person = PersonSerializer(read_only=True)
    source_code = serializers.CharField(source="source.code", read_only=True)
    owner_login_id = serializers.CharField(source="owner.login_id", read_only=True, default=None)

    class Meta:
        model = Enquiry
        fields = [
            "id",
            "enquiry_no",
            "person",
            "student_name",
            "date_of_birth",
            "gender",
            "guardian_name",
            "guardian_mobile",
            "guardian_email",
            "address",
            "school",
            "class_grade",
            "cricket_experience",
            "playing_role",
            "batting_style",
            "bowling_style",
            "current_club",
            "residential_required",
            "source",
            "source_code",
            "referred_by",
            "status",
            "remarks",
            "owner",
            "owner_login_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EnquiryWriteSerializer(serializers.ModelSerializer):
    """`enquiry_no` and `person` are never client-writable — minted/resolved
    by `services.create_enquiry` — so they're absent here entirely rather
    than merely read-only, per docs/06-conventions.md's "write serializer
    is not a read serializer" rule.
    """

    class Meta:
        model = Enquiry
        fields = [
            "student_name",
            "date_of_birth",
            "gender",
            "guardian_name",
            "guardian_mobile",
            "guardian_email",
            "address",
            "school",
            "class_grade",
            "cricket_experience",
            "playing_role",
            "batting_style",
            "bowling_style",
            "current_club",
            "residential_required",
            "source",
            "referred_by",
            "status",
            "remarks",
            "owner",
        ]
        extra_kwargs = {"status": {"required": False}}


class EnquiryFollowUpSerializer(serializers.ModelSerializer):
    created_by_login_id = serializers.CharField(
        source="created_by.login_id", read_only=True, default=None
    )

    class Meta:
        model = EnquiryFollowUp
        fields = [
            "id",
            "enquiry",
            "contacted_on",
            "mode",
            "notes",
            "next_action_on",
            "created_by",
            "created_by_login_id",
        ]
        read_only_fields = ["id", "enquiry", "created_by", "created_by_login_id"]


class ConvertToTrialSerializer(serializers.Serializer):
    slot_id = serializers.UUIDField()


class DuplicateCandidateSerializer(serializers.Serializer):
    exact = PersonSerializer(many=True)
    fuzzy = PersonSerializer(many=True)


class ConversionAnalyticsRowSerializer(serializers.Serializer):
    # Shadows DRF Field's own `source` attribute (a str|None used for
    # source-mapping) by name only — this is a genuine response field
    # named "source" (the enquiry source code), not a source mapping, and
    # renaming it would change the wire format for no reason.
    source = serializers.CharField()  # type: ignore[assignment]
    source_name = serializers.CharField()
    enquiries = serializers.IntegerField()
    trials = serializers.IntegerField()
    admissions = serializers.IntegerField()
    enquiry_to_trial_rate = serializers.FloatField()
    trial_to_admission_rate = serializers.FloatField()
