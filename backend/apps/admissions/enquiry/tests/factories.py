import datetime

import factory
from factory.django import DjangoModelFactory

from apps.admissions.enquiry.models import Enquiry, EnquiryFollowUp, FollowUpMode, PlayingRole
from apps.core.tests.factories import EnquirySourceFactory
from apps.people.models import Gender


class EnquiryFactory(DjangoModelFactory):
    class Meta:
        model = Enquiry

    enquiry_no = factory.Sequence(lambda n: f"ENQ/2627/{n:05d}")
    student_name = factory.Faker("name")
    date_of_birth = factory.Faker("date_of_birth", minimum_age=8, maximum_age=18)
    gender = Gender.OTHER
    guardian_name = factory.Faker("name")
    guardian_mobile = factory.Sequence(lambda n: f"90000{n:05d}")
    playing_role = PlayingRole.ALL_ROUNDER
    source = factory.SubFactory(EnquirySourceFactory)


class EnquiryFollowUpFactory(DjangoModelFactory):
    class Meta:
        model = EnquiryFollowUp

    enquiry = factory.SubFactory(EnquiryFactory)
    contacted_on = factory.Faker("date_time_this_month", tzinfo=datetime.UTC)
    mode = FollowUpMode.CALL
