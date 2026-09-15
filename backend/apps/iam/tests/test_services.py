import pytest
from rest_framework.exceptions import ValidationError

from apps.iam.models import User
from apps.iam.services import get_or_create_user_for_person
from apps.people.tests.factories import PersonFactory


@pytest.mark.django_db
def test_creates_a_user_and_role_for_a_new_person(seeded_roles):
    person = PersonFactory()

    user, created = get_or_create_user_for_person(person, role_code="parent")

    assert created is True
    assert user.person_id == person.id
    assert user.login_id == person.mobile
    assert not user.has_usable_password()
    assert "parent" in {role.code for role in user.current_roles()}


@pytest.mark.django_db
def test_is_idempotent_for_a_person_who_already_has_a_user(seeded_roles):
    person = PersonFactory()
    first_user, _ = get_or_create_user_for_person(person, role_code="parent")

    second_user, created = get_or_create_user_for_person(person, role_code="parent")

    assert created is False
    assert second_user.id == first_user.id
    assert User.objects.filter(person=person).count() == 1


@pytest.mark.django_db
def test_adding_a_second_role_to_an_existing_user_does_not_duplicate_the_user(seeded_roles):
    person = PersonFactory()
    user, _ = get_or_create_user_for_person(person, role_code="parent")

    same_user, created = get_or_create_user_for_person(person, role_code="student")

    assert created is False
    assert same_user.id == user.id
    held = {role.code for role in same_user.current_roles()}
    assert {"parent", "student"} <= held


@pytest.mark.django_db
def test_refuses_to_provision_a_second_user_on_a_mobile_already_in_use(seeded_roles):
    existing_person = PersonFactory(mobile="+919876500001")
    get_or_create_user_for_person(existing_person, role_code="parent")
    colliding_person = PersonFactory(mobile="+919876500001")

    with pytest.raises(ValidationError):
        get_or_create_user_for_person(colliding_person, role_code="student")
