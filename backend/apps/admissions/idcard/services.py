"""docs/05-build-sequence.md T-801/T-802/T-803. No `docs/04-state-machines.md`
table exists for `IDCard.status` (only the choices are named in
docs/01-data-model.md section 5) — transitions here are the minimal,
literal reading of "replacement history is retained; old cards are
invalidated" (docs/05 T-801's acceptance check), not an invented state
machine with guards/roles this doc never specified.
"""

import datetime

from django.core import signing
from django.db import transaction
from django.utils import timezone

from .models import IDCard, IDCardStatus

_QR_SALT = "apps.admissions.idcard.qr"
DEFAULT_VALIDITY_YEARS = 3


def _issue_seq(student_code: str) -> int:
    return IDCard.objects.filter(student__student_code=student_code).count() + 1


def _sign_qr_payload(card_no: str) -> str:
    """docs/01-data-model.md section 5: "signed token, not the raw student
    id" — `card_no` (not the student's pk) is what gets encoded, so a
    resolved token still never has to reveal or embed the database id.
    """
    return signing.dumps({"card_no": card_no}, salt=_QR_SALT)


def _unsign_qr_payload(token: str) -> str | None:
    try:
        data = signing.loads(token, salt=_QR_SALT, max_age=None)
    except signing.BadSignature:
        return None
    return data.get("card_no")


@transaction.atomic
def issue_card(student, *, issued_by, valid_until=None) -> IDCard:
    """docs/01-data-model.md section 6: `{student_code}-{issue_seq}`,
    scoped per student rather than a flat series (`core.services.numbering`
    doesn't carry this one — its own docstring says so explicitly).
    Supersedes any currently-active card for this student.
    """
    previous_active = IDCard.objects.filter(student=student, status=IDCardStatus.ACTIVE).first()

    card_no = f"{student.student_code}-{_issue_seq(student.student_code)}"
    card = IDCard.objects.create(
        student=student,
        card_no=card_no,
        issued_on=timezone.now().date(),
        valid_until=valid_until
        or (timezone.now().date() + datetime.timedelta(days=365 * DEFAULT_VALIDITY_YEARS)),
        qr_payload=_sign_qr_payload(card_no),
        status=IDCardStatus.ACTIVE,
        replaces=previous_active,
        issued_by=issued_by,
    )

    if previous_active is not None:
        previous_active.status = IDCardStatus.REPLACED
        previous_active.save(update_fields=["status", "updated_at"])

    return card


def report_lost(card: IDCard) -> IDCard:
    card.status = IDCardStatus.LOST
    card.save(update_fields=["status", "updated_at"])
    return card


def resolve_qr(token: str, *, authorized: bool) -> dict:
    """GET /id-cards/resolve/{token} — docs/02-api-spec.md: "Unauthenticated
    returns validity only." `authorized` is the caller's
    `has_perm_for("idcard", "view")`, not merely "is logged in" — the
    endpoint is reachable without auth at all, so an authenticated user
    lacking that permission gets the same minimal payload as a stranger.
    """
    card_no = _unsign_qr_payload(token)
    if card_no is None:
        return {"valid": False}

    card = (
        IDCard.objects.select_related("student", "student__person").filter(card_no=card_no).first()
    )
    if card is None:
        return {"valid": False}

    is_valid = card.status == IDCardStatus.ACTIVE and card.valid_until >= timezone.now().date()
    if not authorized:
        return {"valid": is_valid}

    return {
        "valid": is_valid,
        "student_code": card.student.student_code,
        "name": str(card.student.person),
        "status": card.status,
        "valid_until": card.valid_until,
    }
