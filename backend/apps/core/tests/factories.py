import datetime

import factory
from factory.django import DjangoModelFactory

from apps.core.models import (
    AgeCategory,
    ApprovalRequest,
    ApprovalRule,
    AssessmentCriterion,
    AssessmentCriterionGroup,
    ConsentType,
    DocumentApplicability,
    DocumentType,
    EnquirySource,
    FeeHead,
    Programme,
    Season,
    Venue,
)
from apps.iam.tests.factories import RoleFactory, UserFactory
from apps.people.tests.factories import PersonFactory


class ProgrammeFactory(DjangoModelFactory):
    class Meta:
        model = Programme

    code = factory.Sequence(lambda n: f"programme-{n}")
    name = factory.Sequence(lambda n: f"Programme {n}")


class AgeCategoryFactory(DjangoModelFactory):
    class Meta:
        model = AgeCategory

    code = factory.Sequence(lambda n: f"age-category-{n}")
    name = factory.Sequence(lambda n: f"Age Category {n}")
    min_age = 8
    max_age = 19
    as_on_date_rule = "09-01"


class SeasonFactory(DjangoModelFactory):
    class Meta:
        model = Season

    code = factory.Sequence(lambda n: f"season-{n}")
    name = factory.Sequence(lambda n: f"Season {n}")
    start_date = datetime.date(2026, 4, 1)
    end_date = datetime.date(2027, 3, 31)
    age_cutoff_date = datetime.date(2026, 4, 1)


class FeeHeadFactory(DjangoModelFactory):
    class Meta:
        model = FeeHead

    code = factory.Sequence(lambda n: f"fee-head-{n}")
    label = factory.Sequence(lambda n: f"Fee Head {n}")
    is_mandatory = True


class ConsentTypeFactory(DjangoModelFactory):
    class Meta:
        model = ConsentType

    code = factory.Sequence(lambda n: f"consent-{n}")
    label = factory.Sequence(lambda n: f"Consent {n}")
    body_text = "Sample consent body text."
    version = "1.0"
    is_mandatory = True


class VenueFactory(DjangoModelFactory):
    class Meta:
        model = Venue

    code = factory.Sequence(lambda n: f"venue-{n}")
    name = factory.Sequence(lambda n: f"Venue {n}")


class EnquirySourceFactory(DjangoModelFactory):
    class Meta:
        model = EnquirySource

    code = factory.Sequence(lambda n: f"source-{n}")
    name = factory.Sequence(lambda n: f"Source {n}")


class DocumentTypeFactory(DjangoModelFactory):
    class Meta:
        model = DocumentType

    code = factory.Sequence(lambda n: f"doctype-{n}")
    name = factory.Sequence(lambda n: f"Document type {n}")
    applies_to = DocumentApplicability.STUDENT


class AssessmentCriterionFactory(DjangoModelFactory):
    class Meta:
        model = AssessmentCriterion

    code = factory.Sequence(lambda n: f"criterion-{n}")
    name = factory.Sequence(lambda n: f"Criterion {n}")
    group = AssessmentCriterionGroup.BATTING
    scale_min = 0
    scale_max = 10


class ApprovalRuleFactory(DjangoModelFactory):
    class Meta:
        model = ApprovalRule

    module = factory.Sequence(lambda n: f"module_{n}")
    action = "approve"
    required_role = factory.SubFactory(RoleFactory)
    threshold = None


class ApprovalRequestFactory(DjangoModelFactory):
    class Meta:
        model = ApprovalRequest

    rule = factory.SubFactory(ApprovalRuleFactory)
    subject = factory.SubFactory(PersonFactory)
    requested_by = factory.SubFactory(UserFactory)
