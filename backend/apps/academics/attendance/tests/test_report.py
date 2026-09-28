import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.academics.batch.tests.factories import (
    BatchEnrollmentFactory,
    BatchFactory,
    TrainingSessionFactory,
)
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory

from .. import services
from ..models import Status
from .factories import AttendanceFactory


def _user_with_role(role_code: str):
    user = UserFactory()
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=role_code), valid_from=datetime.date(2020, 1, 1)
    )
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_report_percentage_is_attendance_percentage_not_a_recompute():
    """Row totals come from attendance_percentage() — the only place the
    formula exists — so the report can never disagree with the portal."""
    batch = BatchFactory()
    enrollment = BatchEnrollmentFactory(batch=batch, from_date=datetime.date(2026, 3, 1))
    student = enrollment.student
    month = datetime.date(2026, 4, 1)

    dates = [datetime.date(2026, 4, d) for d in (1, 3, 8, 10)]
    statuses = [Status.PRESENT, Status.PRESENT, Status.ABSENT, Status.MEDICAL_LEAVE]
    for date, status in zip(dates, statuses, strict=True):
        session = TrainingSessionFactory(batch=batch, date=date, is_conducted=True)
        AttendanceFactory(session=session, student=student, status=status)

    report = services.monthly_report(batch, month)

    row = next(r for r in report["rows"] if r["student_id"] == str(student.id))
    expected = services.attendance_percentage(student, month, datetime.date(2026, 4, 30))
    assert row["percentage"] == expected
    # 2 present of 3 counted (medical leave excluded from the denominator).
    assert expected == Decimal("66.67")


@pytest.mark.django_db
def test_cancelled_sessions_appear_as_columns_with_null_marks():
    """A cancelled session is a column, not an absence — it's present in
    `sessions` (so the grid can grey it) and every row's mark for that
    date is null, never "absent"."""
    batch = BatchFactory()
    enrollment = BatchEnrollmentFactory(batch=batch, from_date=datetime.date(2026, 3, 1))
    month = datetime.date(2026, 4, 1)
    conducted = TrainingSessionFactory(
        batch=batch, date=datetime.date(2026, 4, 1), is_conducted=True
    )
    TrainingSessionFactory(batch=batch, date=datetime.date(2026, 4, 3), is_conducted=False)
    AttendanceFactory(session=conducted, student=enrollment.student, status=Status.PRESENT)

    report = services.monthly_report(batch, month)

    assert [s["date"] for s in report["sessions"]] == ["2026-04-01", "2026-04-03"]
    assert [s["is_conducted"] for s in report["sessions"]] == [True, False]
    row = report["rows"][0]
    assert row["marks"]["2026-04-01"] == Status.PRESENT
    assert row["marks"]["2026-04-03"] is None


@pytest.mark.django_db
def test_report_only_includes_students_enrolled_during_the_month():
    batch = BatchFactory()
    month = datetime.date(2026, 4, 1)
    current = BatchEnrollmentFactory(batch=batch, from_date=datetime.date(2026, 3, 1))
    # Left before the month started — not a row.
    BatchEnrollmentFactory(
        batch=batch,
        from_date=datetime.date(2026, 1, 1),
        to_date=datetime.date(2026, 2, 28),
        is_active=False,
    )
    # Joins after the month ended — not a row either.
    BatchEnrollmentFactory(batch=batch, from_date=datetime.date(2026, 5, 1))

    report = services.monthly_report(batch, month)

    assert [r["student_id"] for r in report["rows"]] == [str(current.student_id)]


@pytest.mark.django_db
def test_report_endpoint_requires_a_month(api_client, seeded_roles):
    user = _user_with_role("head_coach")
    batch = BatchFactory()
    api_client.force_authenticate(user)

    assert api_client.get(f"/api/v1/batches/{batch.id}/attendance-report/").status_code == 400
    assert (
        api_client.get(f"/api/v1/batches/{batch.id}/attendance-report/?month=nope").status_code
        == 400
    )
    ok = api_client.get(f"/api/v1/batches/{batch.id}/attendance-report/?month=2026-04")
    assert ok.status_code == 200
    assert ok.data["month"] == "2026-04"


@pytest.mark.django_db
def test_student_cannot_read_the_report(api_client, seeded_roles):
    """`attendance` grants student own-scope view only; the report is a
    staff screen and filter_to_own returns nothing."""
    user = _user_with_role("student")
    batch = BatchFactory()
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/batches/{batch.id}/attendance-report/?month=2026-04")

    assert response.status_code == 404
