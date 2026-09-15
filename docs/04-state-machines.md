# State machines

Every status in this system is a state machine with guards and permitted roles, not a free
text field. Never assign a status field directly — call the transition method, which
validates the guard, checks the role, requires a reason where marked, and writes the audit row.

Implementation: `core.state.StateMachine` base class. Each transition is declared, tested for
success **and** for rejection.

---

## 1. Admission chain (SOP §9)

The 13 SOP steps collapse into 7 persisted states on `Admission.step`, because steps 1–5
live on `Enquiry` and `TrialRegistration`, and steps 11–13 happen after `Student` exists.

| From | To | Permitted roles | Guard | Reason required |
|---|---|---|---|---|
| — | `draft` | Administration | Source is a `selected` trial result, OR a `trial_waiver_approval` exists and is approved | no |
| `draft` | `documents_pending` | Administration | All checklist items created for the programme | no |
| `documents_pending` | `documents_verified` | Administration | **Every mandatory** `AdmissionChecklistItem.status == verified` | no |
| `documents_verified` | `fee_pending` | Administration | — | no |
| `fee_pending` | `fee_cleared` | Accounts, Administration | `fee_payment_status in (paid, waived)`; a waiver needs an approved `ApprovalRequest` | on waiver |
| `fee_cleared` | `approved` | Academy Head (per `ApprovalRule`) | Approval request approved | no |
| `fee_cleared` | `rejected` | Academy Head | — | **yes** |
| `documents_verified` | `documents_pending` | Administration | A verified document was later rejected or expired | **yes** |
| `fee_cleared` | `fee_pending` | Accounts, Administration | A recorded payment was marked unpaid (bounced UPI/card, entered in error) | **yes** (fixed reason string) |
| `approved` | *(terminal)* | — | Creates `Student`, issues `student_code`, sets status `active` | — |

**How the approval gate actually works (implementation note):** reaching `fee_cleared`
automatically raises the `ApprovalRequest` for `(admission, "approve")` — Administration
doesn't take a separate "request approval" action. The Academy Head decides it via the
generic `POST /approvals/{id}/approve`; that alone does **not** flip `Admission.step` (the
generic approval endpoint knows nothing about admissions specifically). A separate call to
`POST /admissions/{id}/approve` — gated on the `admission`/`approve` verb, checked
independently of the `ApprovalRule.required_role` the decision itself required — is what
commits the already-decided approval into the actual `Student`-creating transition. Direct
admission's `draft` waiver gate works the same way: `POST /admissions/direct` raises the
`(admission, "trial_waiver")` request itself, since there is no earlier state for a separate
trigger to fire from.

**Manual fee collection (implementation note):** `POST /admissions/{id}/record-payment` is
deliberately manual for Phase 1 — UPI/card/cash reference plus a `payment_method`, or a waiver
reason, or `mark_unpaid` to correct one of those. It also *is* the `fee_pending → fee_cleared`
(and reverse, on `mark_unpaid`) transition — recording the payment and clearing the gate are the
same call, not two, so Accounts (permitted on this transition but holding no `admission`/`edit`
verb at all — see docs/02-api-spec.md's footnote on this endpoint) never needs the separately-gated
`/advance` endpoint. The `approved` guard also re-checks `fee_payment_status` itself, not only
that a decision was made — an admission marked unpaid after reaching `fee_cleared` must still
refuse approval even if step regression hadn't happened yet.

**Rejected transitions that must be tested:**
- `draft → approved` (skipping steps) → 409
- `documents_pending → fee_cleared` with an unverified mandatory document → 409
- Approval attempted by a role without the `approve` verb on `admissions` → 403
- `approved` with `fee_payment_status` no longer `paid`/`waived` (marked unpaid after the fact) → 409

### The full 13-step chain and where each step lives

| # | SOP step | Where it is recorded |
|---|---|---|
| 1 | Enquiry | `Enquiry` created, `enquiry_no` issued |
| 2 | Registration | `TrialRegistration` created from the enquiry |
| 3 | Trial | `TrialRegistration.attended = True` |
| 4 | Assessment | `TrialAssessment` + scores |
| 5 | Selection | `TrialResult.outcome = selected` |
| 6 | Admission | `Admission` opens in `draft`, pre-filled from steps 1–5 |
| 7 | Document verification | `documents_pending → documents_verified` |
| 8 | Fee payment | `fee_pending → fee_cleared` (Phase 1 stub; real engine is Phase 3) |
| 9 | Approval | `fee_cleared → approved`; `Student` created, `student_code` issued |
| 10 | ID card | `IDCard` issued |
| 11 | Batch allocation | `BatchAllocation` stub (Phase 2 replaces) |
| 12 | Coach allocation | `CoachAllocation` stub |
| 13 | Training activation | Domain event `student.activated` → schedule notification to parent |

---

## 2. Student status (SOP §11)

All 11 statuses. `Student.status`.

| Status | Meaning | Entered from | Who may set |
|---|---|---|---|
| `enquiry` | Pre-student. Held on `Enquiry`, not `Student` | — | system |
| `trial` | Pre-student. Held on `TrialRegistration` | — | system |
| `selected` | Trial passed, admission not yet opened | — | Head Coach |
| `admission_pending` | Admission in progress | selected | Administration |
| `active` | Training | admission_pending, medical_hold, fee_hold, leave, suspended | system on approval; Administration |
| `medical_hold` | Cannot train — medical | active | **Medical Team only** |
| `fee_hold` | Cannot train — fees | active | Accounts (policy rule, not manual whim) |
| `leave` | Approved absence | active | Administration |
| `suspended` | Disciplinary | active | Academy Head + approval |
| `withdrawn` | Left the academy | active, leave, suspended, fee_hold | Academy Head + clearance (Phase 11) |
| `completed` | Programme finished | active | Administration |

**Rules:**
- Every transition requires a `reason` and writes a `StudentStatusHistory` row. No exceptions.
- `active → suspended` and `→ withdrawn` require an `ApprovalRequest`.
- Only the Medical Team may set or clear `medical_hold`. Not the Head Coach, not the
  Academy Head. Clearing it in Phase 5 will require a fitness clearance.
- `withdrawn → active` is **not** a transition. That is re-admission: a new `Student` record
  on the **same** `Person`, with the prior record retained. See §5 below.
- A student not in `active` cannot be added to a training session or a trial squad.

**How the approval gate actually works (implementation note):** `POST /students/{id}/status`
is one endpoint for every transition, approval-gated or not. For `suspended`/`withdrawn`,
calling it the first time — while no *approved* `ApprovalRequest` exists yet for this
`(student, action)` pair — raises one (reusing a pending one if a second call arrives before
it's decided) and returns `202 {status: "approval_pending", approval_request_id}` *without*
changing `Student.status`. An authorised approver decides it via the generic
`POST /approvals/{id}/approve`. Calling `POST /students/{id}/status` again with the same
`to_status` and `reason` then finds the approval decided and completes the transition. This
is the same two-call shape `Admission`'s `fee_cleared → approved` gate uses — see the
admission chain table below.

**Student portal login is not granted automatically.** `apps.admissions.trial.services.
_resolve_or_create_person` sets a trial candidate's own `Person.mobile` to their *guardian's*
mobile (a minor usually has no phone of their own yet at that stage), so a just-approved
`Student`'s number is normally identical to the guardian's. OTP login (`POST /auth/otp/verify`)
requires exactly one `User` per mobile number, so provisioning logins for both at admission
time would make login ambiguous — and fail — for both people. `POST /students/{id}/login-access`
(docs/02-api-spec.md) is the explicit, Administration-triggered action instead: it can update
the student's own mobile first, then provisions their login only once that number is distinct
from every guardian already mapped to them via `POST /students/{id}/guardians`.

---

## 3. Trial result (SOP §8)

`TrialResult.outcome`, set once by the Head Coach.

| Outcome | Effect |
|---|---|
| `selected` | Enables admission. Notification: congratulations + next steps |
| `shortlisted` | Held pending capacity. `review_on` required |
| `waitlisted` | `review_on` required. Appears on the daily administration worklist until resolved |
| `not_selected` | Notification sent. Enquiry closes as `lost` |
| `re_trial` | New `TrialRegistration` may be created linked to the same enquiry |

Declaring any outcome sets `TrialAssessment.is_locked = True`. Editing a locked assessment
requires an approval and is audited.

**A waitlist that is never worked is a lost revenue list.** `review_on` is mandatory for
`shortlisted` and `waitlisted`, and overdue reviews surface on the worklist.

**Resolving a waitlist/shortlist (implementation note):** "set once" above is true of
`selected`/`not_selected`/`re_trial` — those are final, and redeclaring one raises a 409. A
`shortlisted`/`waitlisted` result is explicitly *not* final ("held pending capacity", "until
resolved"), so `POST /trials/registrations/{id}/result` on a registration whose existing result
is still one of those two updates it in place to the new outcome instead of refusing. This is the
answer to "the candidate didn't get in on trial day — how do they get another chance without a
whole new enquiry": a spot opens up, the Head Coach re-declares the same registration as
`selected`, no new `TrialRegistration` needed. `re_trial` is the other path (SOP-named), for when
the candidate should be assessed fresh rather than have the same-day result reconsidered — that
one still creates a second `TrialRegistration` against the same enquiry.

---

## 4. Document lifecycle (SOP §12)

`Document.status`.

| From | To | Who | Notes |
|---|---|---|---|
| — | `pending` | system | Checklist item created, nothing uploaded |
| `pending` | `submitted` | Administration, Parent | File uploaded and confirmed |
| `submitted` | `verified` | Administration | `verified_by` and `verified_at` recorded |
| `submitted` | `rejected` | Administration | `rejection_reason` **required**; parent notified |
| `rejected` | `submitted` | Administration, Parent | Re-upload |
| `verified` | `expired` | system (Celery daily) | `expires_on` passed |
| `expired` | `submitted` | Administration, Parent | Renewal uploaded |

**Edge case that must be handled:** a document that is rejected or expires *after* the
admission was approved moves the admission back to `documents_pending` and the student to a
documented hold. It does not silently continue. The approval that permitted it stays on record.

---

## 5. Re-admission (SOP §67, §78)

Not a status transition. The flow:

1. Administration searches by name, DOB or guardian mobile.
2. `resolve_person()` returns the existing `Person` with its prior `Student` record(s).
3. A **new** `Student` row is created against the **same** `Person`, with a new
   `student_code` and a new `admission`.
4. The prior `Student` record keeps `status = withdrawn` and all of its history.
5. Everything attached to the `Person` — documents, guardians, and later attendance, fees,
   performance, achievements and medical records — remains reachable.

**The system must refuse to create a second `Person`, not merely warn.** A warning that can
be clicked past becomes a duplicate within a week of go-live.
