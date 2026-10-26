"""No list endpoint may run more database queries because it has more rows
to show (the "N+1" problem — one query per row for a related object the
serializer touches). Under load that is what turns a 20 ms page into a
2 s one, so it is checked for every list endpoint, automatically:

  1. create 3 rows of the endpoint's model, count the queries of a GET;
  2. create 6 more rows, count again;
  3. the two counts must be equal.

Endpoints are discovered from the real URLconf (every GET route with no
path parameters whose view lists a model), and rows are made with that
model's own factory, found by scanning the apps' tests/factories.py — so
a new list endpoint is covered the day it's added, like
test_permission_matrix.py. An endpoint whose model has no factory is
reported as uncovered rather than silently passing.
"""

import datetime
import importlib
import pkgutil

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import URLResolver, get_resolver
from factory.django import DjangoModelFactory
from rest_framework.generics import GenericAPIView
from rest_framework.test import APIClient

import apps
from apps.iam.models import Role, UserRole
from apps.iam.tests.factories import UserFactory

FEW, MORE = 3, 6


def _walk(patterns, prefix=""):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _walk(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            yield prefix + str(pattern.pattern), pattern


def _list_routes():
    """[(url, view_name, model), ...] for every parameterless GET route
    whose view is a list over a model's queryset."""
    routes = {}
    for route, pattern in _walk(get_resolver().url_patterns):
        if "<" in route or "(?P" in route or not route.startswith("api/v1/"):
            continue
        callback = pattern.callback
        view_cls = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
        if not (isinstance(view_cls, type) and issubclass(view_cls, GenericAPIView)):
            continue
        actions = getattr(callback, "actions", None)
        if actions is not None:
            if actions.get("get") != "list":
                continue
        elif not hasattr(view_cls, "list"):
            continue
        queryset = getattr(view_cls, "queryset", None)
        if queryset is None:
            continue
        url = "/" + route.replace("^", "").replace("$", "")
        routes[url] = (view_cls.__name__, queryset.model)
    return sorted((url, name, model) for url, (name, model) in routes.items())


def _factories():
    """model -> its factory, from every apps/**/tests/factories.py."""
    found = {}
    for module_info in pkgutil.walk_packages(apps.__path__, "apps."):
        if not module_info.name.endswith(".tests.factories"):
            continue
        module = importlib.import_module(module_info.name)
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, DjangoModelFactory)
                and value is not DjangoModelFactory
                and getattr(value._meta, "model", None) is not None
            ):
                # The plainest factory wins (e.g. AdmissionFactory over
                # DirectAdmissionFactory) — the first one defined.
                found.setdefault(value._meta.model, value)
    return found


ROUTES = _list_routes()
FACTORIES = _factories()


@pytest.fixture
def staff_client(seeded_roles):
    """Holds every role, so every list is visible at all-scope."""
    user = UserFactory()
    for role in Role.objects.all():
        UserRole.objects.create(user=user, role=role, valid_from=datetime.date(2020, 1, 1))
    client = APIClient()
    client.force_authenticate(user)
    return client


def _query_count(client, url):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(url, {"page_size": 100})
    return response, len(queries)


@pytest.mark.django_db
@pytest.mark.parametrize("url,view_name,model", ROUTES, ids=[r[0] for r in ROUTES])
def test_list_query_count_does_not_grow_with_rows(staff_client, url, view_name, model):
    factory = FACTORIES.get(model)
    if factory is None:
        pytest.skip(f"{view_name}: no factory for {model.__name__} to create rows with")

    factory.create_batch(FEW)
    # Warm-up: the first request of a test also resolves and caches the
    # user's permissions — one-off cost, not per-row cost.
    first, _ = _query_count(staff_client, url)
    _, few_queries = _query_count(staff_client, url)
    if first.status_code != 200:
        pytest.skip(f"{view_name}: GET {url} -> {first.status_code} without extra parameters")
    factory.create_batch(MORE)
    _, more_queries = _query_count(staff_client, url)

    assert more_queries == few_queries, (
        f"{view_name} ({url}) ran {few_queries} queries for {FEW} rows but "
        f"{more_queries} for {FEW + MORE} — something is fetched once per row. "
        "Add select_related()/prefetch_related() to its queryset."
    )
