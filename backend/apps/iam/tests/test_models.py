import pytest

from apps.iam.models import User


@pytest.mark.django_db
def test_create_user_sets_usable_password():
    user = User.objects.create_user(login_id="coach@example.com", password="s3cret-pass")

    assert user.check_password("s3cret-pass")
    assert user.person is None
    assert user.is_active is True
    assert user.is_staff is False


@pytest.mark.django_db
def test_create_superuser_grants_staff_and_superuser():
    user = User.objects.create_superuser(login_id="admin@example.com", password="s3cret-pass")

    assert user.is_staff is True
    assert user.is_superuser is True


@pytest.mark.django_db
def test_username_field_is_login_id():
    assert User.USERNAME_FIELD == "login_id"
