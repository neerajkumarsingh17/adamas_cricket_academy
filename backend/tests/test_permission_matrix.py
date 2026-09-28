"""Parameterised over every (registered ModuleScopedViewSet route x seeded
role x verb that route actually uses), asserting against docs/03-rbac.md —
via the same MATRIX data seed_roles.py seeds from, so this test and the
seeded database are always compared against one single source of truth.

Routes are discovered from the real URLconf (config.urls), not a fixture,
so this test starts covering new endpoints automatically as later sprints
register real ViewSets — no rewrite needed. A module with no docs/03-rbac.md
row FAILS here, per CLAUDE.md: never add a skip marker to this suite.
"""

import datetime

import pytest
from django.urls import URLResolver, get_resolver

from apps.core.management.commands.seed_roles import ROLES, expected_access
from apps.core.views import ModuleScopedViewSet
from apps.iam.models import Role, User, UserRole


def _walk(patterns):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _walk(pattern.url_patterns)
        else:
            yield pattern


def _verb_for_action(callback, viewset_cls, action_name: str, http_method: str) -> str:
    # `callback.initkwargs` is what DRF's own ViewSetMixin.as_view() stores
    # from *any* extra kwarg passed to it — including an explicit
    # `.as_view({...}, verb="edit")` call (apps.academics.attendance.urls'
    # three explicit-path routes), which the previous two-tier check below
    # never looked at. Checking it first covers both wiring styles with
    # one mechanism, rather than guessing the explicit-path verb from the
    # HTTP method (wrong for SessionAttendanceViewSet.cancel: POST would
    # guess "add", but urls.py passes verb="edit").
    initkwarg_verb = getattr(callback, "initkwargs", {}).get("verb")
    if initkwarg_verb:
        return initkwarg_verb
    bound = getattr(viewset_cls, action_name, None)
    verb_override = getattr(bound, "kwargs", {}).get("verb") if bound else None
    if verb_override:
        return verb_override
    return viewset_cls._METHOD_VERBS.get(http_method.upper(), "view")


def _discover_route_cases() -> list[tuple[str, str, str]]:
    """[(viewset_name, module, verb), ...] — one entry per distinct
    (module, verb) pair actually exercised by a registered
    ModuleScopedViewSet route, deduplicated (e.g. update + partial_update
    both map to "edit" — one case, not two).
    """
    seen: dict[tuple[str, str], str] = {}
    for pattern in _walk(get_resolver().url_patterns):
        callback = getattr(pattern, "callback", None)
        viewset_cls = getattr(callback, "cls", None)
        if not (isinstance(viewset_cls, type) and issubclass(viewset_cls, ModuleScopedViewSet)):
            continue
        actions = getattr(callback, "actions", None) or {}
        action_modules = getattr(viewset_cls, "action_modules", {})
        for http_method, action_name in actions.items():
            verb = _verb_for_action(callback, viewset_cls, action_name, http_method)
            module = action_modules.get(action_name, viewset_cls.module)
            key = (module, verb)
            seen.setdefault(key, viewset_cls.__name__)
    return [(name, module, verb) for (module, verb), name in sorted(seen.items())]


ROUTE_CASES = _discover_route_cases()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewset_name,module,verb",
    ROUTE_CASES,
    ids=[f"{name}:{module}:{verb}" for name, module, verb in ROUTE_CASES],
)
@pytest.mark.parametrize("role_code,role_name", ROLES, ids=[code for code, _ in ROLES])
def test_permission_matrix(seeded_roles, viewset_name, module, verb, role_code, role_name):
    try:
        expected = expected_access(module, verb, role_code)
    except LookupError:
        pytest.fail(
            f"{viewset_name} registers module={module!r}, which has no row in "
            f"docs/03-rbac.md's matrix. Every registered module needs a matrix "
            f"entry — add one (see docs/03-rbac.md) rather than skip this."
        )

    user = User.objects.create_user(
        login_id=f"probe-{role_code}-{module}-{verb}@example.com",
    )
    UserRole.objects.create(
        user=user,
        role=Role.objects.get(code=role_code),
        valid_from=datetime.date(2020, 1, 1),
    )

    actual = user.has_perm_for(module, verb)

    assert actual == expected, (
        f"{role_name} ({role_code}) on {module}/{verb} ({viewset_name}): "
        f"docs/03-rbac.md says {expected}, seeded database says {actual}"
    )


def test_at_least_one_real_route_is_covered():
    """A guard against this suite silently going empty — the check ("deleting
    one RolePermission row makes exactly one parameterised case fail") is
    only meaningful if there's at least one real case.
    """
    assert ROUTE_CASES, (
        "No registered ModuleScopedViewSet routes found — the permission "
        "matrix test has nothing to parameterise over."
    )
