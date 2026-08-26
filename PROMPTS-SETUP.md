# Sprint 0 — project setup

Do this before any model. Four prompts, roughly a day.

Local development is **native** — no Docker on your machine. `LOCAL-SETUP.md` has the
prerequisites, the one-time setup and the troubleshooting table. Production still ships as a
container to ECS Fargate.

Read `docs/00-project-structure.md` first — it has the full 37-app map and the naming rule.

---

## 1. Repository skeleton

```
Read CLAUDE.md and docs/00-project-structure.md.

Create the repository skeleton — directories, __init__.py files, apps.py,
config files. No models, no views, no serializers. Structure only.

backend/
  config/settings/{base,dev,staging,prod}.py, django-environ, no secrets
         in code. config/{urls,celery,asgi,wsgi}.py
  apps/  Create ONLY the twelve Phase 0 + Phase 1 apps listed at the end of
         docs/00-project-structure.md. Do not create apps/academics,
         apps/finance, apps/performance or anything else yet.

         core, iam, audit, people,
         admissions/{enquiry,trial,admission,student,parent,document,idcard},
         engagement/communication

  Every nested app gets an apps.py with the full dotted `name` and an
  explicit `label`, per the nested-apps section of the structure doc.
  Every package directory gets an __init__.py.
  Each app gets: models.py, serializers.py, views.py, urls.py, filters.py,
  services.py, signals.py, admin.py, migrations/__init__.py, tests/.

  pyproject.toml (or requirements/{base,dev,prod}.txt), pytest.ini,
  ruff.toml, mypy.ini, .pre-commit-config.yaml

frontend/
  Vite + React 18 + TypeScript + Tailwind.
  src/{api,auth,components,lib,styles}/ and src/features/ with one folder
  per Phase 1 module, same names as the Django apps.

Show me the tree before writing file contents.

Check: `python manage.py check` passes with all twelve apps in
INSTALLED_APPS, and `npm run build` succeeds.

Do not create a docker-compose.yml. Local services are installed natively —
see LOCAL-SETUP.md.
```

---

## 2. Local environment (native — no Docker)

```
Read LOCAL-SETUP.md.

Set up native local development. Services run natively; the app runs
natively. No docker-compose.

Create:
- requirements/{base,dev,prod}.txt. dev includes honcho, pytest-django,
  factory-boy, django-extensions, ruff, mypy.
- .env.example with every variable and no real values, matching the block
  in LOCAL-SETUP.md.
- config/settings/dev.py reading DATABASE_URL, REDIS_URL and
  AWS_S3_ENDPOINT_URL from the environment via django-environ.
  AWS_S3_ENDPOINT_URL points at local MinIO in dev and is UNSET in staging
  and production, so boto3 talks to real S3. No application code may branch
  on which one it is.
- config/settings/test.py using Django's in-memory storage backend, so the
  test suite never needs a running object store.
- Procfile.dev with four processes: web (runserver), worker (celery worker),
  beat (celery beat), frontend (vite dev). MinIO is NOT in the Procfile — it
  runs once as a background service.
- Makefile with the targets listed in LOCAL-SETUP.md: dev, migrate, seed,
  test, lint, fmt, shell, storage, reset-db.
- A health endpoint GET /api/v1/health/ that checks database and Redis
  connectivity and reports each in the payload.
- A migration adding the pg_trgm and unaccent PostgreSQL extensions, so a
  fresh database gets them without a manual psql step.

Also write the production Dockerfile now — multi-stage, non-root user,
gunicorn, Python pinned to 3.12. It is built by CI for ECS Fargate and never
used locally. Do not add a docker-compose.yml.

Check: `make dev` starts all four processes in one terminal,
`curl localhost:8000/api/v1/health/` returns 200 with database and Redis both
ok, and `make test` passes with MinIO stopped.
```

## 3. Shared foundations in `core`

```
Build apps/core/ — the pieces every module app depends on. No business
logic yet.

- models.py: TimeStampedModel (UUID pk, created_at, updated_at) and
  AuditedModel (the mixin; the middleware comes in the audit app)
- services/numbering.py: next_number(series, **ctx) backed by a PostgreSQL
  sequence per series. Collision-safe under concurrency — never count()+1.
  Formats per docs/01-data-model.md section 6.
- views.py: ModuleScopedViewSet, the base every module ViewSet extends.
  Maps HTTP method to permission verb; leave the permission check as a
  TODO stub until iam exists.
- pagination.py: cursor pagination, the default for every list endpoint
- exceptions.py: the {code, message, field_errors, request_id} envelope
- middleware.py: request_id generation, echoed into logs and responses

Rule to enforce in review: apps/core imports nothing from other apps/.

Check: a test proving 500 concurrent next_number("ENQ") calls produce 500
distinct numbers with no gaps and no duplicates.
```

---

## 4. CI pipeline

```
Add .github/workflows/ci.yml.

Jobs: ruff check, mypy, pytest with coverage (fail under 75), Django
migration conflict check (makemigrations --check --dry-run), frontend
tsc --noEmit and vite build.

Postgres and Redis as service containers for pytest.

Check: green on this empty project. Adding a deliberately failing test
turns it red, and an un-generated migration turns it red.
```

---

## Then

Move to `PROMPTS.md` prompt 3 — the `Person` model and duplicate detection. That is the first
real code, and it is the piece most expensive to get wrong.

---

## Adding a module app later

When Phase 2 starts:

```
Read docs/00-project-structure.md.

Create apps/academics/ with the batch, training, attendance and coach apps,
following the same structure as the Phase 1 apps. Add them to
INSTALLED_APPS and create the matching src/features/ folders.

Structure only — no models yet.

Check: python manage.py check passes and no existing migration changed.
```

The last line of that check matters. Adding an app must never alter an existing migration.
