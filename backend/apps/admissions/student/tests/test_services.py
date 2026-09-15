import datetime

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.admissions.admission.models import AdmissionStep
from apps.admissions.admission.tests.factories import AdmissionFactory
from apps.admissions.student import services
from apps.admissions.student.models import StudentStatus
from apps.admissions.trial.tests.factories import TrialRegistrationFactory
from apps.core.models import ApprovalRule
from apps.core.services import approvals
from apps.core.state import InvalidTransition
from apps.core.tests.factories import ProgrammeFactory
from apps.iam.models import Role, User, UserRole
from apps.iam.tests.factories import UserFactory
from apps.people.models import Gender, Relationship, StudentGuardian
from apps.people.tests.factories import GuardianFactory, PersonFactory, StudentGuardianFactory

from .factories import StudentFactory


def _user_with_role(role_code: str):
    user = UserFactory()
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=role_code), valid_from=datetime.date(2020, 1, 1)
    )
    return user


@pytest.mark.django_db
def test_approve_admission_creates_a_student_and_history_row(seeded_roles):
    ApprovalRule.objects.update_or_create(
        module="admission",
        action="approve",
        defaults={"required_role": Role.objects.get(code="academy_head")},
    )
    # _guard_approved re-checks fee_payment_status itself (services.
    # record_payment's docstring), not just that the step says
    # fee_cleared — AdmissionFactory's own default is "pending". A real
    # `trial_registration`, not the factory's default None, so this test
    # actually exercises the trial-based path's approval requirement
    # rather than the direct-admission bypass (admission/state.py's
    # `_guard_approved`).
    admission = AdmissionFactory(
        step=AdmissionStep.FEE_CLEARED,
        fee_payment_status="paid",
        trial_registration=TrialRegistrationFactory(),
    )
    requester = UserFactory()
    approval_request = approvals.request(admission, "admission", "approve", requester)
    approver = _user_with_role("academy_head")
    approvals.decide(approval_request, approver, approve=True)

    student = services.approve_admission(admission, user=approver)

    assert student.student_code.startswith("ACA/")
    assert student.status == StudentStatus.ACTIVE
    admission.refresh_from_db()
    assert admission.step == AdmissionStep.APPROVED
    assert admission.approved_by_id == approver.id
    history = student.status_history.get()
    assert history.to_status == StudentStatus.ACTIVE
    assert history.from_status == ""


@pytest.mark.django_db
def test_approve_admission_without_a_decided_approval_is_rejected(seeded_roles):
    ApprovalRule.objects.update_or_create(
        module="admission",
        action="approve",
        defaults={"required_role": Role.objects.get(code="academy_head")},
    )
    admission = AdmissionFactory(step=AdmissionStep.FEE_CLEARED)

    with pytest.raises(InvalidTransition):
        services.approve_admission(admission, user=UserFactory())


@pytest.mark.django_db
def test_medical_hold_requires_medical_team_role(seeded_roles):
    student = StudentFactory(status=StudentStatus.ACTIVE)
    non_medical = _user_with_role("administration")

    with pytest.raises(PermissionDenied):
        services.change_status(
            student, to_status=StudentStatus.MEDICAL_HOLD, reason="Injury.", user=non_medical
        )

    medical = _user_with_role("medical_team")
    result = services.change_status(
        student, to_status=StudentStatus.MEDICAL_HOLD, reason="Hamstring injury.", user=medical
    )
    assert result["pending_approval"] is False
    student.refresh_from_db()
    assert student.status == StudentStatus.MEDICAL_HOLD


@pytest.mark.django_db
def test_every_status_transition_requires_a_reason(seeded_roles):
    student = StudentFactory(status=StudentStatus.ACTIVE)
    accounts = _user_with_role("accounts")

    with pytest.raises(ValidationError):
        services.change_status(student, to_status=StudentStatus.FEE_HOLD, reason="", user=accounts)


@pytest.mark.django_db
def test_suspension_requires_approval_before_it_takes_effect(seeded_roles):
    ApprovalRule.objects.update_or_create(
        module="students",
        action=StudentStatus.SUSPENDED,
        defaults={"required_role": Role.objects.get(code="academy_head")},
    )
    student = StudentFactory(status=StudentStatus.ACTIVE)
    requester = _user_with_role("administration")

    result = services.change_status(
        student,
        to_status=StudentStatus.SUSPENDED,
        reason="Repeated disciplinary breaches.",
        user=requester,
    )
    assert result["pending_approval"] is True
    student.refresh_from_db()
    assert student.status == StudentStatus.ACTIVE  # unchanged until approved

    from apps.core.models import ApprovalRequest

    approval_request = ApprovalRequest.objects.get(pk=result["approval_request_id"])
    approver = _user_with_role("academy_head")
    approvals.decide(approval_request, approver, approve=True)

    result = services.change_status(
        student,
        to_status=StudentStatus.SUSPENDED,
        reason="Repeated disciplinary breaches.",
        user=requester,
    )
    assert result["pending_approval"] is False
    student.refresh_from_db()
    assert student.status == StudentStatus.SUSPENDED


@pytest.mark.django_db
def test_withdrawn_to_active_is_not_a_transition(seeded_roles):
    student = StudentFactory(status=StudentStatus.WITHDRAWN)
    user = _user_with_role("administration")

    with pytest.raises(InvalidTransition):
        services.change_status(
            student, to_status=StudentStatus.ACTIVE, reason="Reconsidered.", user=user
        )


@pytest.mark.django_db
def test_re_admission_reuses_the_same_person(seeded_roles):
    person = PersonFactory()
    StudentFactory(person=person, status=StudentStatus.WITHDRAWN)
    requester = _user_with_role("administration")

    new_student = services.re_admit(
        person=person, programme=ProgrammeFactory(), requested_by=requester
    )

    assert new_student.person_id == person.id
    from apps.admissions.student.models import Student

    assert Student.objects.filter(person=person).count() == 2
    # The prior withdrawn record is untouched.
    assert Student.objects.filter(person=person, status=StudentStatus.WITHDRAWN).count() == 1


@pytest.mark.django_db
def test_re_admission_refuses_a_person_with_no_prior_enrolment(seeded_roles):
    person = PersonFactory()
    with pytest.raises(ValidationError):
        services.re_admit(person=person, programme=ProgrammeFactory(), requested_by=UserFactory())


@pytest.mark.django_db
def test_link_guardian_reuses_an_existing_person(seeded_roles):
    student = StudentFactory()
    existing_guardian_person = PersonFactory()

    student_guardian = services.link_guardian(
        student,
        person_id=str(existing_guardian_person.id),
        relationship=Relationship.MOTHER,
        is_primary=True,
        is_emergency_contact=True,
        grant_portal_access=True,
    )

    assert student_guardian.student_id == student.id
    assert student_guardian.guardian.person_id == existing_guardian_person.id
    assert student_guardian.is_primary is True
    assert User.objects.filter(person=existing_guardian_person).exists()


@pytest.mark.django_db
def test_link_guardian_creates_a_new_person_when_none_is_given(seeded_roles):
    student = StudentFactory()

    student_guardian = services.link_guardian(
        student,
        new_person={
            "first_name": "Anita",
            "last_name": "Ganguly",
            "date_of_birth": datetime.date(1985, 4, 12),
            "gender": Gender.FEMALE,
            "mobile": "+919812345678",
            "email": "",
        },
        relationship=Relationship.MOTHER,
        is_primary=False,
        is_emergency_contact=False,
        grant_portal_access=False,
    )

    assert student_guardian.guardian.person.first_name == "Anita"
    # grant_portal_access=False must not provision a login.
    assert not User.objects.filter(person=student_guardian.guardian.person).exists()


@pytest.mark.django_db
def test_link_guardian_refuses_the_student_as_their_own_guardian(seeded_roles):
    student = StudentFactory()

    with pytest.raises(ValidationError):
        services.link_guardian(
            student,
            person_id=str(student.person_id),
            relationship=Relationship.GUARDIAN,
        )


@pytest.mark.django_db
def test_link_guardian_surfaces_a_second_primary_guardian_as_a_400_not_a_500(seeded_roles):
    student = StudentFactory()
    StudentGuardianFactory(student=student, is_primary=True)

    with pytest.raises(ValidationError):
        services.link_guardian(
            student,
            person_id=str(PersonFactory().id),
            relationship=Relationship.FATHER,
            is_primary=True,
        )


@pytest.mark.django_db
def test_unlink_guardian_removes_the_mapping_but_not_the_guardian(seeded_roles):
    student = StudentFactory()
    guardian = GuardianFactory()
    link = StudentGuardianFactory(student=student, guardian=guardian)

    services.unlink_guardian(student, str(link.id))

    assert not StudentGuardian.objects.filter(pk=link.pk).exists()
    assert User.objects.filter(person=guardian.person).exists() is False


@pytest.mark.django_db
def test_grant_student_login_succeeds_with_a_distinct_mobile(seeded_roles):
    student = StudentFactory()

    user, created = services.grant_student_login(student, mobile="+919900011122")

    assert created is True
    assert user.person_id == student.person_id
    assert "student" in {role.code for role in user.current_roles()}


@pytest.mark.django_db
def test_grant_student_login_rejects_a_mobile_already_used_by_the_guardian(seeded_roles):
    guardian_person = PersonFactory(mobile="+919900099999")
    student = StudentFactory(person__mobile="+919900099999")
    services.link_guardian(
        student,
        person_id=str(guardian_person.id),
        relationship=Relationship.FATHER,
        grant_portal_access=True,
    )

    with pytest.raises(ValidationError):
        services.grant_student_login(student)
