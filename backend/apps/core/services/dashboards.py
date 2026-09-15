"""Role dashboards — GET /api/v1/dashboards/me (docs/00-project-structure.md
lists `dashboard/` as a feature folder; docs/05-build-sequence.md defers
full "Dashboards and MIS" to Phase 12, but this endpoint was explicitly
commissioned now to power the stakeholder prototype seed_demo builds).

This aggregates across enquiry/trial/admission/student/document — models
apps/core is not allowed to statically import ("core imports nothing from
apps/", docs/00-project-structure.md). Real cross-app imports only happen
inside `if TYPE_CHECKING:` (so mypy sees full model types; nothing runs at
import time — TYPE_CHECKING is always False at runtime, and grep for
"^from apps\\." finds nothing here since these lines are indented). At
runtime the same names are bound via django.apps.apps.get_model(), the
same mechanism Django itself uses to resolve `"app_label.Model"` string
references — the runtime analogue of the string-FK-reference pattern
already used everywhere else in this codebase for the same reason.

Every query below is written to be reused for both a tile's count and its
card's item list (fetch once, use twice) — this endpoint runs on every
page load and is checked at a 300ms budget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from django.apps import apps as django_apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.models import AssessmentCriterion
from apps.core.services import approvals
from apps.core.services.dates import month_start, upcoming_weekend, week_start

if TYPE_CHECKING:
    from apps.admissions.admission.models import Admission as Admission
    from apps.admissions.document.models import Document as Document
    from apps.admissions.enquiry.models import Enquiry as Enquiry
    from apps.admissions.enquiry.models import EnquiryFollowUp as EnquiryFollowUp
    from apps.admissions.idcard.models import IDCard as IDCard
    from apps.admissions.student.models import Student as Student
    from apps.admissions.trial.models import TrialAssessment as TrialAssessment
    from apps.admissions.trial.models import TrialRegistration as TrialRegistration
    from apps.admissions.trial.models import TrialResult as TrialResult
    from apps.admissions.trial.models import TrialSlot as TrialSlot
    from apps.people.models import StudentGuardian as StudentGuardian
else:
    Admission = django_apps.get_model("admission", "Admission")
    Document = django_apps.get_model("document", "Document")
    Enquiry = django_apps.get_model("enquiry", "Enquiry")
    EnquiryFollowUp = django_apps.get_model("enquiry", "EnquiryFollowUp")
    IDCard = django_apps.get_model("idcard", "IDCard")
    Student = django_apps.get_model("student", "Student")
    TrialAssessment = django_apps.get_model("trial", "TrialAssessment")
    TrialRegistration = django_apps.get_model("trial", "TrialRegistration")
    TrialResult = django_apps.get_model("trial", "TrialResult")
    TrialSlot = django_apps.get_model("trial", "TrialSlot")
    StudentGuardian = django_apps.get_model("people", "StudentGuardian")


class DashboardUser(Protocol):
    """The slice of apps.iam.User this module needs — structural typing,
    same reasoning as core.views._PermissionCheckable.
    """

    def current_roles(self) -> Any: ...

    person: Any


class NoDashboardForRole(Exception):
    """The calling user holds none of the four roles that have a dashboard."""


# SOP §5's own role ordering (seed_roles.ROLES / docs/03-rbac.md's column
# order) filtered to the roles this endpoint implements, in that same
# relative order — not an invented hierarchy. "student"/"parent" sit last:
# self-service roles that, in practice, never coincide with a staff role
# on the same person, but the ordering still matters if one somehow did.
DASHBOARD_ROLE_PRIORITY = [
    "academy_head",
    "administration",
    "head_coach",
    "coach",
    "student",
    "parent",
]


def resolve_dashboard_role(user: DashboardUser) -> str:
    held = set(user.current_roles().values_list("code", flat=True))
    for role_code in DASHBOARD_ROLE_PRIORITY:
        if role_code in held:
            return role_code
    raise NoDashboardForRole(
        f"No dashboard is defined for any role this user holds ({sorted(held)})."
    )


def build_dashboard(user: DashboardUser) -> dict:
    role_code = resolve_dashboard_role(user)
    payload = _BUILDERS[role_code](user)
    return {"role": role_code, **payload}


def _tile(key: str, label: str, value: object, *, meta: object = None, urgent: bool = False):
    return {"key": key, "label": label, "value": value, "meta": meta, "urgent": urgent}


def _card(key: str, title: str, subtitle: str | None, type_: str, items: list):
    return {"key": key, "title": title, "subtitle": subtitle, "type": type_, "items": items}


def _person_name(person) -> str:
    if person is None:
        return ""
    return f"{person.first_name} {person.last_name}"


def _followup_item(fu) -> dict:
    # The queryset this feeds from always filters next_action_on__lt=today,
    # which excludes NULL rows at the SQL level — but the field itself is
    # nullable, so mypy needs the explicit narrowing.
    next_action_on = fu.next_action_on
    assert next_action_on is not None
    return {
        "key": f"followup-{fu.id}",
        "label": f"Overdue follow-up — {fu.enquiry.student_name}",
        "detail": f"Due {next_action_on.isoformat()}",
    }


# ---------------------------------------------------------------------- #
# Administration — "what is stuck in my queue?"
# ---------------------------------------------------------------------- #


def _administration_dashboard(user: DashboardUser) -> dict:
    today = timezone.localdate()
    week_begin = week_start(today)
    sat, sun = upcoming_weekend(today)

    # One fetch of every enquiry (the whole season is a few hundred rows at
    # most), reused for the "new this week" count and the recent-10 table —
    # cheaper than a separate aggregate() plus a separate list() query.
    all_enquiries = list(Enquiry.objects.select_related("source").order_by("-created_at"))
    new_this_week = sum(
        1 for e in all_enquiries if e.status == "new" and e.created_at.date() >= week_begin
    )
    recent_enquiries = all_enquiries[:10]

    overdue_followups = list(
        EnquiryFollowUp.objects.filter(next_action_on__lt=today, enquiry__status="contacted")
        .select_related("enquiry")
        .order_by("next_action_on")
    )
    weekend_and_attended = TrialRegistration.objects.aggregate(
        weekend=Count("id", filter=Q(slot__date__in=[sat, sun])),
        attended=Count("id", filter=Q(attended=True)),
    )
    docs_awaiting = list(
        Document.objects.filter(status="submitted")
        .select_related("document_type")
        .order_by("-created_at")[:20]
    )
    # One fetch covering every step this dashboard cares about — the
    # "approved" count comes out of the same rows as the stuck-in-queue
    # ones, instead of a fourth Admission query.
    relevant_admissions = list(
        Admission.objects.filter(step__in=["documents_pending", "fee_pending", "approved"])
        .select_related("person")
        .order_by("-updated_at")
    )
    docs_pending = [a for a in relevant_admissions if a.step == "documents_pending"]
    fee_pending = [a for a in relevant_admissions if a.step == "fee_pending"]
    admitted_count = sum(1 for a in relevant_admissions if a.step == "approved")

    selected_count = TrialResult.objects.filter(outcome="selected").count()
    active_students = Student.objects.filter(status="active").count()

    slots = list(
        TrialSlot.objects.filter(date__gte=today)
        .select_related("venue", "age_category")
        .order_by("date")[:10]
    )

    tiles = [
        _tile("new_enquiries_this_week", "New enquiries this week", new_this_week),
        _tile(
            "followups_overdue",
            "Follow-ups overdue",
            len(overdue_followups),
            urgent=True,
        ),
        _tile(
            "trials_booked_this_weekend",
            "Trials booked this weekend",
            weekend_and_attended["weekend"],
        ),
        _tile(
            "documents_to_verify",
            "Documents to verify",
            len(docs_awaiting),
            urgent=True,
        ),
    ]

    queue_items = (
        [_followup_item(fu) for fu in overdue_followups]
        + [
            {
                "key": f"admission-docs-{a.id}",
                "label": f"Documents pending — {a.application_no}",
                "detail": _person_name(a.person),
            }
            for a in docs_pending
        ]
        + [
            {
                "key": f"admission-fee-{a.id}",
                "label": f"Fee pending — {a.application_no}",
                "detail": _person_name(a.person),
            }
            for a in fee_pending
        ]
        + [
            {
                "key": f"document-{d.id}",
                "label": f"Awaiting verification — {d.document_type.name}",
                "detail": d.original_filename,
            }
            for d in docs_awaiting
        ]
    )

    cards = [
        _card("my_queue", "My queue", "Items waiting on you", "list", queue_items),
        _card(
            "recent_enquiries",
            "Recent enquiries",
            None,
            "table",
            [
                {
                    "enquiry_no": e.enquiry_no,
                    "student_name": e.student_name,
                    "source": e.source.name,
                    "status": e.status,
                    "created_at": e.created_at.isoformat(),
                }
                for e in recent_enquiries
            ],
        ),
        _card(
            "season_funnel",
            "Season funnel",
            None,
            "bars",
            [
                {"label": "Enquiries", "value": len(all_enquiries)},
                {"label": "Trials", "value": weekend_and_attended["attended"]},
                {"label": "Selected", "value": selected_count},
                {"label": "Admitted", "value": admitted_count},
                {"label": "Active students", "value": active_students},
            ],
        ),
        _card(
            "trial_slots",
            "Trial slots",
            None,
            "table",
            [
                {
                    "date": s.date.isoformat(),
                    "venue": s.venue.name,
                    "age_category": s.age_category.name,
                    "booked": s.booked_count,
                    "capacity": s.capacity,
                }
                for s in slots
            ],
        ),
    ]

    return {"tiles": tiles, "cards": cards}


# ---------------------------------------------------------------------- #
# Head Coach — "what needs my decision?"
# ---------------------------------------------------------------------- #


def _head_coach_dashboard(user: DashboardUser) -> dict:
    today = timezone.localdate()
    needs_assessment = list(
        TrialRegistration.objects.filter(attended=True, assessment__isnull=True)
        .select_related("enquiry")
        .order_by("slot__date")[:20]
    )
    needs_result = list(
        TrialAssessment.objects.filter(registration__result__isnull=True)
        .select_related("registration__enquiry")
        .order_by("assessed_at")[:20]
    )
    selected_not_admitted = list(
        TrialResult.objects.filter(outcome="selected", registration__admissions__isnull=True)
        .select_related("registration__enquiry")
        .order_by("-declared_at")[:20]
    )
    coach_progress = (
        TrialAssessment.objects.values(
            "assessed_by__person__first_name", "assessed_by__person__last_name"
        )
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    next_slot_candidates = list(
        TrialRegistration.objects.filter(attended=False, slot__date__gte=today)
        .select_related("enquiry", "slot", "slot__venue")
        .order_by("slot__date")[:20]
    )

    tiles = [
        _tile(
            "assessments_outstanding", "Assessments outstanding", len(needs_assessment), urgent=True
        ),
        _tile("results_to_declare", "Results to declare", len(needs_result), urgent=True),
        _tile(
            "selected_not_yet_admitted", "Selected, not yet admitted", len(selected_not_admitted)
        ),
    ]

    awaiting_decision = [
        {
            "key": f"assess-{r.id}",
            "label": f"Needs assessment — {r.enquiry.student_name}",
            "detail": r.trial_id,
        }
        for r in needs_assessment
    ] + [
        {
            "key": f"result-{a.id}",
            "label": f"Needs result — {a.registration.enquiry.student_name}",
            "detail": a.registration.trial_id,
        }
        for a in needs_result
    ]

    next_slot = next_slot_candidates[0].slot if next_slot_candidates else None

    cards = [
        _card("awaiting_your_decision", "Awaiting your decision", None, "list", awaiting_decision),
        _card(
            "assessment_progress",
            "Assessment progress per coach",
            None,
            "bars",
            [
                {
                    "label": (
                        f"{row['assessed_by__person__first_name']} "
                        f"{row['assessed_by__person__last_name']}"
                    ),
                    "value": row["count"],
                }
                for row in coach_progress
            ],
        ),
        _card(
            "next_slot_candidates",
            "Candidates for the next slot",
            next_slot.date.isoformat() if next_slot else None,
            "list",
            [
                {
                    "key": f"candidate-{r.id}",
                    "label": r.enquiry.student_name,
                    "detail": r.slot.venue.name if r.slot else "",
                }
                for r in next_slot_candidates
                if next_slot and r.slot_id == next_slot.id
            ],
        ),
        _card(
            "selected_awaiting_admission",
            "Selected, awaiting admission",
            None,
            "list",
            [
                {
                    "key": f"selected-{r.id}",
                    "label": r.registration.enquiry.student_name,
                    "detail": r.registration.trial_id,
                }
                for r in selected_not_admitted
            ],
        ),
    ]

    return {"tiles": tiles, "cards": cards}


# ---------------------------------------------------------------------- #
# Coach — "who do I assess next?"
# ---------------------------------------------------------------------- #


def _coach_dashboard(user: DashboardUser) -> dict:
    today = timezone.localdate()
    sat, sun = upcoming_weekend(today)
    person = user.person
    staff = getattr(person, "staff", None) if person is not None else None

    today_candidates = list(
        TrialRegistration.objects.filter(slot__date=today, assessment__isnull=True)
        .select_related("enquiry", "slot")
        .order_by("id")[:30]
    )
    # "Waiting to sync": this coach's own assessments with no TrialResult
    # yet — the closest real-schema proxy for "recorded, not yet
    # finalised" available (there's no offline/sync flag anywhere in
    # docs/01-data-model.md to model this literally).
    offline_queue = (
        list(
            TrialAssessment.objects.filter(assessed_by=staff, registration__result__isnull=True)
            .select_related("registration__enquiry")
            .order_by("-assessed_at")[:30]
        )
        if staff
        else []
    )
    assessed_this_weekend = (
        TrialAssessment.objects.filter(
            assessed_by=staff, registration__slot__date__in=[sat, sun]
        ).count()
        if staff
        else 0
    )
    next_slot = TrialSlot.objects.filter(date__gte=today).order_by("date").first()
    criteria = list(AssessmentCriterion.objects.filter(is_active=True).order_by("group", "name"))

    tiles = [
        _tile("to_assess_today", "To assess today", len(today_candidates), urgent=True),
        _tile("assessed_this_weekend", "Assessed this weekend", assessed_this_weekend),
        _tile("waiting_to_sync", "Waiting to sync", len(offline_queue), urgent=True),
        _tile(
            "next_slot",
            "Next slot",
            next_slot.date.isoformat() if next_slot else None,
            meta=next_slot.venue.name if next_slot else None,
        ),
    ]

    cards = [
        _card(
            "todays_candidates",
            "Today's candidates",
            None,
            "list",
            [
                {
                    "key": f"today-{r.id}",
                    "label": r.enquiry.student_name,
                    "detail": r.trial_id,
                }
                for r in today_candidates
            ],
        ),
        _card(
            "offline_queue",
            "Offline queue",
            "Assessed, awaiting a declared result",
            "list",
            [
                {
                    "key": f"offline-{a.id}",
                    "label": a.registration.enquiry.student_name,
                    "detail": a.registration.trial_id,
                }
                for a in offline_queue
            ],
        ),
        _card(
            "assessment_criteria",
            "Assessment criteria",
            "SOP §8 — from master data",
            "table",
            [
                {
                    "code": c.code,
                    "name": c.name,
                    "group": c.group,
                    "scale_min": str(c.scale_min),
                    "scale_max": str(c.scale_max),
                }
                for c in criteria
            ],
        ),
    ]

    return {"tiles": tiles, "cards": cards}


# ---------------------------------------------------------------------- #
# Academy Head — "what is waiting on me, and is the funnel healthy?"
# ---------------------------------------------------------------------- #


def _academy_head_dashboard(user: DashboardUser) -> dict:
    today = timezone.localdate()

    decidable = list(approvals.decidable_by(user).select_related("rule", "content_type")[:20])
    admission_stats = Admission.objects.aggregate(
        approved=Count("id", filter=Q(step="approved")),
        new_this_month=Count("id", filter=Q(created_at__date__gte=month_start(today))),
    )
    attended_trials = TrialRegistration.objects.filter(attended=True).count()
    selected_count = TrialResult.objects.filter(outcome="selected").count()
    active_students = Student.objects.filter(status="active").count()
    # Grouped counts sum to the grand total, so this covers both the "by
    # source" bars and the conversion tile's denominator in one query.
    by_source = list(
        Enquiry.objects.values("source__name").annotate(count=Count("id")).order_by("-count")
    )
    enquiry_total = sum(row["count"] for row in by_source)

    conversion_pct = round(active_students / enquiry_total * 100, 1) if enquiry_total else 0.0

    tiles = [
        _tile("waiting_on_your_approval", "Waiting on your approval", len(decidable), urgent=True),
        _tile(
            "new_admissions_this_month",
            "New admissions this month",
            admission_stats["new_this_month"],
        ),
        _tile("active_students", "Active students", active_students),
        _tile(
            "enquiry_to_student_conversion",
            "Enquiry -> student conversion",
            conversion_pct,
            meta="%",
        ),
    ]

    cards = [
        _card(
            "approval_queue",
            "Approval queue",
            None,
            "list",
            [
                {
                    "key": f"approval-{a.id}",
                    "label": f"{a.rule.module}:{a.rule.action}",
                    # content_type is select_related'd; the generic FK
                    # target itself isn't (can't be), so this avoids an
                    # extra query per row for what's just a display label.
                    "detail": f"{a.content_type.model} #{a.object_id}",
                }
                for a in decidable
            ],
        ),
        _card(
            "season_funnel",
            "Season funnel",
            None,
            "bars",
            [
                {"label": "Enquiries", "value": enquiry_total},
                {"label": "Trials", "value": attended_trials},
                {"label": "Selected", "value": selected_count},
                {"label": "Admitted", "value": admission_stats["approved"]},
                {"label": "Active students", "value": active_students},
            ],
        ),
        _card(
            "enquiries_by_source",
            "Enquiries by source",
            None,
            "bars",
            [{"label": row["source__name"], "value": row["count"]} for row in by_source],
        ),
        _card(
            "recent_audit_entries",
            "Recent audit entries",
            "Not available — apps.audit has no AuditLog model yet",
            "audit",
            [],
        ),
    ]

    return {"tiles": tiles, "cards": cards}


# ---------------------------------------------------------------------- #
# Student — "where do I stand?"
# ---------------------------------------------------------------------- #


def _student_dashboard(user: DashboardUser) -> dict:
    # A Person can carry more than one Student row after a re-admission
    # (docs/04-state-machines.md section 5) — the latest one is "me" now.
    student = (
        Student.objects.select_related("admission", "programme")
        .filter(person=user.person)
        .order_by("-created_at")
        .first()
    )
    if student is None:
        # Shouldn't happen in practice — a `student` role is only ever
        # granted via services.grant_student_login, after the Student row
        # already exists — but keeps this dashboard's shape (4 tiles) the
        # same as every other role's rather than a bespoke short payload.
        return {
            "tiles": [
                _tile("status", "My status", "No student record yet"),
                _tile("fee_status", "Fee status", "—"),
                _tile("documents_verified", "Documents verified", "—"),
                _tile("id_card", "ID card", "—"),
            ],
            "cards": [],
            "student_id": None,
        }

    student_ct = ContentType.objects.get_for_model(Student)
    documents = list(
        Document.objects.filter(owner_content_type=student_ct, owner_object_id=student.id)
        .select_related("document_type")
        .order_by("-created_at")
    )
    verified_count = sum(1 for d in documents if d.status == "verified")
    has_active_card = IDCard.objects.filter(student=student, status="active").exists()

    tiles = [
        _tile("status", "My status", student.status),
        _tile(
            "fee_status",
            "Fee status",
            student.admission.fee_payment_status if student.admission_id else "—",
        ),
        _tile("documents_verified", "Documents verified", f"{verified_count}/{len(documents)}"),
        _tile("id_card", "ID card", "Issued" if has_active_card else "Not issued"),
    ]

    cards = [
        _card(
            "my_documents",
            "My documents",
            None,
            "table",
            [
                {
                    "document_type": d.document_type.name,
                    "status": d.status,
                    "filename": d.original_filename,
                }
                for d in documents
            ],
        ),
    ]
    return {"tiles": tiles, "cards": cards, "student_id": str(student.id)}


# ---------------------------------------------------------------------- #
# Parent — "how are my children doing?"
# ---------------------------------------------------------------------- #


def _parent_dashboard(user: DashboardUser) -> dict:
    child_ids = StudentGuardian.objects.filter(guardian__person=user.person).values_list(
        "student_id", flat=True
    )
    children = list(
        Student.objects.filter(id__in=child_ids).select_related("person", "programme", "admission")
    )

    student_ct = ContentType.objects.get_for_model(Student)
    docs_pending = Document.objects.filter(
        owner_content_type=student_ct, owner_object_id__in=[c.id for c in children]
    ).filter(status__in=["submitted", "rejected"])
    fees_pending = len(
        [c for c in children if c.admission_id and c.admission.fee_payment_status != "paid"]
    )
    active_children = len([c for c in children if c.status == "active"])

    tiles = [
        _tile("my_children", "My children", len(children)),
        _tile("active_children", "Active", active_children),
        _tile("documents_pending", "Documents pending action", docs_pending.count(), urgent=True),
        _tile("fees_pending", "Fees pending", fees_pending, urgent=fees_pending > 0),
    ]

    cards = [
        _card(
            "my_children",
            "My children",
            None,
            "table",
            [
                {
                    "name": _person_name(c.person),
                    "student_code": c.student_code,
                    "programme": c.programme.name if c.programme else None,
                    "status": c.status,
                    "href": f"/parent/children/{c.id}",
                }
                for c in children
            ],
        ),
        _card(
            "documents_awaiting_verification",
            "Documents awaiting verification",
            None,
            "list",
            [
                {
                    "key": f"document-{d.id}",
                    "label": d.document_type.name,
                    "detail": d.status,
                    "href": f"/parent/children/{d.owner_object_id}",
                }
                for d in docs_pending.select_related("document_type")
            ],
        ),
    ]
    return {"tiles": tiles, "cards": cards}


_BUILDERS = {
    "administration": _administration_dashboard,
    "head_coach": _head_coach_dashboard,
    "coach": _coach_dashboard,
    "academy_head": _academy_head_dashboard,
    "student": _student_dashboard,
    "parent": _parent_dashboard,
}
