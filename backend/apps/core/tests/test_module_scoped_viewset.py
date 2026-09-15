import pytest
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.iam.tests.factories import (
    PermissionFactory,
    RolePermissionFactory,
    UserFactory,
    UserRoleFactory,
)
from apps.people.tests.factories import PersonFactory

from .module_scoped_viewset_support import EnquiryStandInViewSet

factory = APIRequestFactory()


def _user_with_grant(module: str, verb: str, scope: str = "all", **user_kwargs):
    # PermissionFactory is get_or_create on (module, verb) — "enquiry" is a
    # real seeded module (docs/03-rbac.md), so when this test runs in the
    # same session as anything using the `seeded_roles` fixture (session-
    # scoped, seeds outside any per-test transaction), a real
    # Permission(enquiry, <verb>) row may already exist.
    permission = PermissionFactory(module=module, verb=verb)
    role_permission = RolePermissionFactory(permission=permission, scope=scope)
    user = UserFactory(**user_kwargs)
    UserRoleFactory(user=user, role=role_permission.role)
    return user


@pytest.mark.django_db
def test_post_refused_for_role_with_only_view():
    user = _user_with_grant("enquiry", "view")

    view = EnquiryStandInViewSet.as_view({"post": "create"})
    request = factory.post("/stand-in/", {})
    force_authenticate(request, user=user)
    response = view(request)

    assert response.status_code == 403


@pytest.mark.django_db
def test_post_allowed_for_role_with_add():
    user = _user_with_grant("enquiry", "add")
    payload = {
        "first_name": "Rohan",
        "last_name": "Sharma",
        "date_of_birth": "2015-06-15",
        "gender": "M",
        "mobile": "9876543210",
        "address_line1": "1 MG Road",
        "address_line2": "Near City Park",
        "city": "Kolkata",
        "state": "West Bengal",
        "pincode": "700001",
    }

    view = EnquiryStandInViewSet.as_view({"post": "create"})
    request = factory.post("/stand-in/", payload, format="json")
    force_authenticate(request, user=user)
    response = view(request)

    assert response.status_code == 201


@pytest.mark.django_db
def test_get_refused_for_role_with_no_grant_at_all():
    user = UserFactory()

    view = EnquiryStandInViewSet.as_view({"get": "list"})
    request = factory.get("/stand-in/")
    force_authenticate(request, user=user)
    response = view(request)

    assert response.status_code == 403


@pytest.mark.django_db
def test_scope_own_role_sees_only_own_rows_in_list():
    own_person = PersonFactory()
    other_person = PersonFactory()
    user = _user_with_grant("enquiry", "view", scope="own", person=own_person)

    view = EnquiryStandInViewSet.as_view({"get": "list"})
    request = factory.get("/stand-in/")
    force_authenticate(request, user=user)
    response = view(request)

    assert response.status_code == 200
    returned_ids = {row["id"] for row in response.data["results"]}
    assert returned_ids == {str(own_person.pk)}
    assert str(other_person.pk) not in returned_ids


@pytest.mark.django_db
def test_scope_all_role_sees_every_row_in_list():
    PersonFactory()
    PersonFactory()
    user = _user_with_grant("enquiry", "view", scope="all")

    view = EnquiryStandInViewSet.as_view({"get": "list"})
    request = factory.get("/stand-in/")
    force_authenticate(request, user=user)
    response = view(request)

    assert response.status_code == 200
    assert len(response.data["results"]) == 2


@pytest.mark.django_db
@pytest.mark.urls("apps.core.tests.module_scoped_viewset_urls")
def test_custom_action_checks_its_declared_verb_not_the_http_method_default():
    """@action(detail=True, methods=["post"], verb="approve") must be
    checked against "approve", not POST's default mapping to "add" — a
    role holding only "add" must still be refused. Routed through a real
    SimpleRouter, since the verb override is only applied by router
    machinery, not by a bare ViewSet.as_view({...}) call.
    """
    person = PersonFactory()
    user = _user_with_grant("enquiry", "add")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(f"/stand-in/{person.pk}/approve/")

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.urls("apps.core.tests.module_scoped_viewset_urls")
def test_custom_action_succeeds_when_role_holds_its_declared_verb():
    person = PersonFactory()
    user = _user_with_grant("enquiry", "approve")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(f"/stand-in/{person.pk}/approve/")

    assert response.status_code == 200
    assert response.data == {"approved": True}
