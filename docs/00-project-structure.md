# Project structure

One Django app per SOP module, named after the module. Apps are grouped into domain packages so
`INSTALLED_APPS` stays readable at 37 entries, and the React side mirrors the same names.

**Create an app when its phase starts, not before.** Thirty empty apps on day one is noise that
makes it harder — for you and for Claude Code — to see what actually exists.

---

## The full map

`M##` is the module number from SOP Section 4. `P#` is the phase that creates the app.

```
backend/
  config/                       settings/, urls.py, celery.py, asgi.py, wsgi.py
  apps/
    core/                       —    P0   base models, numbering, approvals, master data
    iam/                        M35  P0   User, Role, Permission, RolePermission, UserRole
    audit/                      M35  P0   AuditLog, audit mixin, middleware
    people/                     —    P0   Person, Guardian, Staff — THE IDENTITY SPINE

    admissions/
      enquiry/                  M01  P1
      trial/                    M03  P1
      admission/                M02  P1
      student/                  M04  P1
      parent/                   M05  P1   portal access + contact preferences (not Guardian)
      document/                 M06  P0   moved to P0 — admission depends on it
      idcard/                   M07  P1

    academics/
      batch/                    M08  P2
      training/                 M09  P2
      attendance/               M10  P2
      coach/                    M11  P2

    finance/
      fee/                      M12  P3
      payment/                  M13  P3

    performance/
      assessment/               M14  P4   technical, fitness, behavioural
      development/              M15  P4   Individual Development Plans
      coach_evaluation/         M16  P4

    medical/                    M17  P5

    competition/
      match/                    M18  P6
      tournament/               M19  P6
      achievement/              M20  P6

    athlete/
      athlete/                  M21  P7   classification, athlete master profile
      profiling/                M22  P7   rating, market readiness, media, portfolio
      scouting/                 M23  P8
      placement/                M24  P8   opportunities, external trials, placements
      contract/                 M25  P9
      commercial/               M26  P9   sponsorship, brand, athlete revenue

    operations/
      residential/              M27  P10
      transport/                M28  P10
      equipment/                M29  P10
      facility/                 M30  P10

    engagement/
      communication/            M31  P0   notification service in P0, campaigns in P11
      grievance/                M32  P11  complaints and feedback
      discipline/               M33  P11  incidents, disciplinary action, withdrawal, re-admission

    reporting/                  M34  P12
  tests/
```

37 apps. 35 modules, plus `core` and `people`, with M35 split into `iam` and `audit` because
access control and audit logging are genuinely different concerns.

---

## Two apps that are not SOP modules

**`people`** holds `Person`, `Guardian` and `Staff`. It exists because SOP §78 — one athlete,
one digital profile — means identity cannot belong to any single module. If `Person` lived in
`student/`, then `coach/`, `parent/` and `athlete/` would all import from `student/`, which is
wrong: a coach is not a kind of student. Identity is the spine; modules hang off it.

**`core`** holds what every module needs and nobody owns: base model classes, the numbering
service, the approval engine, master data (`Programme`, `AgeCategory`, `Venue`, `Season`), and
shared mixins. Nothing in `core` may import from a module app — that rule is what stops `core`
becoming a dumping ground.

Note `parent/` does **not** hold the `Guardian` model. Guardian is identity and lives in
`people/`. M05 Parent Management is the parent's *portal access*, contact preferences and
notification settings — the relationship, not the person.

---

## Dependency direction

Imports flow one way. Draw it once and hold to it in review.

```
core  ←  iam  ←  audit
  ↑
people
  ↑
enquiry ← trial ← admission ← student
                                 ↑
        document, idcard, parent, batch, attendance, fee, medical, …
```

Rules:

- `core` imports nothing from `apps/`.
- `people` imports only `core`.
- A module app may import `core`, `people`, and apps **earlier in its own chain** — never later.
- Two apps that need each other's models mean the boundary is wrong. Move the shared model down
  into `people` or `core`, or use a string reference (`"student.Student"`) plus a service
  function rather than a direct import.
- Cross-module behaviour goes through **domain events**, not imports. When an admission is
  approved, `admission/` emits `student.activated`; `communication/` and `batch/` listen. That
  is how Phase 2 hooks into Phase 1 without Phase 1 knowing Phase 2 exists.

The chain `enquiry → trial → admission → student` is the one to watch. These four are tightly
coupled by the SOP §9 state machine and it is tempting to let them import each other freely.
Keep the arrow pointing one way: `student` knows about `admission`, `admission` knows about
`trial`, and never the reverse.

---

## Nested apps — the Django detail that bites

A nested app needs an explicit `AppConfig` with the full dotted `name`, and an explicit `label`
wherever the last path segment would collide:

```python
# apps/admissions/enquiry/apps.py
from django.apps import AppConfig

class EnquiryConfig(AppConfig):
    name = "apps.admissions.enquiry"
    label = "enquiry"                    # migrations land in enquiry/migrations/
    verbose_name = "Enquiry Management"
```

`apps/athlete/athlete/` would otherwise produce label `athlete` twice — set
`label = "athlete_core"` on the outer one, or flatten it. Every package directory in the chain
needs an `__init__.py`.

`INSTALLED_APPS` lists the dotted paths:

```python
LOCAL_APPS = [
    "apps.core", "apps.iam", "apps.audit", "apps.people",
    "apps.admissions.enquiry", "apps.admissions.trial",
    "apps.admissions.admission", "apps.admissions.student",
    "apps.admissions.parent", "apps.admissions.document",
    "apps.admissions.idcard",
    "apps.engagement.communication",
]
```

Phase 2 appends four lines. Nothing before it changes.

---

## What each app contains

```
enquiry/
  __init__.py
  apps.py
  models.py            or models/ package once it exceeds ~300 lines
  serializers.py
  views.py             ViewSets extending core.ModuleScopedViewSet
  urls.py              a router, included by config/urls.py
  filters.py
  services.py          business logic that is not a model method
  permissions.py       only if the module needs rules beyond the matrix
  signals.py
  admin.py
  migrations/
  management/commands/ seed_* commands live here, never in migrations
  tests/
    test_models.py  test_api.py  test_permissions.py  factories.py
```

Each app declares one module slug used by the permission layer:

```python
class EnquiryViewSet(ModuleScopedViewSet):
    module = "enquiry"        # matches docs/03-rbac.md
```

---

## Frontend — same names

```
frontend/src/
  api/            generated types + typed client (never hand-edited)
  auth/           login, OTP, token refresh, route guards
  components/     shared primitives — Button, Field, Pill, Card, StatTile, Table
  lib/            hooks, formatters, permission helpers
  styles/         tokens.css
  features/
    dashboard/      role dashboards
    enquiry/        ← apps/admissions/enquiry
    trial/          ← apps/admissions/trial
    admission/      ← apps/admissions/admission
    student/        ← apps/admissions/student
    parent/         ← apps/admissions/parent
    document/       ← apps/admissions/document
    idcard/         ← apps/admissions/idcard
```

One feature folder per Django app, same name. Each contains `api/`, `components/`, `hooks/`,
`pages/`. When you add `apps/academics/batch` in Phase 2, you add `features/batch` — the
symmetry is what makes it obvious where anything lives.

---

## Twelve apps exist before Phase 2

Six from Phase 0, six from Phase 1:

| Phase 0 | Phase 1 |
|---|---|
| `core` | `enquiry` |
| `iam` | `trial` |
| `audit` | `admission` |
| `people` | `student` |
| `document` | `parent` |
| `communication` | `idcard` |

`document` and `communication` sit in Phase 0 rather than Phase 1 because admission cannot gate
on documents that do not exist, and trial results cannot notify parents without the notification
service. Both are built as shared services, not as admission-specific features.

Everything else stays uncreated until its phase. `apps/academics/` does not exist yet.
