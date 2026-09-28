from rest_framework import serializers

from .models import (
    AgeCategory,
    ApprovalRequest,
    AssessmentCriterion,
    Building,
    ConsentType,
    DocumentType,
    EnquirySource,
    FeeHead,
    PaymentType,
    Programme,
    Season,
    TrainingType,
    Venue,
)


class DashboardTileSerializer(serializers.Serializer):
    key = serializers.CharField()
    # serializers.Field itself has a `label` attribute (its own form
    # display name) — this shadows it with a real field, which is fine at
    # runtime but needs the type: ignore for the stub collision.
    label = serializers.CharField()  # type: ignore[assignment]
    # Heterogeneous by design (a count, a percentage, an ISO date string, or
    # null) — the dashboard's own docstring gives the real shape per tile.
    value = serializers.JSONField()
    meta = serializers.JSONField(allow_null=True)
    urgent = serializers.BooleanField()


class DashboardCardSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_null=True)
    type = serializers.ChoiceField(choices=["list", "table", "bars", "audit"])
    # Item shape depends on `type` (list: {key,label,detail}; table: arbitrary
    # column dict; bars: {label,value}) — left as JSON here for the same
    # reason as DashboardTileSerializer.value.
    items = serializers.ListField(child=serializers.JSONField())


class DashboardSerializer(serializers.Serializer):
    """GET /api/v1/dashboards/me — apps.core.services.dashboards.build_dashboard().

    `build_dashboard()` returns a plain dict passed straight to `Response()`
    (this serializer is schema-only, per DashboardMeView's docstring), so
    `student_id` simply isn't a key at all for any role but `student` —
    `allow_null=True, required=False` here is about the generated schema
    letting the frontend check for it, not about runtime validation.
    """

    role = serializers.CharField()
    tiles = DashboardTileSerializer(many=True)
    cards = DashboardCardSerializer(many=True)
    student_id = serializers.UUIDField(allow_null=True, required=False)


class ApprovalRequestSerializer(serializers.ModelSerializer):
    module = serializers.CharField(source="rule.module", read_only=True)
    action = serializers.CharField(source="rule.action", read_only=True)
    subject_type = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "module",
            "action",
            "subject_type",
            "object_id",
            "requested_by",
            "status",
            "decided_by",
            "decided_at",
            "reason",
            "created_at",
        ]
        read_only_fields = fields


class ApprovalDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
        fields = ["id", "code", "name", "description", "is_active"]


class AgeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeCategory
        fields = ["id", "code", "name", "min_age", "max_age", "as_on_date_rule", "is_active"]


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "code", "name", "address", "is_active"]


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ["id", "code", "name", "address", "is_active"]


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ["id", "code", "name", "start_date", "end_date", "age_cutoff_date", "is_active"]


class EnquirySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnquirySource
        fields = ["id", "code", "name", "is_active"]


class TrainingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingType
        fields = ["id", "code", "name", "is_active"]


class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = [
            "id",
            "code",
            "name",
            "is_mandatory_default",
            "has_expiry",
            "applies_to",
            "required_stage",
        ]


class FeeHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeHead
        fields = ["id", "code", "label", "is_mandatory", "display_order", "applies_to", "is_active"]


class PaymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentType
        fields = ["id", "code", "label", "is_recurring", "display_order", "is_active"]


class ConsentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentType
        fields = ["id", "code", "label", "body_text", "version", "is_mandatory", "is_active"]


class AssessmentCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentCriterion
        fields = ["id", "code", "name", "group", "scale_min", "scale_max", "weight", "is_active"]
