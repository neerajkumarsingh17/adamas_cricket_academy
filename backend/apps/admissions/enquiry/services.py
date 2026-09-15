"""docs/05-build-sequence.md T-401/T-402/T-403: numbering, duplicate
detection at intake, and follow-up tracking.

The enquiry -> trial conversion (SOP §9 step 2, T-404) is deliberately
*not* here even though docs/02-api-spec.md names its URL
`/enquiries/{id}/convert-to-trial` — `apps.admissions.enquiry` may not
import `apps.admissions.trial` (docs/00-project-structure.md: "the chain
enquiry -> trial -> admission -> student ... student knows about
admission, admission knows about trial, and never the reverse"). The
view, service and URL for that endpoint live in
`apps.admissions.trial`, which is allowed to import `enquiry` going
forward along the chain; only the URL *path* (registered from trial's
urls.py) preserves the spec's enquiry-shaped route.
"""

from django.db import transaction

from apps.core.services.numbering import next_number
from apps.people.services import PersonMatch, resolve_person_by_name

from .models import Enquiry, EnquiryFollowUp, EnquiryStatus


def check_duplicate(*, student_name: str, date_of_birth, guardian_mobile: str) -> PersonMatch:
    """The same check `create_enquiry` runs automatically, exposed so the
    frontend's live "duplicate candidates as you type" (T-407) can call it
    before anything is submitted. `GET /persons/search` calls
    `apps.people.services.resolve_person_by_name` directly instead of this
    — `people` cannot import from `admissions.enquiry`
    (docs/00-project-structure.md's dependency direction).
    """
    return resolve_person_by_name(
        full_name=student_name, date_of_birth=date_of_birth, guardian_mobile=guardian_mobile
    )


@transaction.atomic
def create_enquiry(data: dict, *, owner=None) -> tuple[Enquiry, PersonMatch]:
    """T-401 (numbering) + T-402 (duplicate detection at intake). An exact
    dedupe_key match auto-links `enquiry.person` — SOP §78 says a returning
    person must never get a second identity record, and by the time
    someone is re-entering a name+DOB+guardian-mobile combination that
    hashes to an existing Person, that's already true, not just probable.
    Fuzzy matches are lower-confidence and are only surfaced for a human to
    look at, never auto-linked.
    """
    match = check_duplicate(
        student_name=data["student_name"],
        date_of_birth=data["date_of_birth"],
        guardian_mobile=data["guardian_mobile"],
    )
    enquiry = Enquiry.objects.create(
        enquiry_no=next_number("ENQ"),
        owner=owner,
        person=match.exact[0] if match.exact else None,
        **data,
    )
    return enquiry, match


@transaction.atomic
def add_follow_up(
    enquiry: Enquiry, *, contacted_on, mode: str, notes: str, next_action_on, created_by
) -> EnquiryFollowUp:
    follow_up = EnquiryFollowUp.objects.create(
        enquiry=enquiry,
        contacted_on=contacted_on,
        mode=mode,
        notes=notes,
        next_action_on=next_action_on,
        created_by=created_by,
    )
    if enquiry.status == EnquiryStatus.NEW:
        enquiry.status = EnquiryStatus.CONTACTED
        enquiry.save(update_fields=["status"])
    return follow_up


def conversion_analytics(*, date_from=None, date_to=None):
    """GET /enquiries/analytics/conversion — docs/02-api-spec.md: rates by
    source and period, computable "with no manual counting"
    (docs/05-build-sequence.md T-411 and the Phase 1 exit criteria).
    """
    from django.db.models import Count, Q

    queryset = Enquiry.objects.all()
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    # `admission_count`, not `admissions` — django-stubs generates a
    # .values()/.annotate() return type from the model's own fields and
    # reverse relations, and Enquiry already has an "admissions" reverse
    # relation (Admission.enquiry's related_name), so annotating under
    # that same name collides with it in the generated stub.
    rows = queryset.values("source__code", "source__name").annotate(
        enquiries=Count("id"),
        trials=Count("id", filter=Q(trial_registrations__isnull=False), distinct=True),
        admission_count=Count("id", filter=Q(admissions__isnull=False), distinct=True),
    )

    results = []
    for row in rows:
        enquiries = row["enquiries"]
        admission_count = row["admission_count"]
        results.append(
            {
                "source": row["source__code"],
                "source_name": row["source__name"],
                "enquiries": enquiries,
                "trials": row["trials"],
                "admissions": admission_count,
                "enquiry_to_trial_rate": (row["trials"] / enquiries) if enquiries else 0,
                "trial_to_admission_rate": (admission_count / row["trials"])
                if row["trials"]
                else 0,
            }
        )
    return results
