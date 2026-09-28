"""GET /api/v1/dashboards/me — one dashboard per role, resolved from the
calling user's own roles, never from a client-supplied parameter.
"""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.admissions.admission.tests.factories import AdmissionFactory
from apps.admissions.document.tests.factories import DocumentFactory
from apps.admissions.enquiry.tests.factories import EnquiryFactory
from apps.admissions.student.tests.factories import StudentFactory
from apps.admissions.trial.tests.factories import (
    TrialAssessmentFactory,
    TrialRegistrationFactory,
    TrialResultFactory,
)
from apps.core.services import dashboards
from apps.core.tests.factories import ApprovalRequestFactory, ApprovalRuleFactory
from apps.iam.models import Permission, Role, RolePermission, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import (
    GuardianFactory,
    PersonFactory,
    StaffFactory,
    StudentGuardianFactory,
)

# get_or_create throughout, deliberately — these tests must work whether or
# not some other test in the same session already triggered the real
# seed_roles data (the `seeded_roles` fixture). A plain RoleFactory/
# PermissionFactory .create() would collide with a real seeded row via
# their unique constraints depending on test execution order; this module
# stays correct either way instead of depending on that ordering.


def _get_or_create_role(role_code: str) -> Role:
    role, _ = Role.objects.get_or_create(
        code=role_code, defaults={"name": role_code.replace("_", " ").title()}
    )
    return role


def _user_with_role(role_code, **kwargs):
    user = UserFactory(**kwargs)
    role = _get_or_create_role(role_code)
    UserRole.objects.create(user=user, role=role, valid_from=datetime.date(2020, 1, 1))
    return user


def _grant(role: Role, module: str, verb: str, scope: str = "all"):
    permission, _ = Permission.objects.get_or_create(module=module, verb=verb)
    RolePermission.objects.get_or_create(
        role=role, permission=permission, defaults={"scope": scope}
    )


def _coach_user():
    user = _user_with_role("coach", person=PersonFactory())
    StaffFactory(person=user.person)
    return user


def _student_user():
    from apps.admissions.student.tests.factories import StudentFactory

    user = _user_with_role("student", person=PersonFactory())
    StudentFactory(person=user.person)
    return user


def _parent_user():
    from apps.admissions.student.tests.factories import StudentFactory

    user = _user_with_role("parent", person=PersonFactory())
    guardian = GuardianFactory(person=user.person)
    StudentGuardianFactory(student=StudentFactory(), guardian=guardian)
    return user


EXPECTED_CARD_COUNT = {
    "administration": 4,
    "head_coach": 4,
    "coach": 3,  # the brief lists only 3 cards for Coach
    "academy_head": 4,
    "student": 3,  # + upcoming_sessions, attendance_trend
    "parent": 5,  # + children_attendance, children_attendance_this_month, upcoming_sessions
}

_SPECIAL_CASE_USERS = {
    "coach": _coach_user,
    "student": _student_user,
    "parent": _parent_user,
}


_EXPECTED_TILE_COUNTS = {
    # head_coach lost its "waiver_requests" tile — always 0 in practice
    # (nothing ever set trial_waiver_approval), and the field it queried
    # no longer exists post direct-admission redesign.
    "head_coach": 3,
    # + my_batch, attendance (this month)
    "student": 6,
}


@pytest.mark.django_db
def test_each_role_gets_its_own_shaped_payload():
    for role_code in dashboards.DASHBOARD_ROLE_PRIORITY:
        make_user = _SPECIAL_CASE_USERS.get(role_code, lambda code=role_code: _user_with_role(code))
        user = make_user()

        payload = dashboards.build_dashboard(user)

        assert payload["role"] == role_code
        assert len(payload["tiles"]) == _EXPECTED_TILE_COUNTS.get(role_code, 4)
        for tile in payload["tiles"]:
            assert set(tile) == {"key", "label", "value", "meta", "urgent"}
        assert len(payload["cards"]) == EXPECTED_CARD_COUNT[role_code]
        for card in payload["cards"]:
            assert set(card) == {"key", "title", "subtitle", "type", "items"}
            assert card["type"] in {"list", "table", "bars", "audit"}


@pytest.mark.django_db
def test_administration_tile_values_are_real_queries_not_hardcoded():
    admin = _user_with_role("administration")
    EnquiryFactory.create_batch(3, status="new")
    EnquiryFactory.create_batch(2, status="lost")  # must not count toward the tile

    payload = dashboards.build_dashboard(admin)

    tile = next(t for t in payload["tiles"] if t["key"] == "new_enquiries_this_week")
    assert tile["value"] == 3


@pytest.mark.django_db
def test_academy_head_approval_tile_reflects_a_real_pending_request():
    head = _user_with_role("academy_head")
    academy_head_role = _get_or_create_role("academy_head")
    _grant(academy_head_role, "admission", "approve")
    rule = ApprovalRuleFactory(
        module="admission", action="approve", required_role=academy_head_role
    )
    ApprovalRequestFactory(rule=rule)

    payload = dashboards.build_dashboard(head)

    tile = next(t for t in payload["tiles"] if t["key"] == "waiting_on_your_approval")
    assert tile["value"] == 1
    assert tile["urgent"] is True


@pytest.mark.django_db
def test_student_tiles_show_real_attendance_and_batch():
    from apps.academics.attendance.tests.factories import AttendanceFactory
    from apps.academics.batch.tests.factories import (
        BatchEnrollmentFactory,
        BatchFactory,
        TrainingSessionFactory,
    )

    user = _user_with_role("student", person=PersonFactory())
    student = StudentFactory(person=user.person)
    batch = BatchFactory(name="U-14 Morning")
    BatchEnrollmentFactory(student=student, batch=batch, is_active=True)

    today = timezone.localdate()
    session = TrainingSessionFactory(batch=batch, date=today, is_conducted=True)
    AttendanceFactory(session=session, student=student, status="present")

    payload = dashboards.build_dashboard(user)

    batch_tile = next(t for t in payload["tiles"] if t["key"] == "my_batch")
    assert batch_tile["value"] == "U-14 Morning"
    attendance_tile = next(t for t in payload["tiles"] if t["key"] == "attendance")
    assert attendance_tile["value"] == "100.00%"

    trend_card = next(c for c in payload["cards"] if c["key"] == "attendance_trend")
    assert trend_card["items"] == [{"label": today.strftime("%b %Y"), "value": 100.0}]


@pytest.mark.django_db
def test_parent_attendance_table_has_one_row_per_child():
    from apps.academics.batch.tests.factories import BatchEnrollmentFactory, BatchFactory

    user = _user_with_role("parent", person=PersonFactory())
    guardian = GuardianFactory(person=user.person)
    enrolled_child = StudentFactory()
    unenrolled_child = StudentFactory()
    StudentGuardianFactory(student=enrolled_child, guardian=guardian)
    StudentGuardianFactory(student=unenrolled_child, guardian=guardian)
    BatchEnrollmentFactory(
        student=enrolled_child, batch=BatchFactory(name="U-16 Evening"), is_active=True
    )

    payload = dashboards.build_dashboard(user)

    table = next(c for c in payload["cards"] if c["key"] == "children_attendance")
    rows = {row["child"]: row for row in table["items"]}
    assert len(rows) == 2
    enrolled_row = rows[f"{enrolled_child.person.first_name} {enrolled_child.person.last_name}"]
    assert enrolled_row["batch"] == "U-16 Evening"
    unenrolled_row = rows[
        f"{unenrolled_child.person.first_name} {unenrolled_child.person.last_name}"
    ]
    assert unenrolled_row["batch"] == "Not enrolled"


@pytest.mark.django_db
def test_multi_role_user_gets_the_highest_priority_dashboard():
    user = UserFactory()
    for code in ("coach", "administration"):
        UserRole.objects.create(
            user=user, role=_get_or_create_role(code), valid_from=datetime.date(2020, 1, 1)
        )

    role = dashboards.resolve_dashboard_role(user)

    # "administration" outranks "coach" in SOP §5's own role ordering.
    assert role == "administration"


@pytest.mark.django_db
def test_user_with_no_dashboarded_role_raises():
    user = UserFactory()
    UserRole.objects.create(
        user=user, role=_get_or_create_role("accounts"), valid_from=datetime.date(2020, 1, 1)
    )

    with pytest.raises(dashboards.NoDashboardForRole):
        dashboards.build_dashboard(user)


@pytest.mark.django_db
def test_coach_cannot_obtain_another_roles_payload_via_the_endpoint():
    coach = _coach_user()
    api_client = APIClient()
    api_client.force_authenticate(user=coach)

    response = api_client.get("/api/v1/dashboards/me/")

    assert response.status_code == 200
    assert response.data["role"] == "coach"
    card_keys = {card["key"] for card in response.data["cards"]}
    # Cards that only exist on other roles' dashboards.
    assert "approval_queue" not in card_keys
    assert "my_queue" not in card_keys
    assert "awaiting_your_decision" not in card_keys
    # No parameter on this endpoint lets the client ask for a role.
    response_with_role_param = api_client.get("/api/v1/dashboards/me/?role=academy_head")
    assert response_with_role_param.data["role"] == "coach"


@pytest.mark.django_db
def test_student_dashboard_reflects_their_own_documents_not_someone_elses():
    from apps.admissions.document.tests.factories import DocumentFactory

    student_user = _user_with_role("student", person=PersonFactory())
    student = StudentFactory(person=student_user.person, status="active")
    DocumentFactory(owner=student, status="verified")
    DocumentFactory(owner=student, status="submitted")
    DocumentFactory(owner=StudentFactory(), status="verified")  # someone else's — must not count

    payload = dashboards.build_dashboard(student_user)

    status_tile = next(t for t in payload["tiles"] if t["key"] == "status")
    assert status_tile["value"] == "active"
    docs_tile = next(t for t in payload["tiles"] if t["key"] == "documents_verified")
    assert docs_tile["value"] == "1/2"
    card = next(c for c in payload["cards"] if c["key"] == "my_documents")
    assert len(card["items"]) == 2


@pytest.mark.django_db
def test_parent_dashboard_only_counts_their_own_children():
    parent_user = _user_with_role("parent", person=PersonFactory())
    guardian = GuardianFactory(person=parent_user.person)
    own_child = StudentFactory()
    StudentGuardianFactory(student=own_child, guardian=guardian)
    StudentFactory()  # someone else's child — must not count

    payload = dashboards.build_dashboard(parent_user)

    tile = next(t for t in payload["tiles"] if t["key"] == "my_children")
    assert tile["value"] == 1
    card = next(c for c in payload["cards"] if c["key"] == "my_children")
    assert len(card["items"]) == 1
    assert card["items"][0]["student_code"] == own_child.student_code


@pytest.mark.django_db
def test_head_coach_sees_a_registration_needing_assessment():
    head_coach = _user_with_role("head_coach")
    reg = TrialRegistrationFactory(attended=True)

    payload = dashboards.build_dashboard(head_coach)

    tile = next(t for t in payload["tiles"] if t["key"] == "assessments_outstanding")
    assert tile["value"] == 1
    card = next(c for c in payload["cards"] if c["key"] == "awaiting_your_decision")
    assert any(item["key"] == f"assess-{reg.id}" for item in card["items"])


@pytest.mark.django_db
def test_full_response_round_trip_is_reasonably_fast():
    import time

    admin = _user_with_role("administration")
    EnquiryFactory.create_batch(20)
    for _ in range(10):
        reg = TrialRegistrationFactory(attended=True)
        TrialAssessmentFactory(registration=reg)
        TrialResultFactory(registration=reg, outcome="selected")
    for _ in range(5):
        AdmissionFactory()
    StudentFactory.create_batch(5)
    DocumentFactory.create_batch(5, status="submitted")

    api_client = APIClient()
    api_client.force_authenticate(user=admin)

    start = time.perf_counter()
    response = api_client.get("/api/v1/dashboards/me/")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    # Generous CI-safe ceiling — the 300ms budget from the brief is
    # verified separately against the full demo dataset (docs note).
    assert elapsed < 2.0, f"dashboard round trip took {elapsed:.2f}s"
