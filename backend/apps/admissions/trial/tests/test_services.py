import datetime

import pytest

from apps.admissions.enquiry.tests.factories import EnquiryFactory
from apps.admissions.trial import services
from apps.admissions.trial.models import TrialOutcome, TrialRegistration, TrialResult
from apps.core.tests.factories import AssessmentCriterionFactory
from apps.iam.tests.factories import UserFactory
from apps.people.tests.factories import StaffFactory

from .factories import TrialRegistrationFactory, TrialSlotFactory


@pytest.mark.django_db
def test_register_from_enquiry_creates_a_person_and_increments_booked_count():
    enquiry = EnquiryFactory(guardian_mobile="9876543211")
    slot = TrialSlotFactory(capacity=2, booked_count=0)

    registration = services.register_from_enquiry(enquiry, slot.id)

    assert registration.trial_id.startswith("TRL/")
    assert registration.person is not None
    slot.refresh_from_db()
    assert slot.booked_count == 1
    enquiry.refresh_from_db()
    assert enquiry.person_id == registration.person_id
    assert enquiry.status == "trial_scheduled"


@pytest.mark.django_db
def test_register_from_enquiry_refuses_when_slot_is_full():
    enquiry = EnquiryFactory()
    slot = TrialSlotFactory(capacity=1, booked_count=1)

    with pytest.raises(services.TrialSlotFull):
        services.register_from_enquiry(enquiry, slot.id)


@pytest.mark.django_db
def test_register_from_enquiry_reuses_an_already_resolved_person():
    from apps.people.tests.factories import PersonFactory

    person = PersonFactory()
    enquiry = EnquiryFactory(person=person)
    slot = TrialSlotFactory(capacity=1, booked_count=0)

    registration = services.register_from_enquiry(enquiry, slot.id)

    assert registration.person_id == person.id


@pytest.mark.django_db
def test_submit_assessment_then_resubmit_upserts_the_same_row():
    registration = TrialRegistrationFactory()
    coach = StaffFactory()
    criterion = AssessmentCriterionFactory()

    first = services.submit_assessment(
        registration,
        assessed_by=coach,
        overall_remarks="Good technique.",
        scores=[{"criterion": criterion.id, "score": 6}],
    )
    second = services.submit_assessment(
        registration,
        assessed_by=coach,
        overall_remarks="Good technique, improved footwork.",
        scores=[{"criterion": criterion.id, "score": 8}],
    )

    assert first.id == second.id
    assert TrialRegistration.objects.get(pk=registration.pk).assessment.scores.count() == 1
    assert second.scores.get(criterion=criterion).score == 8


@pytest.mark.django_db
def test_submit_assessment_is_rejected_once_locked():
    registration = TrialRegistrationFactory()
    coach = StaffFactory()
    services.submit_assessment(registration, assessed_by=coach, overall_remarks="", scores=[])
    services.declare_result(registration, outcome=TrialOutcome.SELECTED, declared_by=UserFactory())

    with pytest.raises(services.AssessmentLocked):
        services.submit_assessment(registration, assessed_by=coach, overall_remarks="", scores=[])


@pytest.mark.django_db
def test_declare_result_requires_review_on_for_waitlisted():
    from rest_framework.exceptions import ValidationError

    registration = TrialRegistrationFactory()

    with pytest.raises(ValidationError):
        services.declare_result(
            registration, outcome=TrialOutcome.WAITLISTED, declared_by=UserFactory()
        )


@pytest.mark.django_db
def test_declare_result_closes_the_enquiry_as_lost_when_not_selected():
    registration = TrialRegistrationFactory()

    services.declare_result(
        registration, outcome=TrialOutcome.NOT_SELECTED, declared_by=UserFactory()
    )

    registration.enquiry.refresh_from_db()
    assert registration.enquiry.status == "lost"


@pytest.mark.django_db
def test_declare_result_twice_is_rejected():
    registration = TrialRegistrationFactory()
    services.declare_result(registration, outcome=TrialOutcome.SELECTED, declared_by=UserFactory())

    with pytest.raises(services.ResultAlreadyDeclared):
        services.declare_result(
            registration, outcome=TrialOutcome.SELECTED, declared_by=UserFactory()
        )


@pytest.mark.django_db
def test_a_waitlisted_result_can_later_be_resolved_to_selected():
    registration = TrialRegistrationFactory()
    services.declare_result(
        registration,
        outcome=TrialOutcome.WAITLISTED,
        declared_by=UserFactory(),
        review_on=datetime.date(2026, 12, 1),
    )

    result = services.declare_result(
        registration, outcome=TrialOutcome.SELECTED, declared_by=UserFactory()
    )

    assert result.outcome == TrialOutcome.SELECTED
    assert TrialResult.objects.filter(registration=registration).count() == 1


@pytest.mark.django_db
def test_a_resolved_waitlisted_result_cannot_be_redeclared_again():
    registration = TrialRegistrationFactory()
    services.declare_result(
        registration,
        outcome=TrialOutcome.WAITLISTED,
        declared_by=UserFactory(),
        review_on=datetime.date(2026, 12, 1),
    )
    services.declare_result(registration, outcome=TrialOutcome.SELECTED, declared_by=UserFactory())

    with pytest.raises(services.ResultAlreadyDeclared):
        services.declare_result(
            registration, outcome=TrialOutcome.NOT_SELECTED, declared_by=UserFactory()
        )


@pytest.mark.django_db
def test_declare_result_sends_a_notification(settings):
    from apps.engagement.communication.tests.factories import NotificationTemplateFactory

    NotificationTemplateFactory(
        code="trial_result_selected", body="Congratulations {{ student_name }}!"
    )
    registration = TrialRegistrationFactory()

    services.declare_result(registration, outcome=TrialOutcome.SELECTED, declared_by=UserFactory())

    from apps.engagement.communication.models import NotificationLog

    assert NotificationLog.objects.filter(recipient=registration.enquiry.guardian_mobile).exists()
