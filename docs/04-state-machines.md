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
| `approved` | *(terminal)* | — | Creates `Student`, issues `student_code`, sets status `active` | — |

**Rejected transitions that must be tested:**
- `draft → approved` (skipping steps) → 409
- `documents_pending → fee_cleared` with an unverified mandatory document → 409
- Approval attempted by a role without the `approve` verb on `admissions` → 403

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
