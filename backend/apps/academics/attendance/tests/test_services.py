import datetime

import pytest
from django.utils import timezone

from apps.academics.batch.models import TrainingSession
from apps.academics.batch.tests.factories import TrainingSessionFactory
from apps.admissions.student.tests.factories import StudentFactory
from apps.iam.tests.factories import UserFactory

from .. import services
from ..models import Attendance, CorrectionStatus, Status
from .factories import AttendanceFactory


def _conducted_session(date):
    return TrainingSessionFactory(date=date, is_conducted=True)


@pytest.mark.django_db
def test_medical_leave_does_not_change_attendance_percentage():
    """A student on MEDICAL_LEAVE for six weeks shows the same percentage
    as before the leave — NOT_COUNTED statuses are excluded from the
    denominator entirely, not just the numerator.
    """
    student = StudentFactory()
    start = datetime.date(2026, 1, 5)

    # Baseline: 8 conducted sessions, all present.
    baseline_dates = [start + datetime.timedelta(weeks=w) for w in range(8)]
    for date in baseline_dates:
        AttendanceFactory(session=_conducted_session(date), student=student, status=Status.PRESENT)

    baseline = services.attendance_percentage(student, start, start + datetime.timedelta(weeks=20))
    assert baseline == 100

    # Six more weeks, all on medical leave.
    leave_dates = [start + datetime.timedelta(weeks=w) for w in range(8, 14)]
    for date in leave_dates:
        AttendanceFactory(
            session=_conducted_session(date), student=student, status=Status.MEDICAL_LEAVE
        )

    with_leave = services.attendance_percentage(
        student, start, start + datetime.timedelta(weeks=20)
    )
    assert with_leave == baseline == 100


@pytest.mark.django_db
def test_unconducted_sessions_are_excluded():
    student = StudentFactory()
    start = datetime.date(2026, 1, 5)
    end = start + datetime.timedelta(weeks=4)

    AttendanceFactory(session=_conducted_session(start), student=student, status=Status.PRESENT)
    cancelled = TrainingSessionFactory(date=start + datetime.timedelta(weeks=1), is_conducted=False)
    AttendanceFactory(session=cancelled, student=student, status=Status.ABSENT)

    assert services.attendance_percentage(student, start, end) == 100


@pytest.mark.django_db
def test_attendance_percentage_with_no_conducted_sessions_is_none():
    student = StudentFactory()
    start = datetime.date(2026, 1, 5)
    assert services.attendance_percentage(student, start, start) is None


@pytest.mark.django_db
def test_mark_bulk_saves_the_others_when_one_student_fails():
    """Marking 22 students where 1 fails must save the other 21."""
    session = TrainingSessionFactory()
    good_students = [StudentFactory() for _ in range(5)]
    user = UserFactory()

    marks = [{"student": str(s.id), "status": Status.PRESENT} for s in good_students]
    marks.insert(2, {"student": "00000000-0000-0000-0000-000000000000", "status": Status.PRESENT})

    results = services.mark_bulk(session, marks, user)

    assert sum(1 for r in results if r["ok"]) == 5
    assert sum(1 for r in results if not r["ok"]) == 1
    assert Attendance.objects.filter(session=session).count() == 5


@pytest.mark.django_db
def test_mark_bulk_does_not_overwrite_an_existing_mark():
    session = TrainingSessionFactory()
    student = StudentFactory()
    user = UserFactory()
    AttendanceFactory(session=session, student=student, status=Status.PRESENT)

    results = services.mark_bulk(
        session, [{"student": str(student.id), "status": Status.ABSENT}], user
    )

    assert results[0]["ok"] is False
    attendance = Attendance.objects.get(session=session, student=student)
    assert attendance.status == Status.PRESENT  # unchanged


@pytest.mark.django_db
def test_mark_bulk_refuses_once_the_24_hour_window_has_closed():
    session = TrainingSessionFactory(date=timezone.localdate() - datetime.timedelta(days=2))
    student = StudentFactory()
    user = UserFactory()

    with pytest.raises(services.SessionWindowClosed):
        services.mark_bulk(session, [{"student": str(student.id), "status": Status.PRESENT}], user)

    assert not Attendance.objects.filter(session=session).exists()


@pytest.mark.django_db
def test_mark_bulk_refuses_a_session_that_has_not_started_yet():
    session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))
    student = StudentFactory()
    user = UserFactory()

    with pytest.raises(services.SessionNotYetStarted):
        services.mark_bulk(session, [{"student": str(student.id), "status": Status.PRESENT}], user)

    assert not Attendance.objects.filter(session=session).exists()


@pytest.mark.django_db
def test_mark_bulk_succeeds_within_the_24_hour_grace_window():
    """A session that started earlier today (not "today" by date alone)
    can still be marked — matches
    test_update_session_details_reschedules_within_the_24_hour_grace_window's
    reasoning for the shared boundary."""
    one_hour_ago = timezone.localtime() - datetime.timedelta(hours=1)
    session = TrainingSessionFactory(date=one_hour_ago.date(), start_time=one_hour_ago.time())
    student = StudentFactory()
    user = UserFactory()

    results = services.mark_bulk(
        session, [{"student": str(student.id), "status": Status.PRESENT}], user
    )

    assert results[0]["ok"] is True


@pytest.mark.django_db
def test_cancel_session_refuses_once_the_24_hour_window_has_closed():
    session = TrainingSessionFactory(date=timezone.localdate() - datetime.timedelta(days=2))

    with pytest.raises(services.SessionWindowClosed):
        services.cancel_session(session, reason="Rain.")

    session.refresh_from_db()
    assert session.cancel_reason == ""


@pytest.mark.django_db
def test_cancel_session_refuses_a_session_that_has_not_started_yet():
    """A future session isn't "cancelled" in this app's sense yet — it's
    just not-yet-happened. (Rescheduling it, or deleting it outright via
    delete_session, is the tool for that — see
    test_update_session_details_reschedules_a_future_unmarked_session.)"""
    session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))

    with pytest.raises(services.SessionNotYetStarted):
        services.cancel_session(session, reason="Rain expected.")

    session.refresh_from_db()
    assert session.cancel_reason == ""


@pytest.mark.django_db
def test_cancel_session_deletes_its_attendance_rows():
    """Nobody is absent from a session that did not happen."""
    session = TrainingSessionFactory(is_conducted=True)
    AttendanceFactory(session=session, status=Status.PRESENT)
    AttendanceFactory(session=session, status=Status.ABSENT)
    assert session.attendance_records.count() == 2

    services.cancel_session(session, reason="Rain.")

    session.refresh_from_db()
    assert session.is_conducted is False
    assert session.cancel_reason == "Rain."
    assert session.attendance_records.count() == 0


@pytest.mark.django_db
def test_mark_session_conducted_sets_is_conducted_true():
    session = TrainingSessionFactory(is_conducted=False)

    updated = services.mark_session_conducted(session)

    assert updated.is_conducted is True
    session.refresh_from_db()
    assert session.is_conducted is True


@pytest.mark.django_db
def test_mark_session_conducted_clears_a_previous_cancel_reason():
    """Un-cancels: a session cancelled in error can be marked conducted
    again within the same 24-hour window."""
    session = TrainingSessionFactory(is_conducted=False, cancel_reason="Rain.")

    services.mark_session_conducted(session)

    session.refresh_from_db()
    assert session.is_conducted is True
    assert session.cancel_reason == ""


@pytest.mark.django_db
def test_mark_session_conducted_refuses_once_the_24_hour_window_has_closed():
    session = TrainingSessionFactory(
        date=timezone.localdate() - datetime.timedelta(days=2), is_conducted=False
    )

    with pytest.raises(services.SessionWindowClosed):
        services.mark_session_conducted(session)

    session.refresh_from_db()
    assert session.is_conducted is False


@pytest.mark.django_db
def test_mark_session_conducted_refuses_a_session_that_has_not_started_yet():
    session = TrainingSessionFactory(
        date=timezone.localdate() + datetime.timedelta(days=7), is_conducted=False
    )

    with pytest.raises(services.SessionNotYetStarted):
        services.mark_session_conducted(session)

    session.refresh_from_db()
    assert session.is_conducted is False


@pytest.mark.django_db
def test_update_session_details_changes_content_fields_on_a_past_session():
    """training_type/objective/report stay editable even once a session
    is in the past — that's when a coach normally files the report."""
    session = TrainingSessionFactory(date=timezone.localdate() - datetime.timedelta(days=1))

    updated = services.update_session_details(session, {"objective": "Yorkers", "report": "Good."})

    updated.refresh_from_db()
    assert updated.objective == "Yorkers"
    assert updated.report == "Good."


@pytest.mark.django_db
def test_update_session_details_reschedules_a_future_unmarked_session():
    session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))
    new_date = timezone.localdate() + datetime.timedelta(days=8)

    services.update_session_details(session, {"date": new_date})

    session.refresh_from_db()
    assert session.date == new_date


@pytest.mark.django_db
def test_update_session_details_refuses_to_reschedule_a_past_session():
    # 2 days ago, not 1 — a session dated "yesterday" can still be inside
    # the 24-hour-after-start grace window depending on what time of day
    # this test happens to run, which would make this assertion flaky.
    session = TrainingSessionFactory(date=timezone.localdate() - datetime.timedelta(days=2))

    with pytest.raises(services.SessionNotEditable):
        services.update_session_details(
            session, {"date": timezone.localdate() + datetime.timedelta(days=1)}
        )


@pytest.mark.django_db
def test_update_session_details_reschedules_within_the_24_hour_grace_window():
    """A session that started an hour ago is still editable — the
    boundary is 24 hours after it *started*, not "today vs not today".
    `one_hour_ago`'s date/time are taken from the same shifted instant
    (not `today`'s date + `now - 1h`'s time) so this doesn't misbehave
    when the test happens to run just after local midnight.
    """
    one_hour_ago = timezone.localtime() - datetime.timedelta(hours=1)
    session = TrainingSessionFactory(date=one_hour_ago.date(), start_time=one_hour_ago.time())

    updated = services.update_session_details(session, {"end_time": datetime.time(19, 0)})

    updated.refresh_from_db()
    assert updated.end_time == datetime.time(19, 0)


@pytest.mark.django_db
def test_update_session_details_refuses_to_reschedule_once_attendance_exists():
    session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))
    AttendanceFactory(session=session, status=Status.PRESENT)

    with pytest.raises(services.SessionNotEditable):
        services.update_session_details(session, {"start_time": datetime.time(17, 0)})


@pytest.mark.django_db
def test_update_session_details_refuses_a_date_that_collides_with_another_session():
    batch = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7)).batch
    other = TrainingSessionFactory(
        batch=batch, date=timezone.localdate() + datetime.timedelta(days=8)
    )

    with pytest.raises(services.SessionDateConflict):
        services.update_session_details(
            other, {"date": timezone.localdate() + datetime.timedelta(days=7)}
        )


@pytest.mark.django_db
def test_delete_session_removes_a_future_unmarked_session():
    session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))
    session_id = session.id

    services.delete_session(session)

    assert not TrainingSession.objects.filter(id=session_id).exists()


@pytest.mark.django_db
def test_delete_session_refuses_a_past_session():
    # 2 days ago, not 1 — see test_update_session_details_refuses_to_reschedule_a_past_session.
    session = TrainingSessionFactory(date=timezone.localdate() - datetime.timedelta(days=2))

    with pytest.raises(services.SessionNotEditable):
        services.delete_session(session)


@pytest.mark.django_db
def test_delete_session_refuses_a_session_with_attendance_recorded():
    """Cancel it instead — deleting would silently destroy the
    attendance history (Attendance.session is on_delete=CASCADE)."""
    session = TrainingSessionFactory(date=timezone.localdate() + datetime.timedelta(days=7))
    AttendanceFactory(session=session, status=Status.PRESENT)

    with pytest.raises(services.SessionNotEditable):
        services.delete_session(session)

    assert TrainingSession.objects.filter(id=session.id).exists()


@pytest.mark.django_db
def test_request_correction_does_not_change_attendance_status():
    attendance = AttendanceFactory(status=Status.ABSENT)
    user = UserFactory()

    correction = services.request_correction(
        attendance, to_status=Status.PRESENT, reason="Marked in error.", user=user
    )

    attendance.refresh_from_db()
    assert attendance.status == Status.ABSENT
    assert correction.from_status == Status.ABSENT
    assert correction.to_status == Status.PRESENT
    assert correction.approved_by is None


@pytest.mark.django_db
def test_approve_correction_changes_attendance_status():
    attendance = AttendanceFactory(status=Status.ABSENT)
    requester = UserFactory()
    approver = UserFactory()
    correction = services.request_correction(
        attendance, to_status=Status.PRESENT, reason="Marked in error.", user=requester
    )

    services.approve_correction(correction, user=approver)

    attendance.refresh_from_db()
    correction.refresh_from_db()
    assert attendance.status == Status.PRESENT
    assert correction.status == CorrectionStatus.APPROVED
    assert correction.approved_by == approver
    assert correction.approved_at is not None


@pytest.mark.django_db
def test_reject_correction_leaves_attendance_untouched():
    """A rejected correction never happened as far as the attendance
    record is concerned — same separation request_correction() keeps."""
    attendance = AttendanceFactory(status=Status.ABSENT)
    correction = services.request_correction(
        attendance, to_status=Status.PRESENT, reason="Marked in error.", user=UserFactory()
    )
    decider = UserFactory()

    services.reject_correction(correction, user=decider)

    attendance.refresh_from_db()
    correction.refresh_from_db()
    assert attendance.status == Status.ABSENT
    assert correction.status == CorrectionStatus.REJECTED
    assert correction.approved_by == decider
    assert correction.approved_at is not None
