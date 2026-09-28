import datetime

import pytest
from rest_framework.test import APIClient

from apps.core.tests.factories import PaymentTypeFactory
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import PersonFactory

from .factories import PaymentFactory


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
def test_administration_can_record_a_payment(api_client, seeded_roles):
    """`payment:add` is Administration's role grant (docs/03-rbac.md) —
    the role a real Administration-desk staff member logs in with, not
    Django-admin/superuser access."""
    user = _user_with_role("administration")
    person = PersonFactory()
    payment_type = PaymentTypeFactory(is_recurring=True)
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/v1/payments/record/",
        {
            "person": str(person.id),
            "payment_type": str(payment_type.id),
            "billing_period": "2026-09-01",
            "amount": "3500.00",
            "payment_mode": "upi",
            "reference_no": "UTR123",
            "payment_date": datetime.date.today().isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.data["confirmation_no"].startswith("PCF/")
    assert response.data["status"] == "confirmed"


@pytest.mark.django_db
def test_student_cannot_record_a_payment(api_client, seeded_roles):
    """The `payment` row grants student/parent own-scope `view` only, no
    `add` — recording stays Administration/Accounts-only."""
    user = _user_with_role("student")
    person = PersonFactory()
    payment_type = PaymentTypeFactory(is_recurring=False)
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/v1/payments/record/",
        {
            "person": str(person.id),
            "payment_type": str(payment_type.id),
            "amount": "3500.00",
            "payment_mode": "upi",
            "payment_date": datetime.date.today().isoformat(),
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_accounts_can_settle_a_confirmed_payment(api_client, seeded_roles):
    user = _user_with_role("accounts")
    payment = PaymentFactory()
    api_client.force_authenticate(user)

    response = api_client.post(f"/api/v1/payments/{payment.id}/settle/")

    assert response.status_code == 200
    assert response.data["status"] == "settled"
    assert response.data["invoice_no"].startswith("INV/")


@pytest.mark.django_db
def test_coach_cannot_settle_a_payment(api_client, seeded_roles):
    user = _user_with_role("coach")
    payment = PaymentFactory()
    api_client.force_authenticate(user)

    response = api_client.post(f"/api/v1/payments/{payment.id}/settle/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_administration_can_list_payments(api_client, seeded_roles):
    """The staff operational queue — distinct from the self-service
    /students/me/payments/ and /parents/me/children/{id}/payments/
    summary endpoints."""
    user = _user_with_role("administration")
    PaymentFactory()
    PaymentFactory()
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/payments/")

    assert response.status_code == 200
    assert len(response.data["results"]) == 2


@pytest.mark.django_db
def test_list_can_be_filtered_by_status(api_client, seeded_roles):
    user = _user_with_role("accounts")
    confirmed = PaymentFactory()
    settled = PaymentFactory()
    from .. import services

    services.mark_settled(settled, user=user)
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/payments/?status=confirmed")

    ids = {row["id"] for row in response.data["results"]}
    assert str(confirmed.id) in ids
    assert str(settled.id) not in ids


@pytest.mark.django_db
def test_coach_cannot_list_payments(api_client, seeded_roles):
    user = _user_with_role("coach")
    PaymentFactory()
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/payments/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_current_fee_uses_the_day_scholar_amount_for_a_non_residential_student(
    api_client, seeded_roles
):
    from apps.academics.batch.tests.factories import BatchEnrollmentFactory, BatchFactory
    from apps.admissions.student.tests.factories import StudentFactory

    batch = BatchFactory(monthly_fee="3500.00", residential_monthly_fee="12000.00")
    student = StudentFactory(residential=False, person=PersonFactory())
    BatchEnrollmentFactory(student=student, batch=batch)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/payments/current-fee/?person={student.person_id}")

    assert response.status_code == 200
    assert response.data["amount"] == "3500.00"


@pytest.mark.django_db
def test_current_fee_uses_the_residential_amount_for_a_residential_student(
    api_client, seeded_roles
):
    from apps.academics.batch.tests.factories import BatchEnrollmentFactory, BatchFactory
    from apps.admissions.student.tests.factories import StudentFactory

    batch = BatchFactory(monthly_fee="3500.00", residential_monthly_fee="12000.00")
    student = StudentFactory(residential=True, person=PersonFactory())
    BatchEnrollmentFactory(student=student, batch=batch)
    user = _user_with_role("administration")
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/payments/current-fee/?person={student.person_id}")

    assert response.status_code == 200
    assert response.data["amount"] == "12000.00"


@pytest.mark.django_db
def test_current_fee_is_null_for_a_person_with_no_active_enrolment(api_client, seeded_roles):
    person = PersonFactory()
    user = _user_with_role("administration")
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/payments/current-fee/?person={person.id}")

    assert response.status_code == 200
    assert response.data["amount"] is None


@pytest.mark.django_db
def test_coach_cannot_read_current_fee(api_client, seeded_roles):
    person = PersonFactory()
    user = _user_with_role("coach")
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/payments/current-fee/?person={person.id}")

    assert response.status_code == 403


@pytest.mark.django_db
def test_student_listing_payments_sees_only_their_own(api_client, seeded_roles):
    """docs/03-rbac.md: student/parent hold own-scope `V` on `payment`,
    not all-scope like Administration/Accounts — GET /payments/ must not
    hand a Student everyone else's amounts, payment modes and reference
    numbers just because the permission itself exists."""
    own_person = PersonFactory()
    own_payment = PaymentFactory(person=own_person)
    PaymentFactory()  # someone else's — must not appear
    student_user = UserFactory(person=own_person)
    UserRole.objects.create(
        user=student_user,
        role=Role.objects.get(code="student"),
        valid_from=datetime.date(2020, 1, 1),
    )
    api_client.force_authenticate(student_user)

    response = api_client.get("/api/v1/payments/")

    assert response.status_code == 200
    ids = {row["id"] for row in response.data["results"]}
    assert ids == {str(own_payment.id)}


@pytest.mark.django_db
def test_parent_listing_payments_sees_only_their_childs(api_client, seeded_roles):
    from apps.admissions.student.tests.factories import StudentFactory
    from apps.people.tests.factories import GuardianFactory, StudentGuardianFactory

    child_person = PersonFactory()
    child_payment = PaymentFactory(person=child_person)
    PaymentFactory()  # unrelated family — must not appear
    student = StudentFactory(person=child_person)
    guardian_person = PersonFactory()
    guardian = GuardianFactory(person=guardian_person)
    StudentGuardianFactory(student=student, guardian=guardian, is_primary=True)
    parent_user = UserFactory(person=guardian_person)
    UserRole.objects.create(
        user=parent_user, role=Role.objects.get(code="parent"), valid_from=datetime.date(2020, 1, 1)
    )
    api_client.force_authenticate(parent_user)

    response = api_client.get("/api/v1/payments/")

    assert response.status_code == 200
    ids = {row["id"] for row in response.data["results"]}
    assert ids == {str(child_payment.id)}


@pytest.mark.django_db
def test_a_student_with_no_person_sees_no_payments(api_client, seeded_roles):
    """A User with no linked Person (shouldn't normally happen for a
    student role, but the own-scope filter must fail closed, not open,
    if it ever does)."""
    PaymentFactory()
    user = UserFactory(person=None)
    UserRole.objects.create(
        user=user, role=Role.objects.get(code="student"), valid_from=datetime.date(2020, 1, 1)
    )
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/payments/")

    assert response.status_code == 200
    assert response.data["results"] == []


@pytest.mark.django_db
def test_administration_can_download_a_receipt_for_a_confirmed_payment(api_client, seeded_roles):
    user = _user_with_role("administration")
    payment = PaymentFactory()
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/payments/{payment.id}/receipt.pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert payment.confirmation_no in response["Content-Disposition"]


@pytest.mark.django_db
def test_receipt_is_refused_for_a_voided_payment(api_client, seeded_roles):
    from .. import services

    user = _user_with_role("administration")
    payment = PaymentFactory()
    services.void_payment(payment, user=user, reason="Duplicate entry.")
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/payments/{payment.id}/receipt.pdf/")

    assert response.status_code == 409


@pytest.mark.django_db
def test_invoice_is_refused_before_settlement(api_client, seeded_roles):
    user = _user_with_role("administration")
    payment = PaymentFactory()
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/payments/{payment.id}/invoice.pdf/")

    assert response.status_code == 409


@pytest.mark.django_db
def test_invoice_is_available_once_settled(api_client, seeded_roles):
    from .. import services

    user = _user_with_role("accounts")
    payment = PaymentFactory()
    services.mark_settled(payment, user=user)
    api_client.force_authenticate(user)

    response = api_client.get(f"/api/v1/payments/{payment.id}/invoice.pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    payment.refresh_from_db()
    assert payment.invoice_no in response["Content-Disposition"]


@pytest.mark.django_db
def test_student_can_download_their_own_receipt(api_client, seeded_roles):
    own_person = PersonFactory()
    payment = PaymentFactory(person=own_person)
    student_user = UserFactory(person=own_person)
    UserRole.objects.create(
        user=student_user,
        role=Role.objects.get(code="student"),
        valid_from=datetime.date(2020, 1, 1),
    )
    api_client.force_authenticate(student_user)

    response = api_client.get(f"/api/v1/payments/{payment.id}/receipt.pdf/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_student_cannot_download_someone_elses_receipt(api_client, seeded_roles):
    payment = PaymentFactory()
    student_user = UserFactory(person=PersonFactory())
    UserRole.objects.create(
        user=student_user,
        role=Role.objects.get(code="student"),
        valid_from=datetime.date(2020, 1, 1),
    )
    api_client.force_authenticate(student_user)

    response = api_client.get(f"/api/v1/payments/{payment.id}/receipt.pdf/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_parent_can_download_their_childs_receipt(api_client, seeded_roles):
    from apps.admissions.student.tests.factories import StudentFactory
    from apps.people.tests.factories import GuardianFactory, StudentGuardianFactory

    child_person = PersonFactory()
    payment = PaymentFactory(person=child_person)
    student = StudentFactory(person=child_person)
    guardian_person = PersonFactory()
    guardian = GuardianFactory(person=guardian_person)
    StudentGuardianFactory(student=student, guardian=guardian, is_primary=True)
    parent_user = UserFactory(person=guardian_person)
    UserRole.objects.create(
        user=parent_user, role=Role.objects.get(code="parent"), valid_from=datetime.date(2020, 1, 1)
    )
    api_client.force_authenticate(parent_user)

    response = api_client.get(f"/api/v1/payments/{payment.id}/receipt.pdf/")

    assert response.status_code == 200

