# ACA-OMS — Adamas Cricket Academy Operations & Athlete Management System

You are working on Phase 0 (platform foundation) and Phase 1 (admission funnel) of a system
that will eventually cover 35 modules from the academy's Standard Operating Procedure.

Read `docs/05-build-sequence.md` to find the current task. Read `docs/01-data-model.md`
before writing any model. Do not invent fields that are not in the spec — if the spec is
missing something the task needs, say so and stop rather than guessing.

## Stack

- **Backend**: Python 3.12, Django 5.1, Django REST Framework, PostgreSQL 16, Celery + Redis
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, TanStack Query, React Hook Form + Zod
- **Storage**: AWS S3 (presigned uploads — files never pass through the API server)
- **Auth**: JWT (short-lived access + rotating refresh); mobile OTP for parents and students
- **Testing**: pytest + factory_boy (backend), Vitest + Playwright (frontend)
- **Tooling**: ruff, mypy, pre-commit, drf-spectacular for OpenAPI

## Directory layout

```
backend/
  config/            settings (base.py, dev.py, staging.py, prod.py), urls, celery
  apps/
    iam/             User, Role, Permission, RolePermission, UserRole
    audit/           AuditLog, audit mixin, middleware
    people/          Person, Guardian, StudentGuardian, Staff, Document, IDCard
    admissions/      Enquiry, Trial, TrialAssessment, Admission, Student
    core/            master data, ApprovalRequest, NotificationTemplate, base classes
  tests/
frontend/
  src/
    api/             generated types + typed client
    auth/            login, OTP, token refresh, route guards
    components/      shared UI primitives
    features/        one folder per domain area (enquiry, trial, admission, student)
    lib/             hooks, formatters, permission helpers
docs/                the specs in this kit — keep them current, they are the handover artifact
```

## Non-negotiable rules

These come from the academy's SOP and are the reason the system exists. Violating one is a
defect even if the code works.

1. **One Person, one profile.** `Person` is the canonical human record. `Student`, `Athlete`,
   `Guardian` and `Staff` all point at it. There is no code path that creates a `Person`
   without first calling `people.services.resolve_person()`, which runs duplicate detection.
   Re-admitting a former student **reuses** their `Person`. (SOP §78)

2. **Enter once.** Data captured at enquiry flows to trial, then to admission, then to the
   student profile. Never re-collect a field that an earlier step already captured. If you
   find yourself writing a second `phone_number` field on a second model, stop. (SOP §79)

3. **Permissions are data, not code.** Never write `if user.role == "coach"`. Check
   `user.has_perm_for(module, verb)` against the `RolePermission` table. `Export` is a
   distinct verb from `View`.

4. **Audit is automatic.** Add `AuditedModel` to a model and the middleware writes the
   field-level diff. Never write manual audit calls. Never add an `UPDATE` or `DELETE` path
   to `AuditLog`.

5. **Status is a state machine.** Student status, admission steps, trial results and document
   states each have an explicit transition table in `docs/04-state-machines.md` with guards
   and permitted roles. Never set a status field directly — call the transition method.

6. **Object-level authorisation on every endpoint.** A parent must not reach another parent's
   child by changing an id in the URL. Every list is scoped by queryset; every detail view
   checks the object. Every endpoint has a permission test.

7. **Money and identity are transactional.** Anything that generates a sequential number
   (`enquiry_no`, `student_code`, `application_no`) must be collision-safe under concurrency.
   Use a database sequence or `select_for_update`, never `count() + 1`.

## Conventions

- API is versioned at `/api/v1/`. Plural resource nouns. Verbs only for real state
  transitions (`POST /api/v1/admissions/{id}/approve`).
- Cursor pagination on every list endpoint. Offset pagination degrades on large tables.
- Error envelope: `{code, message, field_errors, request_id}`. `message` is user-safe;
  `code` is what the frontend switches on.
- Every response carries a `request_id`, echoed into logs and Sentry.
- Idempotency keys on any endpoint that creates a numbered record.
- Timezone is `Asia/Kolkata`. Store UTC, render IST. Dates display as DD-MM-YYYY.
- Currency is INR. Money is `Decimal`, never `float`.
- Frontend types are **generated** from the OpenAPI schema. Do not hand-write API types —
  a backend field rename must break the frontend build.

## Testing policy

- Every model gets a factory. Every endpoint gets a permission test.
- The permission matrix test (`tests/test_permission_matrix.py`) is parameterised over
  every (role × endpoint × verb). Adding an endpoint without a matrix entry **must fail the
  build**. This is the highest-value suite in the project — do not weaken it.
- Coverage gate: 75% overall, 90% on `iam`, `audit` and anything handling money or identity.
- State machines get a test per transition **and** per rejected transition.

## What to never do

- Never run `makemigrations` and `migrate` in the same step without showing me the migration
  first. Migrations touching `people` or `iam` need review.
- Never store a file in the database or proxy an upload through the API server — use S3
  presigned URLs.
- Never add a third-party package without saying why in the commit message.
- Never soft-delete a `Person`. Deactivate the `Student` record instead; the human still exists.
- Never write seed data into a migration. Seeds live in `apps/core/management/commands/seed_*`.
- Never hardcode a role name, fee amount, assessment criterion or document requirement.
  They are master data.

## Working style

- Work one task at a time from `docs/05-build-sequence.md`. Finish its acceptance check
  before starting the next.
- Write the test first when the task has a stated acceptance criterion.
- After each task, run `ruff check`, `mypy`, `pytest` and the frontend type-check before
  saying it is done.
- When a spec is ambiguous, ask. A wrong guess in the identity model is the single most
  expensive mistake available in this project.
