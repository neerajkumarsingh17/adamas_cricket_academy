"""docs/05-build-sequence.md T-203 (built here as part of Phase 1, since
`enquiry`/`admission` need it) and docs/07-storage.md end to end: presign,
confirm (with real server-side validation, never trusting the client),
verify/reject, and the lifecycle in `state.py`.

`_s3_client()`/`_head_object()` are the two functions
docs/07-storage.md says test code must mock ("the test suite must not
touch MinIO ... presign calls are mocked") — kept as thin, separately
patchable wrappers around boto3 for exactly that reason.
"""

import uuid

import boto3
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.admissions.admission.models import Admission
from apps.people.models import Person, Staff

from .models import Document, DocumentStatus
from .state import DocumentStateMachine

# docs/07-storage.md: "Allowed types only ... Nothing else", per-type size
# limits ("10 MB documents, 5 MB photos").
ALLOWED_MIME_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png", "image/webp"})
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024

# Magic-byte sniffing (docs/07-storage.md: "Sniff the content type from the
# first bytes, do not trust the declared Content-Type"). No new dependency
# (python-magic needs the system libmagic library, which isn't guaranteed
# present) — these four signatures cover the entire allow-list above.
_MAGIC_BYTES: dict[str, bytes] = {
    "application/pdf": b"%PDF",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}

# docs/01-data-model.md section 4: `applies_to` (person / student / staff /
# admission) is who a Document can be attached to. `document` is allowed to
# import `student`/`admission` going forward along the dependency chain
# (docs/00-project-structure.md places document, idcard, parent, ... after
# student) even though `admission` only ever references `Document` back via
# a string FK to avoid the reverse import.
_OWNER_MODELS = {
    "person": Person,
    "staff": Staff,
    "admission": Admission,
}


def _owner_model(owner_type: str):
    from apps.admissions.student.models import Student

    models_by_type = {**_OWNER_MODELS, "student": Student}
    try:
        return models_by_type[owner_type]
    except KeyError:
        raise ValidationError({"owner_type": f"Unknown owner_type: {owner_type!r}"}) from None


def _build_key(*parts: str) -> str:
    """Joins `parts` into an S3 key, prefixed with
    `settings.AWS_S3_KEY_PREFIX` when one is set (the shared-bucket case —
    see that setting's definition in config/settings/base.py).
    """
    prefix = settings.AWS_S3_KEY_PREFIX.strip("/") if settings.AWS_S3_KEY_PREFIX else ""
    segments = [prefix, *parts] if prefix else list(parts)
    return "/".join(segments)


def _s3_client():
    # `or None`, not the raw setting: config/settings/dev.py's own
    # env() lookup can only fall back to its "http://localhost:9000"
    # MinIO default when the env var is completely absent, not when it's
    # present-but-empty — so a deliberately-blank AWS_S3_ENDPOINT_URL
    # (meaning "use real AWS, not MinIO") resolves to "", which boto3
    # treats as a literal (invalid) endpoint rather than "no override".
    endpoint_url = settings.AWS_S3_ENDPOINT_URL or None

    # No MinIO override -> real AWS. boto3's default (no endpoint_url at
    # all) signs against the *global* `s3.amazonaws.com` host, which every
    # region outside us-east-1 (ap-south-1 included) 307-redirects away
    # from — S3 has never served that region from the global endpoint.
    # Pointing at the regional host directly avoids that extra round trip
    # (and matters more for a presigned PUT: some HTTP clients don't
    # replay a redirected PUT's body correctly).
    if endpoint_url is None:
        endpoint_url = f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def _presigned_put_url(key: str, mime_type: str, max_size: int) -> str:
    return _s3_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key, "ContentType": mime_type},
        ExpiresIn=300,
    )


def _presigned_get_url(key: str) -> str:
    """docs/07-storage.md: "presigned GET lives 5 minutes" — used only by
    the download view, generated after that view's own permission check,
    never persisted.
    """
    return _s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key},
        ExpiresIn=settings.AWS_QUERYSTRING_EXPIRE,
    )


def _head_object(key: str) -> dict:
    """Returns `{size, sniffed_mime}` or raises `ValidationError` — the
    presign/confirm split docs/07-storage.md describes: this is only ever
    called from `confirm_upload`, never from `presign_upload`.
    """
    response = _s3_client().head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
    return {"size": response["ContentLength"]}


def _sniff_mime(first_bytes: bytes) -> str | None:
    if first_bytes[:4] == b"RIFF" and first_bytes[8:12] == b"WEBP":
        return "image/webp"
    for mime, signature in _MAGIC_BYTES.items():
        if first_bytes.startswith(signature):
            return mime
    return None


def _get_first_bytes(key: str, n: int = 16) -> bytes:
    response = _s3_client().get_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key, Range=f"bytes=0-{n - 1}"
    )
    return response["Body"].read()


def presign_upload(
    *, document_type, owner_type: str, owner_id, filename: str, mime_type: str
) -> dict:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError({"mime": f"Unsupported file type: {mime_type!r}"})

    owner_model = _owner_model(owner_type)
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    # docs/07-storage.md: "Filenames are always a fresh UUID, never the
    # user's filename" — a path-traversal bug otherwise.
    key = _build_key("documents", owner_type, str(owner_id), f"{uuid.uuid4()}.{extension}")
    max_size = MAX_PHOTO_SIZE_BYTES if mime_type.startswith("image/") else MAX_DOCUMENT_SIZE_BYTES

    return {
        "upload_url": _presigned_put_url(key, mime_type, max_size),
        "s3_key": key,
        "owner_model": owner_model,
    }


@transaction.atomic
def confirm_upload(
    *,
    document_type,
    owner_type: str,
    owner_id,
    s3_key: str,
    original_filename: str,
    mime_type: str,
) -> Document:
    owner_model = _owner_model(owner_type)
    owner = owner_model.objects.filter(pk=owner_id).first()
    if owner is None:
        raise ValidationError({"owner_id": "No such object to attach this document to."})

    try:
        head = _head_object(s3_key)
    except Exception as exc:  # boto3 raises a provider-specific ClientError
        raise ValidationError({"s3_key": f"Uploaded object not found: {exc}"}) from None

    max_size = MAX_PHOTO_SIZE_BYTES if mime_type.startswith("image/") else MAX_DOCUMENT_SIZE_BYTES
    if head["size"] > max_size:
        _delete_object(s3_key)
        raise ValidationError({"detail": f"File exceeds the {max_size} byte limit for this type."})

    sniffed = _sniff_mime(_get_first_bytes(s3_key))
    if sniffed is None or sniffed != mime_type:
        _delete_object(s3_key)
        raise ValidationError(
            {"mime": "The file's actual content does not match its declared type."}
        )

    document = Document.objects.create(
        document_type=document_type,
        owner_content_type=ContentType.objects.get_for_model(owner_model),
        owner_object_id=owner.pk,
        s3_key=s3_key,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=head["size"],
        status=DocumentStatus.PENDING,
    )
    machine = DocumentStateMachine(document)
    machine.apply(DocumentStatus.SUBMITTED)
    document.save(update_fields=["status", "updated_at"])

    # Link this upload to the matching AdmissionChecklistItem, if the
    # owner is (or belongs to) an Admission — this is what advances the
    # `documents_verified` guard once someone verifies it below.
    if owner_type == "admission":
        owner.checklist_items.filter(document_type=document_type).update(
            document=document, status=DocumentStatus.SUBMITTED
        )
    elif owner_type == "person":
        from apps.admissions.admission.models import AdmissionChecklistItem

        AdmissionChecklistItem.objects.filter(
            admission__person=owner, document_type=document_type
        ).update(document=document, status=DocumentStatus.SUBMITTED)

    return document


def _delete_object(key: str) -> None:
    _s3_client().delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)


def verify(document: Document, *, verified_by, user) -> Document:
    from django.utils import timezone

    machine = DocumentStateMachine(document)
    machine.apply(DocumentStatus.VERIFIED, user=user)
    document.verified_by = verified_by
    document.verified_at = timezone.now()
    document.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
    _sync_checklist_item_status(document, DocumentStatus.VERIFIED)
    return document


def reject(document: Document, *, reason: str, user) -> Document:
    if not reason:
        raise ValidationError({"rejection_reason": "A reason is required to reject a document."})
    machine = DocumentStateMachine(document)
    machine.apply(DocumentStatus.REJECTED, user=user, reason=reason)
    document.rejection_reason = reason
    document.save(update_fields=["status", "rejection_reason", "updated_at"])
    _sync_checklist_item_status(document, DocumentStatus.REJECTED)
    _handle_invalidated_after_verification(document)
    _notify_rejection(document)
    return document


def _sync_checklist_item_status(document: Document, status: str) -> None:
    """`AdmissionChecklistItem.status` (docs/01-data-model.md section 5:
    "mirrors the document status") is a separate field from
    `Document.status`, not a derived property — the
    `documents_verified` guard reads the checklist item, so nothing
    reflects a document decision onto its admission without this.
    """
    document.checklist_items.update(status=status)


_REOPENABLE_STEPS = frozenset({"documents_verified", "fee_pending", "fee_cleared"})


def _handle_invalidated_after_verification(document: Document) -> None:
    """docs/04-state-machines.md section 4's edge case: a document rejected
    or expired *after* the admission it belongs to was already verified
    moves that admission back to `documents_pending` — regardless of how
    much further the admission has since moved (fee collection may
    already be underway or done; only `approved` is genuinely too late,
    per the note below).

    Only handles the pre-`approved` case. The same doc section also says a
    document invalidated *after* approval "moves the student to a
    documented hold state" — there is no such status among the 11 in
    docs/04 section 2 (`document_hold` doesn't exist), so that half is
    flagged rather than invented; an approved admission's document being
    rejected currently has no automated downstream effect on the
    `Student` it already produced.
    """
    from apps.admissions.admission.state import AdmissionStateMachine

    checklist_item = document.checklist_items.select_related("admission").first()
    if checklist_item is None:
        return
    admission = checklist_item.admission
    if admission.step in _REOPENABLE_STEPS:
        machine = AdmissionStateMachine(admission)
        machine.apply(
            "documents_pending",
            reason=f"Document {document.original_filename!r} was rejected after verification.",
        )
        admission.save(update_fields=["step", "updated_at"])


def _reopen_admission_documents_if_needed(document: Document) -> None:
    """Mirrors the checklist item's status to the document it wraps —
    without this, verifying a `Document` would never update the
    `AdmissionChecklistItem.status` the `documents_verified` guard reads."""
    document.checklist_items.update(status=DocumentStatus.VERIFIED)


def _notify_rejection(document: Document) -> None:
    """docs/04-state-machines.md section 4: "parent notified" on rejection."""
    from apps.engagement.communication.services import NoActiveTemplate
    from apps.engagement.communication.services import send as send_notification

    person = _resolve_notifiable_person(document)
    if person is None or not person.mobile:
        return
    try:
        send_notification(
            code="document_rejected",
            recipient=person.mobile,
            context={
                "document_name": document.document_type.name,
                "reason": document.rejection_reason,
            },
        )
    except NoActiveTemplate:
        pass


def _resolve_notifiable_person(document: Document) -> Person | None:
    owner = document.owner
    if isinstance(owner, Person):
        return owner
    if isinstance(owner, Admission):
        return owner.person
    student_model = _owner_model("student")
    if isinstance(owner, student_model):
        return owner.person
    return None
