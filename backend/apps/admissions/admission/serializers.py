from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.finance.payment.serializers import AdmissionPaymentSerializer
from apps.people.models import Person
from apps.people.serializers import PersonSerializer

from .models import Admission, AdmissionChecklistItem, AdmissionIntake


class AdmissionIntakeSerializer(serializers.ModelSerializer):
    """Read shape — includes the server-computed age_category, never
    accepted as input on the write serializer below.
    """

    age_category_name = serializers.CharField(source="age_category.name", read_only=True)
    season_name = serializers.CharField(source="season.name", read_only=True)

    class Meta:
        model = AdmissionIntake
        fields = [
            "id",
            "season",
            "season_name",
            "admission_category",
            "days_per_week",
            "preferred_slot",
            "full_name",
            "date_of_birth",
            "age_category",
            "age_category_name",
            "gender",
            "playing_role",
            "present_address",
            "city",
            "state",
            "pin_code",
            "student_mobile",
            "guardian_name",
            "guardian_relationship",
            "guardian_mobile",
            "guardian_date_of_birth",
            "guardian_gender",
            "emergency_contact",
            "local_guardian_name",
            "local_guardian_mobile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AdmissionIntakeWriteSerializer(serializers.ModelSerializer):
    """POST /admissions/direct/ (create) and PATCH /admissions/{id}/
    (autosave) — every field the desk actually captures, nothing more
    (docs/01-data-model.md section 5's 24 fields). `age_category` is
    absent: AdmissionIntake.save() computes it, this serializer must
    never be able to set it (docs: "never let the API accept it as
    input").
    """

    class Meta:
        model = AdmissionIntake
        fields = [
            "season",
            "admission_category",
            "days_per_week",
            "preferred_slot",
            "full_name",
            "date_of_birth",
            "gender",
            "playing_role",
            "present_address",
            "city",
            "state",
            "pin_code",
            "student_mobile",
            "guardian_name",
            "guardian_relationship",
            "guardian_mobile",
            "guardian_date_of_birth",
            "guardian_gender",
            "emergency_contact",
            "local_guardian_name",
            "local_guardian_mobile",
        ]


class AdmissionChecklistItemSerializer(serializers.ModelSerializer):
    document_type_name = serializers.CharField(source="document_type.name", read_only=True)
    rejection_reason = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionChecklistItem
        fields = [
            "id",
            "document_type",
            "document_type_name",
            "is_mandatory",
            "document",
            "status",
            "rejection_reason",
        ]
        read_only_fields = fields

    def get_rejection_reason(self, obj: AdmissionChecklistItem) -> str:
        # `rejection_reason` lives on the `Document` the checklist item
        # points at, not on the item itself — a `SerializerMethodField`
        # rather than `source="document.rejection_reason"` since `document`
        # is null until something's actually been uploaded.
        document = obj.document
        return document.rejection_reason if document is not None else ""


class AdmissionSerializer(serializers.ModelSerializer):
    # allow_null=True: person is nullable on the model (a source=DIRECT
    # admission has none until approve_admission() resolves one) — without
    # it here, drf-spectacular emits a non-nullable schema and every
    # generated frontend type lies about `.person` always being present.
    person = PersonSerializer(read_only=True, allow_null=True)
    checklist_items = AdmissionChecklistItemSerializer(many=True, read_only=True)
    programme_name = serializers.CharField(source="programme.name", read_only=True)
    portal_enabled = serializers.SerializerMethodField()
    intake = serializers.SerializerMethodField()
    fee_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    fee_total_in_words = serializers.CharField(read_only=True)
    registration_no = serializers.CharField(source="application_no", read_only=True)
    next_actions = serializers.SerializerMethodField()
    direct_payment = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = [
            "id",
            "application_no",
            "registration_no",
            "source",
            "person",
            "enquiry",
            "trial_registration",
            "programme",
            "programme_name",
            "residential",
            "step",
            "direct_admission_reason",
            "fee_payment_reference",
            "fee_payment_status",
            "fee_payment_method",
            "fee_amount",
            "fee_total",
            "fee_total_in_words",
            "approved_by",
            "approved_at",
            "rejected_reason",
            "cancelled_reason",
            "checklist_items",
            "portal_enabled",
            "intake",
            "direct_payment",
            "next_actions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(AdmissionIntakeSerializer(allow_null=True))
    def get_intake(self, obj: Admission) -> dict | None:
        intake = getattr(obj, "intake", None)
        return AdmissionIntakeSerializer(intake).data if intake is not None else None

    @extend_schema_field(AdmissionPaymentSerializer(allow_null=True))
    def get_direct_payment(self, obj: Admission) -> dict | None:
        payment = getattr(obj, "payment", None)
        return AdmissionPaymentSerializer(payment).data if payment is not None else None

    def get_next_actions(self, obj: Admission) -> list[str]:
        from . import services

        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        return services.next_actions_for(obj, user)

    def get_portal_enabled(self, obj: Admission) -> bool:
        # No dedicated column for this — `services.enable_portal_access`
        # provisions a `User` for `obj.person` the same way `apps.
        # admissions.student.services.grant_student_login` does post-
        # approval, so "does one already exist" is the same signal
        # `get_or_create_user_for_person` itself uses, not a new concept.
        from apps.iam.models import User

        if obj.person_id is None:
            return False
        return User.objects.filter(person_id=obj.person_id).exists()


class AdmissionWriteSerializer(serializers.ModelSerializer):
    """PATCH /admissions/{id} — docs/02-api-spec.md lists this as a real
    `admission/edit` endpoint distinct from `/advance`. `step` is
    deliberately absent: it must only ever change through
    `services.advance`/`approve_admission`/`reject_admission`, never a
    direct field write (CLAUDE.md rule 5).
    """

    class Meta:
        model = Admission
        fields = ["residential"]


class OpenAdmissionSerializer(serializers.Serializer):
    trial_registration = serializers.UUIDField()
    programme = serializers.UUIDField()
    residential = serializers.BooleanField(required=False, default=False)


class DirectAdmissionSerializer(serializers.Serializer):
    """Administration fills the candidate's own info here — there is no
    prior Enquiry/TrialRegistration behind a direct admission, so unlike
    `OpenAdmissionSerializer` this can't take a `person` id. `services.
    open_direct_admission` runs this through `resolve_person()` (CLAUDE.md
    rule 1) rather than blindly creating a `Person`.
    """

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=list(Person._meta.get_field("gender").choices or []))
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    address_line1 = serializers.CharField(required=False, allow_blank=True, default="")
    city = serializers.CharField(required=False, allow_blank=True, default="")
    state = serializers.CharField(required=False, allow_blank=True, default="")
    pincode = serializers.CharField(required=False, allow_blank=True, default="")
    programme = serializers.UUIDField()
    reason = serializers.CharField()
    residential = serializers.BooleanField(required=False, default=False)


class AdvanceSerializer(serializers.Serializer):
    to_step = serializers.ChoiceField(choices=list(Admission._meta.get_field("step").choices or []))
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class RecordPaymentSerializer(serializers.Serializer):
    """The Phase 1 fee stub (services.record_payment's own docstring) —
    Admission.fee_amount itself carries no MinValueValidator (it's a Phase
    3 rebuild away from a real fee engine), so unlike every other money
    field in this codebase a negative value here isn't even caught by a
    model full_clean() downstream — it would just save silently. Guarded
    here instead, same floor as apps.finance.payment's amount fields.
    """

    reference = serializers.CharField(required=False, allow_blank=True, default="")
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    payment_method = serializers.ChoiceField(
        choices=list(Admission._meta.get_field("fee_payment_method").choices or []),
        required=False,
        allow_blank=True,
        default="",
    )
    waiver_reason = serializers.CharField(required=False, allow_blank=True, default="")
    mark_unpaid = serializers.BooleanField(required=False, default=False)


class RejectAdmissionSerializer(serializers.Serializer):
    reason = serializers.CharField()


class FeeLineInputSerializer(serializers.Serializer):
    fee_head = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)


class FeeLinesWriteSerializer(serializers.Serializer):
    """PUT /admissions/{id}/fees/ — replaces the fee lines wholesale, one
    row per FeeHead the bootstrap payload listed.
    """

    lines = FeeLineInputSerializer(many=True)


class ConsentDecisionInputSerializer(serializers.Serializer):
    consent_type = serializers.UUIDField()
    granted = serializers.BooleanField()


class ConsentDecisionsWriteSerializer(serializers.Serializer):
    """POST /admissions/{id}/consents/ — bulk upsert, one row per
    ConsentType the bootstrap payload listed. `declared_by_name` is the
    guardian's typed name — the signature, per docs: "the typed name plus
    the audit row is the signature."
    """

    decisions = ConsentDecisionInputSerializer(many=True)
    declared_by_name = serializers.CharField(max_length=120)


class RecordDirectPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.finance.payment.models import AdmissionPayment

        model = AdmissionPayment
        fields = ["payment_mode", "payment_date"]


class VerifyPaymentSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    verification_note = serializers.CharField(required=False, allow_blank=True, default="")


class CancelAdmissionSerializer(serializers.Serializer):
    reason = serializers.CharField()
