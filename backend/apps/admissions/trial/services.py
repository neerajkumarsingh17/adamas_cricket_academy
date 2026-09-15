"""docs/05-build-sequence.md T-501..T-506. `apps.admissions.trial` is
allowed to import `apps.admissions.enquiry` going forward along the
`enquiry -> trial -> admission -> student` chain
(docs/00-project-structure.md) — the reverse is not allowed, which is why
the enquiry -> trial conversion lives here rather than in `enquiry`.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.admissions.enquiry.models import Enquiry, EnquiryStatus
from apps.core.services.numbering import next_number
from apps.people.models import Person
from apps.people.services import resolve_person, split_name

from .models import (
    TrialAssessment,
    TrialAssessmentScore,
    TrialOutcome,
    TrialRegistration,
    TrialResult,
    TrialSlot,
)


class TrialSlotFull(APIException):
    status_code = 409
    default_code = "trial_slot_full"
    default_detail = "This trial slot has no remaining capacity."


class AssessmentLocked(APIException):
    status_code = 409
    default_code = "assessment_locked"
    default_detail = "A result has already been declared — this assessment can no longer be edited."


class ResultAlreadyDeclared(APIException):
    status_code = 409
    default_code = "result_already_declared"
    default_detail = "A result has already been declared for this registration."


@transaction.atomic
def register_from_enquiry(enquiry: Enquiry, slot_id) -> TrialRegistration:
    """SOP §9 step 2. Backs both documented entry points —
    `POST /enquiries/{id}/convert-to-trial` and `POST /trials/slots/{id}/book`
    (docs/02-api-spec.md) — which are the same operation addressed from two
    different screens (the enquiry pipeline vs. the trial calendar).

    `select_for_update` on the slot (docs/01-data-model.md section 5:
    "Booking must use select_for_update on the slot. Overbooking is a
    defect") so two concurrent bookings onto the last open seat can't both
    succeed.
    """
    slot = TrialSlot.objects.select_for_update().get(pk=slot_id)
    if slot.booked_count >= slot.capacity:
        raise TrialSlotFull()

    person = _resolve_or_create_person(enquiry)

    registration = TrialRegistration.objects.create(
        trial_id=next_number("TRL"),
        enquiry=enquiry,
        person=person,
        slot=slot,
    )
    TrialSlot.objects.filter(pk=slot.pk).update(booked_count=slot.booked_count + 1)

    enquiry.status = EnquiryStatus.TRIAL_SCHEDULED
    enquiry.save(update_fields=["status"])

    return registration


def _resolve_or_create_person(enquiry: Enquiry) -> Person:
    if enquiry.person is not None:
        return enquiry.person

    first_name, last_name = split_name(enquiry.student_name)
    match = resolve_person(
        {
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": enquiry.date_of_birth,
            "guardian_mobile": enquiry.guardian_mobile,
        }
    )
    if match.exact:
        person = match.exact[0]
    else:
        person = Person.objects.create(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=enquiry.date_of_birth,
            gender=enquiry.gender,
            mobile=enquiry.guardian_mobile,
            email=enquiry.guardian_email,
            address_line1=enquiry.address or "",
            address_line2="",
            city="",
            state="",
            pincode="",
        )
    enquiry.person = person
    enquiry.save(update_fields=["person"])
    return person


def record_attendance(registration: TrialRegistration, attended: bool) -> TrialRegistration:
    registration.attended = attended
    registration.save(update_fields=["attended"])
    return registration


@transaction.atomic
def submit_assessment(
    registration: TrialRegistration, *, assessed_by, overall_remarks: str, scores: list[dict]
) -> TrialAssessment:
    """docs/02-api-spec.md: "Full scored assessment in one payload. 409 if
    locked." Idempotent under retry by construction rather than by a
    separate `Idempotency-Key` column: `TrialAssessment` is one-to-one with
    `TrialRegistration`, so replaying the same submission after a
    reconnect (T-509's offline queue) updates the same row instead of
    creating a duplicate — there is no field docs/01-data-model.md defines
    to store a client-supplied key on, and none is needed for correctness
    here.
    """
    assessment, _created = TrialAssessment.objects.get_or_create(
        registration=registration, defaults={"assessed_by": assessed_by}
    )
    if assessment.is_locked:
        raise AssessmentLocked()

    assessment.assessed_by = assessed_by
    assessment.assessed_at = timezone.now()
    assessment.overall_remarks = overall_remarks
    assessment.save(update_fields=["assessed_by", "assessed_at", "overall_remarks", "updated_at"])

    for score in scores:
        TrialAssessmentScore.objects.update_or_create(
            assessment=assessment,
            criterion_id=score["criterion"],
            defaults={"score": score["score"]},
        )

    return assessment


_REVIEW_REQUIRED_OUTCOMES = frozenset({TrialOutcome.SHORTLISTED, TrialOutcome.WAITLISTED})


@transaction.atomic
def declare_result(
    registration: TrialRegistration, *, outcome: str, declared_by, review_on=None, notes: str = ""
) -> TrialResult:
    """docs/04-state-machines.md section 3. Locks the assessment; a locked
    assessment can only be edited through an approval (Phase 3+ concern —
    not built here, flagged rather than silently permitted).

    `shortlisted`/`waitlisted` are explicitly not final in that doc — "held
    pending capacity" / "appears on the daily worklist until resolved" — so
    an *existing* result in one of those two outcomes can be resolved to a
    new outcome once a spot opens up or the wait times out; that's the
    concrete answer to "the candidate didn't get in on the day — how do
    they get another chance without a whole new enquiry/trial." A result
    that's already final (selected/not_selected/re_trial) still can't be
    redeclared — SOP §8's lock is on the *decision*, not on how long it
    took to reach one.
    """
    existing = TrialResult.objects.filter(registration=registration).first()
    if existing is not None and existing.outcome not in _REVIEW_REQUIRED_OUTCOMES:
        raise ResultAlreadyDeclared()

    if outcome in _REVIEW_REQUIRED_OUTCOMES and review_on is None:
        raise ValidationError(
            {"review_on": "review_on is required for a shortlisted or waitlisted outcome."}
        )

    result, _created = TrialResult.objects.update_or_create(
        registration=registration,
        defaults={
            "outcome": outcome,
            "declared_by": declared_by,
            "declared_at": timezone.now(),
            "review_on": review_on,
            "notes": notes,
        },
    )

    TrialAssessment.objects.filter(registration=registration).update(is_locked=True)

    if outcome == TrialOutcome.NOT_SELECTED:
        enquiry = registration.enquiry
        enquiry.status = EnquiryStatus.LOST
        enquiry.save(update_fields=["status"])

    _notify_result(registration, outcome)

    return result


# dict[str, str], not dict[TrialOutcome, str] — `_notify_result` is called
# with plain `str` values (`registration.result.outcome`, a CharField
# value, isn't typed as TrialOutcome at the Python level even though its
# choices are), so a TrialOutcome-keyed dict would mismatch every lookup.
_RESULT_TEMPLATE_CODES: dict[str, str] = {
    TrialOutcome.SELECTED: "trial_result_selected",
    TrialOutcome.SHORTLISTED: "trial_result_shortlisted",
    TrialOutcome.WAITLISTED: "trial_result_waitlisted",
    TrialOutcome.NOT_SELECTED: "trial_result_not_selected",
    TrialOutcome.RE_TRIAL: "trial_result_re_trial",
}


def _notify_result(registration: TrialRegistration, outcome: str) -> None:
    from apps.engagement.communication.services import NoActiveTemplate
    from apps.engagement.communication.services import send as send_notification

    try:
        send_notification(
            code=_RESULT_TEMPLATE_CODES[outcome],
            recipient=registration.enquiry.guardian_mobile,
            context={
                "student_name": registration.enquiry.student_name,
                "trial_id": registration.trial_id,
                "outcome": outcome,
            },
        )
    except NoActiveTemplate:
        pass


def bulk_notify_results(registration_ids: list) -> int:
    """POST /trials/results/bulk-notify — docs/02-api-spec.md: "One action
    notifies a whole trial day." Re-sends the same result notification for
    every registration in the list that already has a declared result.
    """
    count = 0
    for registration in TrialRegistration.objects.filter(
        pk__in=registration_ids, result__isnull=False
    ).select_related("result", "enquiry"):
        _notify_result(registration, registration.result.outcome)
        count += 1
    return count
