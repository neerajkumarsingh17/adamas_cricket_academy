"""docs/00-project-structure.md's academics/attendance app (M10)."""

import calendar
import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.admissions.student.models import Student

from .models import (
    COUNTS_AS_PRESENT,
    NOT_COUNTED,
    Attendance,
    AttendanceCorrection,
    CorrectionStatus,
)


class SessionNotEditable(APIException):
    status_code = 409
    default_code = "session_not_editable"
    default_detail = (
        "This session has already happened, or already has attendance recorded, and can "
        "no longer be rescheduled or deleted — cancel it instead."
    )


class SessionWindowClosed(APIException):
    status_code = 409
    default_code = "session_window_closed"
    default_detail = (
        "This session started more than 24 hours ago — its status and attendance can no "
        "longer be changed."
    )


class SessionNotYetStarted(APIException):
    status_code = 409
    default_code = "session_not_yet_started"
    default_detail = (
        "This session hasn't started yet — its status and attendance can't be changed until "
        "it does."
    )


class SessionDateConflict(APIException):
    status_code = 409
    default_code = "session_date_conflict"
    default_detail = "This batch already has a session scheduled on that date."


_SCHEDULE_FIELDS = {"date", "start_time", "end_time", "coach"}


def _session_start_at(session) -> datetime.datetime:
    """Aware local datetime the session actually starts at — the anchor
    every 24-hour grace window below (and _assert_reschedulable's own
    boundary) is measured from."""
    return timezone.make_aware(datetime.datetime.combine(session.date, session.start_time))


def _assert_within_mark_window(session) -> None:
    """A Coach may mark attendance, flip a session's conducted status, or
    cancel it from the moment it actually starts and for 24 hours after —
    not only "today" — so a session run late in the evening, or one the
    coach only gets to log the next morning, isn't locked out. Nothing
    about a session is real yet before it starts (no attendance to take,
    nothing to confirm as conducted or cancel-in-progress), so a
    same-day-or-future session dated ahead of its start time is refused
    exactly the same way a stale one is. Past the 24-hour close, the
    record is final for everyone, not just the own-scope Coach grant —
    same as _assert_reschedulable's boundary below, this is a
    business-time rule, not a permission check, so an all-scope role gets
    no bypass either. Only an AttendanceCorrection can still change
    already-marked attendance past this point (SOP §70).
    """
    now = timezone.now()
    start = _session_start_at(session)
    if now < start:
        raise SessionNotYetStarted()
    if now > start + datetime.timedelta(hours=24):
        raise SessionWindowClosed()


def attendance_percentage(student, start: datetime.date, end: datetime.date) -> Decimal | None:
    """The ONLY place this formula exists — nothing else may recompute or
    approximate it. Only sessions that actually happened count at all
    (`session__is_conducted=True`); NOT_COUNTED statuses (medical leave)
    are excluded from the denominator entirely, not just from the
    numerator — a student on medical leave shows the same percentage as
    if those sessions had never been scheduled for them, not a lower one.
    Returns None, not 0, when there is nothing to compute a percentage
    from (no conducted sessions in range) — "no data" and "0% attendance"
    are different facts.
    """
    qs = Attendance.objects.filter(
        student=student,
        session__date__range=(start, end),
        session__is_conducted=True,
    ).exclude(status__in=NOT_COUNTED)

    total = qs.count()
    if total == 0:
        return None

    present = qs.filter(status__in=COUNTS_AS_PRESENT).count()
    return (Decimal(present) / Decimal(total) * 100).quantize(Decimal("0.01"))


def mark_bulk(session, marks: list[dict], user) -> list[dict]:
    """Returns a per-student result list — marking 22 students where 1
    fails must save the other 21, not roll all of them back.

    Create-only, deliberately never update_or_create: AttendanceCorrection
    is the only path allowed to change an already-marked attendance (SOP
    §70 — "requesting does not change the attendance, only approval
    does"). Letting a re-submitted bulk mark silently overwrite an
    existing row would bypass that audit trail entirely.

    Gated by the same 24-hour-after-start window as cancel_session/
    mark_session_conducted (_assert_within_mark_window) — raised before
    touching any row, all-or-nothing, unlike the per-student results below.
    """
    _assert_within_mark_window(session)
    results: list[dict] = []
    for mark in marks:
        student_id = mark.get("student")
        if not student_id:
            results.append({"student": student_id, "ok": False, "error": "student is required."})
            continue
        try:
            with transaction.atomic():
                student = Student.objects.get(pk=student_id)
                attendance = Attendance.objects.create(
                    session=session,
                    student=student,
                    status=mark["status"],
                    remarks=mark.get("remarks", ""),
                    marked_by=user,
                )
            results.append({"student": student_id, "ok": True, "status": attendance.status})
        except Student.DoesNotExist:
            results.append({"student": student_id, "ok": False, "error": "Student not found."})
        except IntegrityError:
            results.append(
                {"student": student_id, "ok": False, "error": "Already marked for this session."}
            )
        except (KeyError, ValueError) as exc:
            results.append({"student": student_id, "ok": False, "error": str(exc)})
    return results


@transaction.atomic
def cancel_session(session, reason: str):
    """Nobody is absent from a session that did not happen — any
    Attendance rows already marked for it are deleted, not just the
    session flipped to not-conducted. Gated by the same 24-hour-after-
    start window as mark_bulk/mark_session_conducted.
    """
    _assert_within_mark_window(session)
    session.attendance_records.all().delete()
    session.is_conducted = False
    session.cancel_reason = reason
    session.save(update_fields=["is_conducted", "cancel_reason", "updated_at"])
    return session


@transaction.atomic
def mark_session_conducted(session):
    """Explicit Coach status update — nothing else in this codebase ever
    sets `is_conducted` True (generate_sessions() creates every row False;
    the only other write to the field is cancel_session(), and only ever
    to False). Also clears `cancel_reason`: a session cancelled in error
    can be marked conducted again within the same 24-hour window, the
    same grace period every other action in this module gets.
    """
    _assert_within_mark_window(session)
    session.is_conducted = True
    session.cancel_reason = ""
    session.save(update_fields=["is_conducted", "cancel_reason", "updated_at"])
    return session


def _assert_reschedulable(session) -> None:
    """Same 24-hour-after-start boundary as _assert_within_mark_window
    (replaces the old "started" cutoff of `date <= today`, which blocked
    same-day edits from midnight even before the session had actually
    begun), plus the attendance guard — once someone has actually been
    marked for a session it is a real historical record, not a
    placeholder generate_sessions() can still be corrected in place.
    update_session_details() only calls this when a schedule field is
    actually changing; content fields (training_type/objective/report)
    are exempt, since filing a report is normally done *after* the
    session, often once attendance already exists.
    """
    if (
        timezone.now() > _session_start_at(session) + datetime.timedelta(hours=24)
        or session.attendance_records.exists()
    ):
        raise SessionNotEditable()


@transaction.atomic
def update_session_details(session, data: dict):
    """`data` holds only the fields actually being changed (partial-update
    semantics) — training_type/objective/report are always editable;
    date/start_time/end_time/coach only while the session is still
    reschedulable (see _assert_reschedulable).
    """
    if _SCHEDULE_FIELDS & data.keys():
        _assert_reschedulable(session)

    for field, value in data.items():
        setattr(session, field, value)

    try:
        session.save()
    except IntegrityError:
        raise SessionDateConflict() from None
    return session


@transaction.atomic
def delete_session(session) -> None:
    """Hard delete — distinct from cancel_session()'s soft "not
    conducted" flip, which keeps the row (and its cancel_reason) as a
    permanent record. Only allowed while the session is still
    reschedulable (see _assert_reschedulable); an already-attended or
    past session must be cancelled instead, so its history survives.
    """
    _assert_reschedulable(session)
    session.delete()


def request_correction(
    attendance: Attendance, to_status: str, reason: str, user
) -> AttendanceCorrection:
    """Creates the correction request only — does NOT touch
    `attendance.status`. Only approve_correction() does that; the
    correction row is the permanent record of why it changed (SOP §70).
    """
    return AttendanceCorrection.objects.create(
        attendance=attendance,
        from_status=attendance.status,
        to_status=to_status,
        reason=reason,
        requested_by=user,
    )


def roster(session) -> dict:
    """Enrolled students for this session's batch + each one's attendance
    mark for this specific session, if any. Lives here rather than in
    apps.academics.batch because it needs Attendance data, and the
    dependency direction (docs/00-project-structure.md: attendance hangs
    off batch, never the reverse) only allows this app to import that
    one — not the other way around.
    """
    from apps.people.serializers import PersonSerializer

    enrollments = session.batch.enrollments.filter(is_active=True).select_related("student__person")
    marks = {a.student_id: a for a in Attendance.objects.filter(session=session)}

    return {
        "session_id": str(session.id),
        "students": [
            {
                "student_id": str(enrollment.student_id),
                "student_code": enrollment.student.student_code,
                "person": PersonSerializer(enrollment.student.person).data,
                "mark": {
                    "status": marks[enrollment.student_id].status,
                    "remarks": marks[enrollment.student_id].remarks,
                }
                if enrollment.student_id in marks
                else None,
            }
            for enrollment in enrollments
        ],
    }


def monthly_report(batch, month: datetime.date) -> dict:
    """GET /batches/{id}/attendance-report/ — a student x session-date
    grid for one calendar month. `month` is the 1st of the target month
    (the view parses "YYYY-MM" into this before calling).

    Sessions include cancelled ones (`is_conducted=False`) — the frontend
    greys those columns, it doesn't drop them, so a cancelled session
    reads as "did not happen" rather than as every student's absence.

    Each row's `percentage` is attendance_percentage() itself, called
    once per student — the same formula the self-service portal uses,
    never re-derived from the grid's own marks.
    """
    start = month.replace(day=1)
    end = month.replace(day=calendar.monthrange(month.year, month.month)[1])

    sessions = list(batch.sessions.filter(date__range=(start, end)).order_by("date"))
    enrollments = (
        batch.enrollments.filter(from_date__lte=end)
        .filter(Q(to_date__isnull=True) | Q(to_date__gte=start))
        .select_related("student__person")
    )

    marks_by_student: dict[str, dict[str, str]] = {}
    for mark in Attendance.objects.filter(session__in=sessions):
        marks_by_student.setdefault(str(mark.student_id), {})[mark.session.date.isoformat()] = (
            mark.status
        )

    from apps.people.serializers import PersonSerializer

    rows = []
    for enrollment in enrollments:
        student_marks = marks_by_student.get(str(enrollment.student_id), {})
        rows.append(
            {
                "student_id": str(enrollment.student_id),
                "student_code": enrollment.student.student_code,
                "person": PersonSerializer(enrollment.student.person).data,
                "marks": {
                    session.date.isoformat(): student_marks.get(session.date.isoformat())
                    for session in sessions
                },
                "percentage": attendance_percentage(enrollment.student, start, end),
            }
        )

    return {
        "batch_id": str(batch.id),
        "batch_name": batch.name,
        "month": start.strftime("%Y-%m"),
        "sessions": [
            {"date": session.date.isoformat(), "is_conducted": session.is_conducted}
            for session in sessions
        ],
        "rows": rows,
    }


@transaction.atomic
def approve_correction(correction: AttendanceCorrection, user) -> AttendanceCorrection:
    """Head-Coach-only — enforced entirely by the `attendance` RBAC row
    (docs/03-rbac.md: only head_coach holds `approve` there) plus this
    action's `verb="approve"`, not a code-level role check — CLAUDE.md
    rule 3 forbids `if user.role == "..."`, and a narrow RBAC cell is this
    codebase's documented preference whenever it's expressive enough
    (apps.admissions.document.state's DocumentStateMachine docstring).
    """
    correction.attendance.status = correction.to_status
    correction.attendance.save(update_fields=["status", "updated_at"])

    correction.status = CorrectionStatus.APPROVED
    correction.approved_by = user
    correction.approved_at = timezone.now()
    correction.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return correction


def reject_correction(correction: AttendanceCorrection, user) -> AttendanceCorrection:
    """Declines the request — does NOT touch `attendance.status`, same as
    request_correction() itself: a rejected correction never happened as
    far as the attendance record is concerned. Same Head-Coach-only gate
    as approve_correction() (`verb="approve"` on both actions) — deciding
    a correction either way is the same authority.
    """
    correction.status = CorrectionStatus.REJECTED
    correction.approved_by = user
    correction.approved_at = timezone.now()
    correction.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return correction
