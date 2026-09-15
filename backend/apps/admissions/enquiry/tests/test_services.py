import datetime

import pytest

from apps.admissions.enquiry import services
from apps.admissions.enquiry.models import EnquiryStatus, FollowUpMode
from apps.core.tests.factories import EnquirySourceFactory
from apps.people.tests.factories import PersonFactory


@pytest.mark.django_db
def test_create_enquiry_mints_a_sequential_number():
    source = EnquirySourceFactory()
    enquiry, match = services.create_enquiry(
        {
            "student_name": "Arjun Ganguly",
            "date_of_birth": datetime.date(2014, 5, 1),
            "gender": "M",
            "guardian_name": "Suman Ganguly",
            "guardian_mobile": "9876543210",
            "source": source,
        }
    )

    assert enquiry.enquiry_no.startswith("ENQ/")
    assert enquiry.status == EnquiryStatus.NEW
    assert not match.found
    assert enquiry.person is None


@pytest.mark.django_db
def test_create_enquiry_auto_links_an_exact_dedupe_match():
    existing = PersonFactory(
        first_name="Arjun",
        last_name="Ganguly",
        date_of_birth=datetime.date(2014, 5, 1),
        mobile="+919876543210",
    )
    source = EnquirySourceFactory()

    enquiry, match = services.create_enquiry(
        {
            "student_name": "Arjun Ganguly",
            "date_of_birth": datetime.date(2014, 5, 1),
            "gender": "M",
            "guardian_name": "Suman Ganguly",
            "guardian_mobile": "9876543210",
            "source": source,
        }
    )

    assert match.exact == [existing]
    assert enquiry.person_id == existing.id


@pytest.mark.django_db
def test_add_follow_up_moves_a_new_enquiry_to_contacted():
    from apps.admissions.enquiry.tests.factories import EnquiryFactory
    from apps.iam.tests.factories import UserFactory

    enquiry = EnquiryFactory(status=EnquiryStatus.NEW)
    staff_user = UserFactory()

    follow_up = services.add_follow_up(
        enquiry,
        contacted_on=datetime.datetime(2026, 1, 10, 10, 0, tzinfo=datetime.UTC),
        mode=FollowUpMode.CALL,
        notes="Discussed trial slots.",
        next_action_on=datetime.date(2026, 1, 15),
        created_by=staff_user,
    )

    enquiry.refresh_from_db()
    assert enquiry.status == EnquiryStatus.CONTACTED
    assert follow_up.enquiry_id == enquiry.id


@pytest.mark.django_db
def test_add_follow_up_does_not_regress_a_later_status():
    from apps.admissions.enquiry.tests.factories import EnquiryFactory
    from apps.iam.tests.factories import UserFactory

    enquiry = EnquiryFactory(status=EnquiryStatus.TRIAL_SCHEDULED)
    staff_user = UserFactory()

    services.add_follow_up(
        enquiry,
        contacted_on=datetime.datetime(2026, 1, 10, 10, 0, tzinfo=datetime.UTC),
        mode=FollowUpMode.CALL,
        notes="",
        next_action_on=None,
        created_by=staff_user,
    )

    enquiry.refresh_from_db()
    assert enquiry.status == EnquiryStatus.TRIAL_SCHEDULED
