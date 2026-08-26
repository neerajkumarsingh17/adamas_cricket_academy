# RUN — the execution order

Every prompt for Phase 0 + Phase 1, in the order you run them. 43 prompts across 12 sessions,
roughly 16 weeks solo.

Where a prompt already exists in another kit file, this sheet points at it. Where it does not,
the full text is here.

**Session hygiene.** One session per block below. `/clear` between blocks — a long context makes
Claude Code slower and more confused, not smarter. Commit at the end of every block with the
task ID in the message.

---

## 0 · Orientation — run this once, first

Before any code. This proves Claude Code has actually absorbed the kit rather than skimmed it.

```
Read every file in this repository: CLAUDE.md, LOCAL-SETUP.md,
PROMPTS-SETUP.md, PROMPTS.md, PROMPTS-PHASE1-SCREENS.md, and all of docs/.

Then answer these, briefly, before writing anything:

1. What are the seven non-negotiable rules in CLAUDE.md?
2. Why does Person live in apps/people rather than apps/admissions/student?
3. How many Django apps does Phase 1 create, and which ones?
4. What is the one rule about file uploads?
5. Which single test suite fails the build when an endpoint has no
   permission-matrix entry?
6. Name three things Phase 1 deliberately does NOT build, and what stands in
   for each.

If any answer is not in the docs, say so rather than guessing. Do not write
any code in this response.
```

If it gets any of these wrong, correct it and point at the file before continuing. Every later
prompt assumes this ground is solid.

---

## Session 1 · Scaffolding  (Week 1)

| # | Prompt | Where | Produces |
|---|---|---|---|
| 1 | Repository skeleton | `PROMPTS-SETUP.md` §1 | 12 apps, frontend folders, config files |
| 2 | Native local environment | `PROMPTS-SETUP.md` §2 | Procfile, Makefile, `.env.example`, health endpoint |
| 3 | Shared foundations in `core` | `PROMPTS-SETUP.md` §3 | Base models, numbering, ModuleScopedViewSet, error envelope |
| 4 | CI pipeline | `PROMPTS-SETUP.md` §4 | GitHub Actions, green on empty project |

**Checkpoint:** `make dev` starts four processes, `/api/v1/health/` returns 200, CI is green.
Commit `T-004 … T-007`.

---

## Session 2 · Identity spine  (Weeks 2–3)

The expensive part. Go slowly.

| # | Prompt | Where |
|---|---|---|
| 5 | Person + duplicate detection | `PROMPTS.md` §3 |
| 6 | Guardian, StudentGuardian, Staff, User | `PROMPTS.md` §4 |
| 7 | Roles and permissions | `PROMPTS.md` §5 |
| 8 | Permission enforcement | `PROMPTS.md` §6 |
| 9 | Authentication (JWT + OTP) | `PROMPTS.md` §7 |
| 10 | Permission matrix test | `PROMPTS.md` §8 |

**Checkpoint:** a seeded role can log in, sees only permitted endpoints, and the matrix test
fails when you delete one `RolePermission` row. Commit `T-101 … T-109`.

---

## Session 3 · Approvals and master data  (Week 4)

Not in the other files — full text here.

**11 · Approval engine**

```
Read docs/01-data-model.md section 4, the ApprovalRequest part.

Build the generic approval engine in apps/core/:
- ApprovalRule (module, action, required_role FK, optional threshold JSON)
- ApprovalRequest with a generic FK to the subject, requested_by, status,
  decided_by, decided_at, reason
- Service: approvals.request(subject, module, action, requested_by) and
  approvals.decide(request, user, approve: bool, reason)
- Endpoints per docs/02-api-spec.md, Approvals section. GET /approvals
  returns ONLY requests this user is permitted to decide.

Rejection always requires a reason. Approving your own request is refused.

This engine is reused by admission approval, trial waivers, fee waivers,
status changes, discounts (Phase 3), discipline (Phase 11) and contracts
(Phase 9). Build it generic now; do not special-case admission.

Check: demonstrated end to end on one dummy model — a user without the
approve verb gets 403, the requester cannot approve their own request, and
a rejection without a reason is refused.
```

**12 · Master data**

```
Read docs/01-data-model.md section 4, Master data.

Build in apps/core/: Programme, AgeCategory (min_age, max_age,
as_on_date_rule), Venue, Season, EnquirySource, TrainingType, DocumentType,
AssessmentCriterion. Register all of them in Django admin with sensible
list_display, search and filters.

Add `python manage.py seed_master_data` with realistic starting values for
an Indian cricket academy: U-10 to U-19 age categories, Junior Development
and Elite Pathway programmes, the nine SOP §8 trial assessment criteria, the
enquiry sources from SOP §7, and the document types from SOP §12.

Nothing on this list may ever be hardcoded elsewhere in the codebase.

Check: an administrator adds a new programme through Django admin and it
appears in the API without a code change. seed_master_data is idempotent.
```

**Checkpoint:** commit `T-205 … T-206`.

---

## Session 4 · Audit, storage, notifications  (Weeks 4–5)

| # | Prompt | Where |
|---|---|---|
| 13 | Audit trail | `PROMPTS.md` §9 |
| 14 | S3 storage layer | `PROMPTS.md` §10 |
| 15 | Photograph handling | `PROMPTS.md` §11 |
| 16 | Notifications | `PROMPTS.md` §12 |

**Checkpoint:** a document uploads to MinIO without touching Django, an audited change writes an
uneditable diff, a test message dispatches on each channel. Commit `T-201 … T-210`.

---

## Session 5 · Design system, shell, first screens  (Week 5)

| # | Prompt | Where |
|---|---|---|
| 17 | Design system + primitives | `PROMPTS-PHASE1-SCREENS.md` §0 |
| 18 | App shell | `PROMPTS-PHASE1-SCREENS.md` §1 |
| 19 | Login screen only | `PROMPTS-PHASE1-SCREENS.md` §2 — **build LOGIN only; the register screen waits for the enquiry API in session 7** |

**20 · Admin screens** — full text here:

```
Build the administration screens in src/features/admin/.

- User list and detail, with role assignment (valid_from / valid_to)
- Permission matrix editor: roles down the side, module groups across,
  six verb checkboxes per cell. Save writes RolePermission rows. Warn
  before removing the last approve permission on a module.
- Audit log viewer: filters for model, object, actor, action, date range.
  Each row expands to show the field-level before/after diff. Export is
  behind the export verb and is itself audited.
- Document library with the verification queue: preview beside metadata,
  Verify and Reject with a mandatory reason.
- Notification template manager with per-channel variants and a preview
  that renders sample context.
- Master data screens, or link to Django admin — your call, but say which
  and why.

Check: changing a permission in the matrix editor takes effect on the next
request with no restart, and a role without the export verb sees no export
button AND gets 403 if it calls the endpoint directly.
```

**Checkpoint:** commit `T-107 … T-208`.

---

## Session 6 · Phase 0 gate  (Week 6)

**21 · Exit verification**

```
Read docs/05-build-sequence.md, the Phase 0 exit criteria.

Go through all five criteria one at a time. For each, write or point at the
test that proves it, run it, and show me the output. Do not tell me a
criterion passes without executing something.

Where a criterion is not yet met, list what is missing rather than
implementing it — I want the gap list before any fixing.
```

**22 · Security sweep**

```
Run an object-level authorisation sweep across every endpoint built so far.

For each: write a test where user A requests user B's object by ID. It must
return 404, not 403 — a 403 confirms the record exists.

Also verify: the audit table rejects UPDATE and DELETE at the database
level; presigned GET URLs never appear in list responses; OTP codes are
never logged or stored in plain text.

Report findings as a list before fixing anything.
```

**23 · Demo data and deploy**

```
Add `python manage.py seed_demo` producing a demo-ready database: one user
per role with known credentials, master data, and 10 sample people. It must
refuse to run when DEBUG is False.

Then deploy to staging and run a smoke test.

Check: a clean database plus `make seed` plus `seed_demo` gives a working
demo in under two minutes.
```

**Checkpoint:** Phase 0 gate signed. Commit `T-301 … T-306`. **`/clear` and take a break — Phase 1 starts fresh.**

---

## Session 7 · Enquiry  (Weeks 7–8)

**24 · Enquiry backend**

```
Read docs/01-data-model.md section 5 (Enquiry, EnquiryFollowUp) and
docs/02-api-spec.md, the Enquiry section.

Build apps/admissions/enquiry: models, migrations, serializers, viewsets,
filters, factories and tests.

Specifics:
- enquiry_no from core.services.numbering — never count()+1
- create() calls people.services.resolve_person() and returns duplicate
  candidates in the response rather than silently creating a Person
- POST /public/enquiries is unauthenticated, rate-limited and captcha-gated
- convert-to-trial carries every captured field forward (SOP §79)
- a conversion analytics endpoint: enquiry→trial→admission by source and
  period

Show me the migration before running it.

Check: a public submission creates an enquiry and sends an acknowledgement;
re-entering an existing person's details surfaces the match; two concurrent
creates produce two distinct enquiry numbers.
```

| # | Prompt | Where |
|---|---|---|
| 25 | Enquiry screens (capture, pipeline board, follow-up) | `PROMPTS-PHASE1-SCREENS.md` §4, first block |
| 26 | Public enquiry widget | `PROMPTS-PHASE1-SCREENS.md` §4, second block |
| 27 | Register screen | `PROMPTS-PHASE1-SCREENS.md` §2 — the REGISTER half you deferred in session 5 |
| 28 | Administration dashboard | `PROMPTS-PHASE1-SCREENS.md` §3, first block |

**Checkpoint — M2, first production release.** Enquiry goes live; the academy starts capturing
real enquiries while you build the rest. Commit `T-401 … T-412`.

---

## Session 8 · Trial  (Weeks 9–10)

**29 · Trial backend**

```
Read docs/01-data-model.md section 5 (Trial, TrialSlot, TrialRegistration,
TrialAssessment, TrialResult), docs/02-api-spec.md Trials, and
docs/04-state-machines.md section 3.

Build apps/admissions/trial.

Specifics:
- slot booking uses select_for_update on the slot. Overbooking is a defect,
  not an edge case — write the concurrent test.
- assessment criteria come from master data, not model fields
- POST assess accepts an Idempotency-Key header so an offline replay cannot
  double-write
- declaring a result sets is_locked on the assessment; editing a locked
  assessment requires an approval and writes an audit row
- shortlisted and waitlisted require a review_on date

Check: 30 concurrent bookings on a 20-capacity slot produce exactly 20
bookings and 10 rejections; the same assessment posted twice with one
idempotency key creates one row.
```

| # | Prompt | Where |
|---|---|---|
| 30 | Trial calendar + slot booking | `PROMPTS-PHASE1-SCREENS.md` §5, first block |
| 31 | **Coach assessment (tablet, offline)** | `PROMPTS-PHASE1-SCREENS.md` §5, second block |
| 32 | Result declaration | `PROMPTS-PHASE1-SCREENS.md` §5, first block (second half) |
| 33 | Head Coach + Coach dashboards | `PROMPTS-PHASE1-SCREENS.md` §3, blocks 2 and 3 |

**Checkpoint — M3.** Prompt 31 is the riskiest screen in Phase 1: run the offline sequence
(score three, close tab, reopen, reconnect) before calling it done. Commit `T-501 … T-511`.

---

## Session 9 · Admission  (Weeks 11–12)

**34 · Admission backend**

```
Read docs/01-data-model.md section 5 (Admission, AdmissionChecklistItem),
docs/02-api-spec.md Admissions, and docs/04-state-machines.md section 1.

Build apps/admissions/admission.

The state machine is the whole job. Implement all seven states with their
guards and permitted roles exactly as specified, plus the three rejected
transitions listed in the doc.

Also:
- pre-fill from enquiry and trial — no field is ever re-keyed (SOP §79)
- fee payment is a stub: reference number, or a waiver behind an approval
- direct admission records a reason and raises an approval; it does not
  fabricate a trial
- approval creates the Student and issues student_code in one transaction

Check: every one of the three rejected transitions returns 409 with a clear
code; approval creates exactly one Student; a rolled-back approval leaves no
orphan student_code consumed.
```

| # | Prompt | Where |
|---|---|---|
| 35 | Admission wizard, checklist, verification queue, approval screen | `PROMPTS-PHASE1-SCREENS.md` §6 |
| 36 | Academy Head dashboard | `PROMPTS-PHASE1-SCREENS.md` §3, fourth block |

**Checkpoint — M4.** Commit `T-601 … T-611`.

---

## Session 10 · Student profile  (Week 13)

**37 · Student backend**

```
Read docs/01-data-model.md section 5 (Student, StudentStatusHistory) and
docs/04-state-machines.md sections 2 and 5.

Build apps/admissions/student.

- all 11 SOP §11 statuses as guarded transitions with a mandatory reason
- only the Medical Team may set or clear medical_hold — not Head Coach, not
  Academy Head
- suspended and withdrawn require an ApprovalRequest
- withdrawn → active is NOT a transition; it is re-admission
- re-admission creates a new Student against the SAME Person and there must
  be no code path that creates a second Person
- a composite profile endpoint returning Personal, Parent, Cricket and
  Academy in one call

Check: a test per transition AND per rejected transition; a test proving
re-admission produces one Person and two Student rows with the prior history
intact.
```

| # | Prompt | Where |
|---|---|---|
| 38 | Student Master Profile, status dialog, re-admission | `PROMPTS-PHASE1-SCREENS.md` §7, first block |

**Checkpoint:** commit `T-701 … T-706`.

---

## Session 11 · ID card, parent, handoff  (Week 14)

**39 · ID card + Phase 2 stubs**

```
Read docs/01-data-model.md section 5 (IDCard, and the Phase 2 handoff stubs).

Build apps/admissions/idcard plus the two thin allocation stubs.

- QR payload is a SIGNED, expiring token, never the raw student ID
- GET /id-cards/resolve/{token} unauthenticated returns validity only;
  authorised scanners get the profile
- issuing a replacement invalidates the previous card and both stay in the
  issuance history
- batch print renders many cards to one server-side PDF
- BatchAllocation and CoachAllocation are DELIBERATELY thin — Phase 2
  replaces batch_ref with a real Batch FK. Do not build batch management.
- emit a student.activated domain event on training activation; the
  communication app listens and sends the schedule

Check: 50 cards render to one PDF; an unauthenticated QR scan reveals
nothing beyond validity; the activation event is consumed without the
idcard app importing the communication app.
```

| # | Prompt | Where |
|---|---|---|
| 40 | ID card designer + batch print | `PROMPTS-PHASE1-SCREENS.md` §7, second block |
| 41 | Parent child-profile view | `PROMPTS-PHASE1-SCREENS.md` §7, third block |

**Checkpoint — M5, feature complete.** Commit `T-801 … T-807`.

---

## Session 12 · Integration, migration, go-live  (Weeks 15–16)

**42 · The chain test and hardening**

```
Write tests/test_admission_chain.py — a single automated test running all 13
SOP §9 steps for one candidate, end to end, from public enquiry submission
to training activation. It runs in CI on every commit from now on.

Then:
- a performance pass: find and fix N+1 queries on every list endpoint, add
  the missing indexes, confirm cursor pagination everywhere
- a Playwright suite on the critical journeys: enquiry → activation,
  offline assessment → sync, document upload → verification

Check: the chain test passes; the profile and pipeline screens load under
400ms p95 against 5,000 seeded students.
```

**43 · Legacy migration and cutover**

```
Build the legacy data migration in apps/core/management/commands/.

- import_legacy_people, import_legacy_students, import_legacy_coaches
- every migrated row carries legacy_source and legacy_id
- a --dry-run mode reporting what would be created, updated and skipped
- a duplicate sweep over the imported set that must be run BEFORE go-live,
  because migrating duplicates violates SOP §78 on day one and is far harder
  to unpick once transactions reference both copies

Then the production cutover checklist: backups with 30-day retention and a
tested restore, monitoring and alerting, and a runbook.

Check: --dry-run on the real export reports zero unresolved duplicates
before the live import runs.
```

**Checkpoint — M6, go-live.** Commit `T-901 … T-1005`.

---

## Progress sheet

```
Session  1  Scaffolding                    [ ]  W1
Session  2  Identity spine                 [ ]  W2–3
Session  3  Approvals & master data        [ ]  W4
Session  4  Audit, storage, notifications  [ ]  W4–5
Session  5  Design system & shell          [ ]  W5
Session  6  Phase 0 gate            M1     [ ]  W6
Session  7  Enquiry                 M2     [ ]  W7–8    ← first production release
Session  8  Trial                   M3     [ ]  W9–10
Session  9  Admission               M4     [ ]  W11–12
Session 10  Student profile                [ ]  W13
Session 11  ID card & parent        M5     [ ]  W14
Session 12  Integration & go-live   M6     [ ]  W15–16
```

## If something goes wrong mid-session

The correction table at the end of `PROMPTS.md` has the exact wording for the eight common
drifts — invented fields, hardcoded roles, direct status assignment, proxied uploads, skipped
tests, suspect migrations, and scope creep into a later phase.

The one worth memorising: **"That field is not in docs/01-data-model.md. Re-read section N and
use only what is specified."** Let one invented field through and the next twenty assume it.
