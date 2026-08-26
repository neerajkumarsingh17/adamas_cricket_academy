# What to type into Claude Code

Copy these one at a time, in order. Do not paste two at once — the whole point is that each one
ends with something you can check before moving on.

---

## Before anything

Put the kit at the root of an empty git repo and commit it:

```
your-repo/
  CLAUDE.md
  RUN.md                      the execution order — start here
  LOCAL-SETUP.md              native setup: prerequisites, .env, Makefile
  PROMPTS-SETUP.md            Sprint 0 — do this first
  PROMPTS.md                  Sprints 1–2, then the repeating pattern
  PROMPTS-PHASE1-SCREENS.md   the 27 Phase 1 screens
  docs/00-project-structure.md … 08 (07-storage.md)
```

Claude Code reads `CLAUDE.md` automatically at the start of every session. That is why the
prompts below are short — the rules, conventions and data model are already in front of it.

**Five habits that matter more than the prompts:**

1. **One task per prompt.** "Build the Person model" gets a good result. "Build the models,
   the API and the frontend" gets three mediocre ones.
2. **End with the check.** Every prompt below finishes by naming what must be true. Without it
   you get code that looks right.
3. **Say "show me the migration before running it."** Every time you touch models. A bad
   migration on `people` or `iam` is the expensive kind.
4. **`/clear` between unrelated tasks.** A long context makes it slower and more confused, not
   smarter. Clear it when you move from backend to frontend.
5. **When it guesses, stop it.** If it invents a field that is not in `docs/01-data-model.md`,
   say so and point at the file. Letting one invented field through means the next twenty
   assume it.

---

# Sprint 0 — scaffolding

Moved to **`PROMPTS-SETUP.md`** — four prompts covering the repository skeleton, the local
native local environment, the shared `core` app and CI. Do those first, then come back here.

The app layout is one Django app per SOP module, named after the module. `docs/00-project-structure.md`
has the full 37-app map and the rule about when each one gets created.

---

# Sprint 1 — identity and access

This is the part that is expensive to get wrong. Go slowly here.

### 3. Person and duplicate detection

```
Read docs/01-data-model.md section 1.

Build the Person model and people/services.py::resolve_person() in
backend/apps/people/. Person only — not Guardian, Student or Staff yet.

Requirements from the spec that I want you to be careful about:
- dedupe_key computed on save, exactly as specified
- resolve_person returns exact matches on dedupe_key plus fuzzy candidates
  (name similarity >= 0.85 AND (DOB exact OR guardian mobile exact))
- normalise mobile numbers to E.164 before hashing

Show me the migration before running it.

Check: a test that creates a Person, then attempts a second Person with the
same name, DOB and guardian mobile, and asserts resolve_person returns the
existing one. This is SOP §78 and it is the most important test in the repo.
```

### 4. The rest of the identity spine

```
Read docs/01-data-model.md section 1.

Add Guardian, StudentGuardian, Staff and the custom User model
(USERNAME_FIELD = login_id). Factories for each in tests/factories/.

Enforce in StudentGuardian.clean(): exactly one is_primary per student.

Show me the migration first.

Check: a test proving one guardian with two children is a single Guardian
row, and a test proving a second is_primary guardian is rejected.
```

### 5. Roles and permissions

```
Read docs/01-data-model.md section 2 and docs/03-rbac.md.

Build Role, Permission, RolePermission, UserRole, plus
User.has_perm_for(module, verb) with per-request caching.

Add `python manage.py seed_roles` that loads the 16 roles and the matrix
from docs/03-rbac.md. Seeds are a management command, never a migration.

Check: seed_roles runs idempotently, and has_perm_for("admission","approve")
is True for academy_head and False for coach — read from database rows, not
from any hardcoded role name.
```

### 6. Permission enforcement

```
Read docs/06-conventions.md, the Permissions section.

Build ModuleScopedViewSet in apps/core/: a DRF ViewSet base that maps HTTP
method to verb (GET→view, POST→add, PATCH/PUT→edit, DELETE→edit), checks
has_perm_for, and applies scope="own" queryset filtering.

Add an @action decorator variant that takes an explicit verb, so
@action(detail=True, methods=["post"], verb="approve") works.

Check: a viewset declaring module="enquiry" refuses POST for a role with
only view, and a scope="own" role sees only their own rows in the list.
```

### 7. Authentication

```
Build authentication in apps/iam/ per docs/02-api-spec.md, Auth section.

- JWT: short-lived access, rotating refresh, old refresh blacklisted on use
- Mobile OTP for parents and students: request and verify endpoints,
  6-digit code, 10-minute expiry, rate limit 3 per 10 minutes per mobile
- /auth/me returns user, person, roles and the flattened permission set

Store OTPs hashed in Redis with a TTL, never in the database in plain text.

Check: OTP login works end to end against a stubbed SMS backend, a reused
refresh token is rejected, and the fourth OTP request in ten minutes is
throttled.
```

### 8. The permission matrix test

```
Build tests/test_permission_matrix.py.

Parameterise over every registered DRF route x every seeded role x every
verb, and assert the response matches what docs/03-rbac.md says it should be.
An endpoint whose module has no matrix entry must FAIL the test, not skip it.

Check: it passes now, and deleting one RolePermission row makes exactly one
parameterised case fail.

This suite is what makes the RBAC matrix real instead of documentation.
Do not add skip markers to it later.
```

---

# Sprint 2 — audit, storage, notifications

### 9. Audit trail

```
Read docs/01-data-model.md section 3.

Build AuditLog, an AuditedModel mixin, and the middleware that captures the
field-level diff on save. Actor, IP, user agent and request_id come from the
request; use a contextvar so model signals can reach them.

Add a data migration with RunSQL that revokes UPDATE and DELETE on
audit_auditlog from the application database role.

Check: saving an audited model writes one row with correct from/to values,
and a test asserting that an attempted UPDATE on audit_auditlog raises a
database permission error.
```

### 10. S3 storage layer

```
Read docs/07-storage.md in full before writing anything.

Build the storage layer in apps/core/storage.py plus the Document,
DocumentType and DocumentVersion models from docs/01-data-model.md section 4.

Endpoints: POST /documents/presign, POST /documents/confirm,
GET /documents/{id}/download.

The parts I care about most:
- files never pass through Django — presigned PUT up, presigned GET down
- keys are documents/{owner_type}/{owner_id}/{uuid}.{ext}, never the user's
  filename
- confirm does head_object, checks real size, and sniffs content type from
  the first bytes rather than trusting the declared Content-Type
- presigned GET expires in 5 minutes and is generated only after the
  permission check, never returned in a list endpoint

Use django-storages with boto3. Local dev points at a natively-installed
MinIO via AWS_S3_ENDPOINT_URL, so no AWS credentials are needed to develop.
That variable is unset in staging and production. No application code may
branch on which one it is.

Check: the five tests listed at the end of docs/07-storage.md all pass.
```

### 11. Photograph handling

```
Add photograph upload on top of the storage layer.

Same presign/confirm flow, prefix photos/person/{id}/. On confirm, queue a
Celery task that uses Pillow to strip EXIF and write a 256px square
thumbnail beside the original.

EXIF stripping is not optional — phone photos carry GPS coordinates and
these are photographs of children.

Check: an uploaded JPEG with GPS EXIF produces a thumbnail with no EXIF, and
the profile endpoint returns the thumbnail URL, not the original.
```

### 12. Notifications

```
Build the notification service per docs/01-data-model.md section 4.

NotificationTemplate, NotificationLog, and channel adapters for SMS,
WhatsApp and email behind one interface. Dispatch always async via Celery
with retry and exponential backoff.

Single public entry point: notifications.send(code, recipient, context).
Calling code must never know which channel it used.

Write adapters against MSG91 for SMS and WhatsApp, and Django's email
backend for email, but keep a console adapter as the default in dev.

Check: notifications.send with the console adapter logs a rendered message,
a failing provider retries three times then marks the log failed, and
swapping the adapter requires no change to calling code.
```

---

# Sprint 4 onward

The pattern is now established. For each remaining module, the prompt is:

```
Read docs/01-data-model.md section {N} and docs/02-api-spec.md, {Module}
section. Read docs/04-state-machines.md if this module has a status field.

Build {module}: models, migrations, serializers, viewsets, filters, factories
and tests.

Show me the migration before running it.

Check: {paste the acceptance check from that task's row in
docs/05-build-sequence.md}
```

Work through `docs/05-build-sequence.md` in task order. It has 91 rows and
each one already carries its acceptance check.

---

## Frontend prompts

Do the frontend for a module **after** its API exists, not alongside — you want the generated
types to be real.

```
Run `npm run generate:api` to regenerate src/api/types.gen.ts from the
OpenAPI schema, then build the {feature} screens in
src/features/{feature}/.

Use TanStack Query for all server state, React Hook Form + Zod for forms.
Never hand-write API types.

Every list view needs three states: loading skeleton, empty, and error.
All three, not just the happy path.

Mobile-first — test at 360px. A coach uses this on a tablet at a ground.

Check: {the screen's acceptance check from docs/05-build-sequence.md}
```

---

## When it goes wrong

| What you see | What to say |
|---|---|
| It invented a field | "That field is not in docs/01-data-model.md. Re-read section N and use only what is specified." |
| It hardcoded a role name | "CLAUDE.md rule 3 — permissions are data. Use has_perm_for." |
| It wrote a status assignment | "docs/04-state-machines.md — call the transition method, do not set the field." |
| It proxied a file upload through Django | "docs/07-storage.md — presigned URLs only. The file must not touch the API server." |
| It skipped tests to move faster | "Add the permission test and the object-level authorisation test before we continue." |
| The migration looks wrong | "Do not run it. Explain what each operation does and why." |
| It's drifting into a later phase | "That is Phase {N}. See the boundaries table in docs/05-build-sequence.md. Stub it." |

## Keeping the specs current

When the data model, API or a state machine changes, update the doc **in the same commit**. Tell
Claude Code to do it:

```
That change altered the Document status flow. Update
docs/04-state-machines.md section 4 to match, in this same commit.
```

The specs are the handover artifact. One developer holding the whole build is only safe while
the knowledge lives in the repository rather than in your head.
