import datetime

import factory
from factory.django import DjangoModelFactory

from apps.admissions.admission.models import (
    Admission,
    AdmissionCategory,
    AdmissionChecklistItem,
    AdmissionIntake,
    AdmissionSource,
    ConsentRecord,
    DaysPerWeek,
    PreferredSlot,
)
from apps.admissions.enquiry.tests.factories import EnquiryFactory
from apps.core.tests.factories import (
    AgeCategoryFactory,
    ConsentTypeFactory,
    DocumentTypeFactory,
    ProgrammeFactory,
    SeasonFactory,
)
from apps.people.models import Gender, Relationship
from apps.people.tests.factories import PersonFactory


class AdmissionFactory(DjangoModelFactory):
    class Meta:
        model = Admission

    application_no = factory.Sequence(lambda n: f"ADM/2627/{n:05d}")
    person = factory.SubFactory(PersonFactory)
    programme = factory.SubFactory(ProgrammeFactory)
    # source defaults to ENQUIRY (the model default), and the new
    # CheckConstraint (admission_source_matches_enquiry_and_trial) requires
    # enquiry_id NOT NULL whenever source=ENQUIRY — every real
    # enquiry/trial-based Admission already has one (open_admission() sets
    # it from trial_registration.enquiry), so the factory default should
    # too, or a bare AdmissionFactory() now fails the constraint at the DB.
    enquiry = factory.SubFactory(EnquiryFactory)


class DirectAdmissionFactory(AdmissionFactory):
    """A source=DIRECT admission, as the CheckConstraint requires: no
    enquiry, no trial_registration, no person/programme until approval.
    """

    person = None
    programme = None
    enquiry = None
    source = AdmissionSource.DIRECT
    direct_admission_reason = "Reputation admission — district-level player."


class AdmissionIntakeFactory(DjangoModelFactory):
    class Meta:
        model = AdmissionIntake

    admission = factory.SubFactory(DirectAdmissionFactory)
    season = factory.SubFactory(SeasonFactory)
    admission_category = AdmissionCategory.NON_RESIDENTIAL
    days_per_week = DaysPerWeek.THREE
    preferred_slot = PreferredSlot.EVENING
    full_name = factory.Sequence(lambda n: f"Candidate {n}")
    date_of_birth = datetime.date(2014, 6, 15)
    # age_category is computed in save() — a placeholder SubFactory here
    # just satisfies the required FK before save() overwrites it.
    age_category = factory.SubFactory(AgeCategoryFactory)
    gender = Gender.MALE
    present_address = "123 MG Road"
    city = "Kolkata"
    state = "West Bengal"
    pin_code = "700001"
    guardian_name = "Guardian Name"
    guardian_relationship = Relationship.FATHER
    guardian_mobile = "+919800000001"
    guardian_date_of_birth = datetime.date(1985, 3, 10)
    guardian_gender = Gender.FEMALE
    emergency_contact = "+919800000002"


class AdmissionChecklistItemFactory(DjangoModelFactory):
    class Meta:
        model = AdmissionChecklistItem

    admission = factory.SubFactory(AdmissionFactory)
    document_type = factory.SubFactory(DocumentTypeFactory)


class ConsentRecordFactory(DjangoModelFactory):
    class Meta:
        model = ConsentRecord

    admission = factory.SubFactory(DirectAdmissionFactory)
    consent_type = factory.SubFactory(ConsentTypeFactory)
    granted = True
    version = "1.0"
    granted_at = factory.LazyFunction(datetime.datetime.now)
    declared_by_name = "Guardian Name"
