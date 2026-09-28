# Role-based access control

16 roles (SOP §5) × 6 verbs (SOP §69). This is **seed data**, loaded by
`python manage.py seed_roles`. Never hardcode a role name in application code.

Legend: `V` view · `A` add · `E` edit · `P` approve · `X` export · `O` own records only · `-` no access

Verbs the SOP names but this system folds into others: **Print** is a distinct verb on
`idcard` and `trial` only; elsewhere printing is a client-side action on data the user
may already view.

## Matrix

| Module group | Slug(s) | Acad.Mgmt | Acad.Head | SportsOps | Admin | Accounts | HeadCoach | Coach | S&C | Medical | Physio | Hostel | Transport | AthleteMgmt | Student | Parent | ITAdmin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Enquiry / Admission**² | `enquiry, admission` | VX | VAEPX | VAE | VAE | V | VAE | VA | - | - | - | - | - | V | - | - | V |
| **Trial**² | `trial` | VX | VAEPX | VAE | VAE | V | **VAEP** | VA | - | - | - | - | - | V | - | - | V |
| **ID Card**¹ | `idcard` | VX | VAX | V | VA | - | V | - | - | - | - | - | - | - | O | O | V |
| **Student Master Profile** | `students` | VX | VAEPX | VAE | VAE | V | V | V | V | V | V | V | V | V | O | O | V |
| Student profile completion⁴ | `student_profile` | VX | VAEPX | VAE | VAE | V | V | V | V | V | V | V | V | V | OE | OE | V |
| **Documents** | `documents` | VX | VAEPX | VAE | VAEP | V | - | - | - | V | - | V | - | V | O | OA | V |
| Batch / Training | `batch` | VX | VAEPX | VAE | VAE | - | VAEP | VAE | VAE | V | V | V | - | V | O | O | V |
| Batch management⁵ | `batch_admin` | V | VAEX | V | VAE | - | VAE | V | V | V | V | V | - | V | - | - | V |
| Attendance⁴ | `attendance` | VX | VAEPX | VAE | VAEP | - | VAEP | **OAE** | VAE | V | V | V | - | V | O | O | V |
| Fees / Payments / Discounts | `fees` | VX | VAEPX | V | VAE | VAEPX | - | - | - | - | - | V | V | - | O | O | V |
| Direct-admission payment verification / unified ledger³ | `payment` | V | V | - | VAEP | VAEP | - | - | - | - | - | - | - | - | O | O | V |
| Performance & IDP | `performance` | VX | VAEPX | VAE | V | - | VAEP | VAE | VAE | V | V | - | - | V | O | O | V |
| Coach Evaluation | `coach_evaluation` | VX | VAEPX | VAE | V | - | VAE | O | - | - | - | - | - | - | - | - | V |
| Medical & Injury (confidential) | `medical` | V | V | - | - | - | V | - | V | VAEPX | VAE | V | - | - | O | O | - |
| Match / Tournament / Statistics | `competition` | VX | VAEPX | VAE | VAE | - | VAEP | VAE | V | V | V | - | - | VX | O | O | V |
| Athlete Profile / Rating / Media | `athlete` | VX | VAEPX | V | - | - | VAE | V | V | V | - | - | - | VAEPX | O | O | V |
| Scouting / Opportunity / Placement | `scouting` | VX | VAEPX | V | - | - | V | - | - | - | - | - | - | VAEPX | - | - | V |
| Contracts / Commercial / Revenue | `commercial` | VAEPX | VAEPX | - | - | VX | - | - | - | - | - | - | - | VAE | - | - | - |
| Residential / Transport | `residential, transport` | VX | VAEPX | VAE | VAE | V | - | - | - | V | - | VAEP | VAEP | - | O | O | V |
| Equipment / Facility | `equipment, facility` | VX | VAEPX | VAEP | VAE | V | VAE | VA | VAE | - | - | VA | VA | - | - | - | V |
| **Communication** | `communication` | VAEPX | VAEPX | VAE | VAE | VA | VAE | VA | - | VA | - | VA | VA | VAE | O | O | V |
| Complaints / Incidents / Discipline | `grievance` | VAEPX | VAEPX | VAEP | VAE | V | VAEP | VA | VA | VA | VA | VAE | VA | V | OA | OA | V |
| **Reports & MIS** | `reporting` | VX | VX | VX | VX | VX | VX | V | V | V | V | V | V | VX | - | - | VX |
| **User Access & Roles** | `iam` | V | VP | - | - | - | - | - | - | - | - | - | - | - | - | - | VAEPX |
| **Audit Trail** | `audit` | VX | VX | - | - | V | - | - | - | - | - | - | - | - | - | - | VX |

Rows in **bold** are the module slugs Phase 0 and Phase 1 actually implement.
The rest are seeded now so the matrix is complete, but have no endpoints yet — the
permission-matrix test skips modules with no registered endpoints.

² Originally one bundled "Enquiry / Trial / Admission" row with Head Coach at `VAE` throughout. Split
so Head Coach can hold `approve` on `trial` only (needed to declare trial results — SOP narrative and
docs/02-api-spec.md's `trial/approve` result endpoint) without also gaining it on `admission`, which
stays Academy Head's alone (enforced independently by `ApprovalRule.required_role` regardless of this
coarser verb grant, but there is no reason to widen the verb grant past what's actually used).

³ `payment` is new for the fee-first direct-admission wizard's `/admissions/{id}/verify-payment/` —
replaces the old trial-chain's hardcoded `"accounts" in held_roles` check on `record-payment`
(`AdmissionRecordPaymentView`, still in place for that older endpoint) with real RBAC data, per
CLAUDE.md rule 3. Administration and Accounts both get `approve`, the same dual-role precedent
docs/04-state-machines.md already documents for the trial chain's own `fee_pending -> fee_cleared`.
`student`/`parent` hold own-scope `V` only, for the unified payment ledger's portal view
(`GET /students/me/payments/`, `GET /parents/me/children/{id}/payments/`) — recording and
settling a payment stay Administration/Accounts-only.

⁴ Split from the bundled `batch, training, attendance` row above for the same reason as ².
`POST /corrections/{id}/approve/` (deciding an `AttendanceCorrection`) was originally Head Coach
only per SOP §70 — since widened to Administration and Academy Head too (both now `P`), the
same multi-role decision-maker precedent `payment`'s row already uses for settling a payment.
`coach`'s cell is `OAE` (own scope), not `VAE` (all scope): a Coach only sees, marks or cancels
attendance for sessions where they are `TrainingSession.coach` — enforced at the queryset level
by `SessionAttendanceViewSet`/`AttendanceViewSet`/`AttendanceCorrectionViewSet`/
`BatchReportViewSet`'s `filter_to_own`, same rule 3 as every other own-scope grant below.
Administration, Academy Head, Head Coach and S&C are unaffected (still `all` scope).

⁵ New — `batch` grants create/edit/delete broadly (Sports Ops, Coach, S&C all get `A`/`E`
there too, for enrolling/transferring students), but only Administration, Academy Head and Head
Coach may create, edit or delete the *Batch record itself*. Same "split the row" pattern as
every other footnote here, applied per-action via `ModuleScopedViewSet.action_modules` rather
than per-ViewSet — `BatchViewSet`'s `list`/`retrieve`/`enrol` still check `batch`, only
`create`/`update`/`partial_update`/`destroy` check `batch_admin`. Edit and delete are further
restricted in code (not data) to a batch that hasn't started yet (no `TrainingSession` with
`date <= today`), and delete is refused outright if the batch has ever had an enrolment.
`POST /sessions/{id}/delete/` (a hard delete of one `TrainingSession`, distinct from
`.../cancel/`'s soft not-conducted flip) also checks `batch_admin` for the same reason — a bigger
authority than the `attendance` module's own-scope Coach grant, which still covers
`.../update-details/` (reschedule + edit training_type/objective/report on your own session),
`.../cancel/`, `.../attendance/` (bulk mark) and `.../mark-conducted/` (flip `is_conducted` True —
nothing else in the codebase ever does).
Both `.../delete/` and a schedule-field change via `.../update-details/` are refused in code once
the session started more than 24 hours ago or it already has attendance recorded — cancel it
instead so the history survives; unlike `.../cancel/`/`.../attendance/`/`.../mark-conducted/`
below, these two stay available for a session that **hasn't** started yet — rescheduling and
deleting are exactly the tools for a session that hasn't happened, so only the upper bound
applies to them. `.../cancel/`, `.../attendance/` and `.../mark-conducted/` share a *closed*
24-hour window instead — not just an upper bound: refused both before the session's scheduled
start (nothing to mark, confirm or cancel yet — `SessionNotYetStarted`, 409) and more than 24
hours after it (`SessionWindowClosed`, 409). That window is not tied to `date <= today` on either
side, so a session run late in the evening or logged the next morning isn't locked out, and a
same-day session dated ahead of its actual start time is refused exactly like a future one.
Unlike delete/reschedule, these three are never blocked by attendance already existing — that's
the whole point of `.../cancel/` and `.../mark-conducted/`. Both boundaries are enforced in
`apps.academics.attendance.services` itself, the same way `SessionNotEditable`'s own boundary
always has been — they apply to *every* caller of all five actions regardless of role (own-scope
Coach or an all-scope role alike), not just Coach; once a session's mark window is closed, only
an `AttendanceCorrection` (for already-marked attendance) can still change the record.

⁴ `student_profile` is new for the profile-completion feature (Prompt G) — split from `students`
because that module's own-scope grant for Student/Parent is view-only, and several of its `edit`
actions (status changes, guardian management, login access) are staff-only. Widening `students`
itself would have handed student/parent users those too; this module covers only the 24-field
profile-completion form (`GET/PATCH /students/{id}/profile/`).

¹ `idcard` had no row at all before Phase 1 built the module (flagged, not guessed at, by
`seed_roles.py`). This row is a provisional best-effort reading of SOP step 10 (Administration
issues the card; Academy Head has the same full oversight it has everywhere else; Head Coach,
Student and Parent can view) — **pending Academy Head sign-off**, the same as D-01–D-03. Treat it
like the numbering formats: safe to build against now, expensive to change after cards are
printed with a QR payload that encodes today's assumptions.

## Print — a verb the letter-grid can't express

**Print** is a distinct verb on `idcard` and `trial` only (mentioned above the matrix), and it
cannot be written as a matrix letter: `P` already means Approve in every cell. It is granted
separately, in `apps.core.management.commands.seed_roles.PRINT_ROLES`, additively on top of
whatever the row above already grants:

| Module | Roles granted `print` | Why |
|---|---|---|
| `trial` | Administration, Head Coach, Coach, IT Admin | The trial-sheet print fallback (docs/05-build-sequence.md T-506) is used ground-side by whoever is running the trial, not only by whoever booked it. |
| `idcard` | Administration, Academy Head, IT Admin | `POST /id-cards/batch-print` — printing *other people's* cards in bulk is an operational action, gated separately from viewing any single one. |

`GET /id-cards/{id}/render.pdf` (one card) is deliberately **not** gated on `print` — it uses
the plain `view` verb instead, same as every other detail endpoint. Opening your own card's
PDF is a `view`, not a `print`; gating it on the `print`-only roles above left Student and
Parent — who already hold `idcard`/`view` scope `own` — unable to open the one card they're
actually entitled to see (a 403 caught 2026-09-07). `print` still gates `batch-print`
specifically, which really is an admin/ops bulk action.

## Rules that override the matrix

These are enforced in code, not data, because they are safety and confidentiality
requirements rather than configuration:

1. **Medical records** are readable by the Medical Team and Physiotherapist only.
   Academy Management and Head Coach see *availability status*, never clinical detail.
   Every read is written to the audit log. (Phase 5, but enforce the role now.)
2. **Commercial terms** in contracts and representation agreements are visible to Academy
   Management, Academy Head and Athlete Management only. (Phase 9.)
3. **Parents and students** (`scope="own"`) see only their own records. This is enforced
   at the queryset level *and* checked per object. Requesting another person's record
   returns **404**, not 403 — do not confirm that the record exists.
4. **Export is separate from View.** A role that can see a list cannot necessarily export
   it. Every export writes an audit row with the filter applied and the row count.
5. **No role has unrestricted access** except IT Admin on `iam` and `audit`, and even
   IT Admin cannot read medical records or commercial terms.

## Implementation

```python
user.has_perm_for("admission", "approve")   # the only permission check in the codebase
```

Resolved from `UserRole → RolePermission → Permission`, cached per request. A user holding
several roles gets the union of their permissions, and the *widest* scope among them.
