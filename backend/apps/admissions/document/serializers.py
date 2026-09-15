from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    document_type_name = serializers.CharField(source="document_type.name", read_only=True)
    owner_type = serializers.CharField(source="owner_content_type.model", read_only=True)
    owner_label = serializers.SerializerMethodField()
    admission_id = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "document_type",
            "document_type_name",
            "owner_type",
            "owner_object_id",
            "owner_label",
            "admission_id",
            "original_filename",
            "mime_type",
            "size_bytes",
            "status",
            "verified_by",
            "verified_at",
            "rejection_reason",
            "expires_on",
            "created_at",
        ]
        read_only_fields = fields

    def get_owner_label(self, obj) -> str:
        """The verification queue (docs/02-api-spec.md's `documents` list)
        previously showed only `owner_object_id` — a raw UUID, useless for
        telling two candidates' paperwork apart once more than one is in
        the pipeline at once. Every owner type resolves to a `Person`
        one way or another; this is that name, human-readable.
        """
        owner = obj.owner
        if owner is None:
            return "—"
        is_person = obj.owner_content_type.model == "person"
        person = owner if is_person else getattr(owner, "person", None)
        if person is None:
            # A source=DIRECT admission has no Person until approval
            # (apps.admissions.student.services.approve_admission), but
            # document verification happens before that — fall back to
            # the name captured at intake so the queue isn't blank for
            # every in-progress direct admission.
            if obj.owner_content_type.model == "admission":
                intake = getattr(owner, "intake", None)
                if intake is not None:
                    return f"{intake.full_name} — {owner.application_no}"
            return "—"
        name = f"{person.first_name} {person.last_name}".strip()
        if obj.owner_content_type.model == "admission":
            return f"{name} — {owner.application_no}"
        if obj.owner_content_type.model == "student":
            return f"{name} — {owner.student_code}"
        return name

    def get_admission_id(self, obj) -> str | None:
        """Lets the queue link straight to the one screen that also has
        the upload/verify/fee actions together
        (apps.admissions.admission.pages.AdmissionDetailPage) — only
        meaningful when the document's owner actually is an admission.
        """
        if obj.owner_content_type.model == "admission":
            return str(obj.owner_object_id)
        return None


class PresignRequestSerializer(serializers.Serializer):
    document_type = serializers.UUIDField()
    owner_type = serializers.ChoiceField(choices=["person", "student", "staff", "admission"])
    owner_id = serializers.UUIDField()
    filename = serializers.CharField()
    mime = serializers.CharField()


class PresignResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    s3_key = serializers.CharField()


class ConfirmRequestSerializer(serializers.Serializer):
    document_type = serializers.UUIDField()
    owner_type = serializers.ChoiceField(choices=["person", "student", "staff", "admission"])
    owner_id = serializers.UUIDField()
    s3_key = serializers.CharField()
    filename = serializers.CharField()
    mime = serializers.CharField()


class RejectDocumentSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField()


class DownloadUrlSerializer(serializers.Serializer):
    download_url = serializers.URLField()
