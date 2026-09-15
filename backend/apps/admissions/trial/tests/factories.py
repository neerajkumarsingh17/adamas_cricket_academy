import factory
from factory.django import DjangoModelFactory

from apps.admissions.enquiry.tests.factories import EnquiryFactory
from apps.admissions.trial.models import (
    TrialAssessment,
    TrialAssessmentScore,
    TrialOutcome,
    TrialRegistration,
    TrialResult,
    TrialSlot,
)
from apps.core.tests.factories import AgeCategoryFactory, AssessmentCriterionFactory, VenueFactory
from apps.people.tests.factories import StaffFactory


class TrialSlotFactory(DjangoModelFactory):
    class Meta:
        model = TrialSlot

    date = factory.Faker("future_date")
    venue = factory.SubFactory(VenueFactory)
    reporting_time = "07:00"
    age_category = factory.SubFactory(AgeCategoryFactory)
    capacity = 20


class TrialRegistrationFactory(DjangoModelFactory):
    class Meta:
        model = TrialRegistration

    trial_id = factory.Sequence(lambda n: f"TRL/2627/{n:05d}")
    enquiry = factory.SubFactory(EnquiryFactory)
    slot = factory.SubFactory(TrialSlotFactory)


class TrialAssessmentFactory(DjangoModelFactory):
    class Meta:
        model = TrialAssessment

    registration = factory.SubFactory(TrialRegistrationFactory)
    assessed_by = factory.SubFactory(StaffFactory)


class TrialAssessmentScoreFactory(DjangoModelFactory):
    class Meta:
        model = TrialAssessmentScore

    assessment = factory.SubFactory(TrialAssessmentFactory)
    criterion = factory.SubFactory(AssessmentCriterionFactory)
    score = 7


class TrialResultFactory(DjangoModelFactory):
    class Meta:
        model = TrialResult

    registration = factory.SubFactory(TrialRegistrationFactory)
    outcome = TrialOutcome.SELECTED
