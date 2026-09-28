import datetime

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.admissions.student.tests.factories import StudentFactory
from apps.core.tests.factories import AgeCategoryFactory, TrainingTypeFactory, VenueFactory
from apps.people.tests.factories import StaffFactory

from ..models import Batch, BatchEnrollment, Coach, TrainingSession


class CoachFactory(DjangoModelFactory):
    class Meta:
        model = Coach

    staff = factory.SubFactory(StaffFactory)
    specialisation = "Batting"
    experience_years = 5


class BatchFactory(DjangoModelFactory):
    class Meta:
        model = Batch

    name = factory.Sequence(lambda n: f"Batch {n}")
    age_category = factory.SubFactory(AgeCategoryFactory)
    coach = factory.SubFactory(CoachFactory)
    venue = factory.SubFactory(VenueFactory)
    capacity = 20
    weekdays = "1,3,5"
    start_time = datetime.time(16, 0)
    end_time = datetime.time(18, 0)
    monthly_fee = "3500.00"
    residential_monthly_fee = "12000.00"


class BatchEnrollmentFactory(DjangoModelFactory):
    class Meta:
        model = BatchEnrollment

    student = factory.SubFactory(StudentFactory)
    batch = factory.SubFactory(BatchFactory)
    from_date = datetime.date(2026, 4, 1)


class TrainingSessionFactory(DjangoModelFactory):
    class Meta:
        model = TrainingSession

    batch = factory.SubFactory(BatchFactory)
    # "Started an hour ago", not a hardcoded calendar date and not a fixed
    # future offset. A hardcoded absolute date (this used to be
    # 2026-04-01 + n) silently drifts into the past as real time moves on
    # — that broke every test relying on a fresh TrainingSessionFactory()
    # session being "not yet happened". A same-day-but-future offset
    # (this was briefly `today + n`) breaks the opposite way: it fails
    # apps.academics.attendance.services._assert_within_mark_window's
    # lower bound, which refuses to mark/cancel/conduct a session before
    # it has actually started — every bare TrainingSessionFactory() call
    # is exactly the kind of session those services need to accept by
    # default. "An hour ago" satisfies both: already started (passes the
    # lower bound), and nowhere near the 24-hour close. date/start_time
    # are both taken from the same already-shifted instant, not `today`'s
    # date + `now - 1h`'s time, so this doesn't misbehave when tests
    # happen to run just after local midnight.
    date = factory.LazyFunction(lambda: (timezone.localtime() - datetime.timedelta(hours=1)).date())
    start_time = factory.LazyFunction(
        lambda: (timezone.localtime() - datetime.timedelta(hours=1)).time()
    )
    end_time = datetime.time(18, 0)
    coach = factory.SubFactory(CoachFactory)
    training_type = factory.SubFactory(TrainingTypeFactory)
