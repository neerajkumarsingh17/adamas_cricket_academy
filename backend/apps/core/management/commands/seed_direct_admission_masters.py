"""Master data the direct-admission wizard reads at runtime — nothing here
is hardcoded into the form (docs/01-data-model.md section 4). Idempotent
via update_or_create(), same pattern as seed_master_data.py.

Document types reuse the existing admission-checklist codes wherever one
already matches (birth_certificate, aadhaar_card, medical_certificate,
address_proof, school_id are hardcoded by code in seed_demo.py and the
trial-based admission tests — renaming them would break those) and only
adds `required_stage`, which is new and additive. Only genuinely new
documents (passport photograph, previous cricket records) get new codes.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import ConsentType, DocumentType, FeeHead, PaymentType

FEE_HEADS = [
    # (code, label, is_mandatory, display_order). The "registration" code
    # is kept as-is so existing AdmissionFeeLine rows stay linked; only
    # the label shown at the desk is "Admission Fee".
    ("registration", "Admission Fee", True, 1),
    ("other", "Other", False, 3),
]

# Codes retired from the admission desk. Deactivated rather than deleted:
# historical AdmissionFeeLine rows PROTECT-reference them. Coaching is
# collected monthly through the Payment ledger (PaymentType
# "monthly_coaching_fee"), not at admission.
RETIRED_FEE_HEADS = ["coaching"]

# (code, label, is_recurring, display_order) — the unified Payment ledger's
# type master. Every other category (kit, tournament, hostel...) is added
# from admin only, never here.
PAYMENT_TYPES = [
    ("admission_fee", "Admission Fee", False, 1),
    ("monthly_coaching_fee", "Monthly Coaching Fee", True, 2),
]

CONSENT_TYPES = [
    # (code, label, body_text, version, is_mandatory)
    (
        "code_of_conduct",
        "Code of conduct and attendance policy",
        "I agree to abide by the academy's code of conduct and attendance policy.",
        "1.0",
        True,
    ),
    (
        "fee_policy",
        "Fee policy",
        "Fees paid are non-refundable and non-transferable.",
        "1.0",
        True,
    ),
    (
        "liability_waiver",
        "Liability waiver and injury responsibility",
        "I understand cricket carries a risk of injury and accept responsibility accordingly.",
        "1.0",
        True,
    ),
    (
        "medical_emergency",
        "Emergency medical consent",
        "I authorise the academy to arrange emergency medical treatment if I cannot be reached.",
        "1.0",
        True,
    ),
    (
        "media_use",
        "Media consent",
        "I consent to photographs/video of my child being used in academy promotional material.",
        "1.0",
        False,
    ),
]

# (code, required_stage) — name/is_mandatory_default/has_expiry/applies_to
# are left untouched on every existing row.
DOCUMENT_STAGE_UPDATES = [
    ("birth_certificate", "at_admission"),
    ("aadhaar_card", "at_admission"),
    ("medical_certificate", "before_first_session"),
    ("address_proof", "profile_completion"),
    ("school_id", "profile_completion"),
]

NEW_DOCUMENT_TYPES = [
    # (code, name, is_mandatory_default, has_expiry, required_stage, applies_to)
    ("passport_photo", "Passport Photograph", True, False, "at_admission", "admission"),
    (
        "previous_cricket_records",
        "Previous Cricket Records",
        False,
        False,
        "profile_completion",
        "admission",
    ),
    # student-scoped, not admission — this one is only ever chased once a
    # Student row exists (Prompt G's profile completion), never part of
    # the admission checklist the other profile_completion types above
    # historically also serve (create_checklist() reads applies_to, not
    # required_stage, so this stays out of that list on purpose).
    (
        "second_passport_photo",
        "Second Passport Photograph",
        False,
        False,
        "profile_completion",
        "student",
    ),
]


class Command(BaseCommand):
    help = "Seed master data the direct-admission feature reads (fee heads, consent, docs)."

    @transaction.atomic
    def handle(self, *args, **options):
        counts = {
            "fee heads": 0,
            "fee heads retired": 0,
            "payment types": 0,
            "consent types": 0,
            "document types updated": 0,
            "document types added": 0,
        }

        for code, label, is_mandatory, display_order in FEE_HEADS:
            FeeHead.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "is_mandatory": is_mandatory,
                    "display_order": display_order,
                },
            )
            counts["fee heads"] += 1

        # .save() per row (not queryset .update()) so AuditedModel logs it.
        for fee_head in FeeHead.objects.filter(code__in=RETIRED_FEE_HEADS, is_active=True):
            fee_head.is_active = False
            fee_head.save(update_fields=["is_active", "updated_at"])
            counts["fee heads retired"] += 1

        for code, label, is_recurring, display_order in PAYMENT_TYPES:
            PaymentType.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "is_recurring": is_recurring,
                    "display_order": display_order,
                },
            )
            counts["payment types"] += 1

        for code, label, body_text, version, is_mandatory in CONSENT_TYPES:
            ConsentType.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "body_text": body_text,
                    "version": version,
                    "is_mandatory": is_mandatory,
                },
            )
            counts["consent types"] += 1

        for code, required_stage in DOCUMENT_STAGE_UPDATES:
            updated = DocumentType.objects.filter(code=code).update(required_stage=required_stage)
            if not updated:
                self.stderr.write(
                    self.style.WARNING(
                        f"DocumentType {code!r} not found — run seed_master_data first."
                    )
                )
            counts["document types updated"] += updated

        for (
            code,
            name,
            is_mandatory_default,
            has_expiry,
            required_stage,
            applies_to,
        ) in NEW_DOCUMENT_TYPES:
            DocumentType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_mandatory_default": is_mandatory_default,
                    "has_expiry": has_expiry,
                    "applies_to": applies_to,
                    "required_stage": required_stage,
                },
            )
            counts["document types added"] += 1

        for label, count in counts.items():
            self.stdout.write(self.style.SUCCESS(f"{label}: {count}"))
