# Build sequence

Work one task at a time, in this order. Finish a task's **acceptance check** before
starting the next one. Task ids match the sprint tracker, so `T-501` here is `T-501` in
the manager's spreadsheet — use them in branch names and commit messages.

Hours are for a solo developer working with Claude Code, at roughly 34 productive hours
per week.

> **Before Sprint 1 starts**, decisions D-01 (numbering), D-02 (duplicate rule) and D-03
> (RBAC matrix) must be signed. Building the identity spine against an unconfirmed
> numbering scheme is the one mistake in this project that is genuinely expensive to undo.

## Sprint 0 — Week 1  (34h)

*Decisions locked, repo running, CI green, staging reachable.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-001` | Decisions | Agree ID & numbering scheme | 4 | — | Academy Head signs the format. No format changes accepted after Week 2. |
| `T-002` | Decisions | Confirm role list and RBAC matrix | 4 | — | Academy Management signs. Loaded as seed data, not code. |
| `T-003` | Decisions | Map admission funnel and student status machine | 6 | — | Administration and Head Coach confirm each step's actor and gate. |
| `T-004` | DevOps | Scaffold repository and native local environment | 4 | — | `make dev` starts web, worker, beat and frontend from a clean clone. |
| `T-005` | DevOps | Write the Claude Code kit into the repo | 3 | T-001,T-002,T-003 | Claude Code produces a correct model file from the spec without further prompting. |
| `T-006` | Frontend | Scaffold the React application | 5 | T-004 | Frontend builds clean and calls a health endpoint on the API. |
| `T-007` | DevOps | Set up CI pipeline | 4 | T-004,T-006 | Pipeline green on an empty project. A failing test blocks merge. |
| `T-008` | DevOps | Provision the staging environment | 4 | T-007 | A deploy from main reaches staging automatically. |

## Sprint 1 — Weeks 2-3  (68h)

*Identity spine and access control. Nothing else may be built until this is right.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-101` | Backend | Person model and duplicate-detection service | 8 | T-005 | Creating a Person that matches an existing one is refused and returns the match. SOP Sec.78. |
| `T-102` | Backend | User, Guardian and Staff models | 5 | T-101 | One guardian with two children is one Guardian record. |
| `T-103` | Backend | Role and permission models with seed data | 6 | T-002,T-102 | Changing a permission row changes behaviour with no code release. |
| `T-104` | Backend | Permission enforcement layer | 8 | T-103 | A role without Export can view a list but receives 403 on the export endpoint. |
| `T-105` | Backend | Authentication | 8 | T-102 | A parent logs in with an OTP and never needs a password. |
| `T-106` | QA | Permission matrix test harness | 8 | T-104 | Adding an endpoint without a matrix entry fails the build. Highest-value suite in the project. |
| `T-107` | Frontend | Auth flow and role-driven navigation | 10 | T-105,T-006 | A coach signing in sees no finance menu item, and the route is blocked server-side too. |
| `T-108` | Frontend | User, role and permission admin screens | 12 | T-103,T-107 | An administrator changes a role's permissions from the UI and the effect is immediate. |
| `T-109` | QA | Sprint 1 test pass and fixes | 3 | T-106 | Coverage gate met on the iam and people apps. |

## Sprint 2 — Weeks 4-5  (68h)

*Audit, documents, notifications, approvals, master data — the shared services every later module consumes.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-201` | Backend | Audit trail engine | 8 | T-104 | Every change to an audited model writes a before/after row automatically, with no per-view code. |
| `T-202` | Backend | Make the audit trail immutable | 3 | T-201 | The application database user cannot UPDATE or DELETE an audit row. SOP Sec.70. |
| `T-203` | Backend | Document management | 8 | T-104 | A 20 MB file uploads straight to S3 without passing through the API server. |
| `T-204` | Backend | Notification service | 10 | T-004 | A test message dispatches on each channel and its delivery status is recorded. |
| `T-205` | Backend | Generic approval engine | 7 | T-103 | Demonstrated end to end on one dummy object; later reused by admission, discounts and discipline. |
| `T-206` | Backend | Master data models and admin | 5 | T-103 | Administration can add a new programme or venue without a developer. |
| `T-207` | Frontend | Audit viewer and document library | 10 | T-201,T-203 | A finance user can trace who changed a record, when, and from what to what. |
| `T-208` | Frontend | Notification templates and master data screens | 9 | T-204,T-206 | A message template is edited and the next dispatch uses it. |
| `T-209` | DevOps | Celery, Redis and beat deployment | 4 | T-008 | A scheduled job fires on staging and is visible in logs. |
| `T-210` | QA | Sprint 2 test pass and fixes | 4 | T-205 | Coverage gate met. Audit immutability proven by a failing-write test. |

## Sprint 3 — Week 6  (34h)

*Phase 0 closes. Exit criteria verified, security swept, demo delivered.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-301` | QA | Phase 0 exit-criteria verification | 6 | T-210 | All five criteria demonstrably true on staging. |
| `T-302` | QA | Security sweep | 6 | T-106 | No endpoint returns another user's object by id. Attempts are logged. |
| `T-303` | Data | Seed and demo data | 4 | T-206 | A clean database can be seeded to a demo-ready state with one command. |
| `T-304` | DevOps | Staging deployment and smoke test | 5 | T-209 | Deploy from main, smoke suite passes, errors surface in Sentry. |
| `T-305` | Delivery | M1 demo to management and fixes | 8 | T-301,T-304 | Academy Management sign the Phase 0 gate. |
| `T-306` | Delivery | Publish API schema and developer docs | 5 | T-304 | A new developer can run the project and read the contract without asking. |

## Sprint 4 — Weeks 7-8  (68h)

*Enquiry management. Ships to production at the end — first real business value.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-401` | Backend | Enquiry model and number generator | 5 | T-101 | Enquiry number follows the signed format and never collides under concurrency. |
| `T-402` | Backend | Duplicate detection at enquiry intake | 4 | T-401 | Entering a former student's details surfaces the existing record instead of creating a new one. |
| `T-403` | Backend | Follow-up tracking and reminders | 5 | T-401,T-204 | An overdue follow-up appears on the daily worklist and notifies its owner. |
| `T-404` | Backend | Enquiry API | 6 | T-401 | Conversion creates a trial registration carrying every field already captured. SOP Sec.79. |
| `T-405` | Backend | Public enquiry endpoint | 5 | T-404 | A website submission creates an enquiry and sends an acknowledgement. Abuse is throttled. |
| `T-406` | Backend | Acknowledgement notification | 3 | T-405,T-204 | Parent receives an acknowledgement within a minute of submitting. |
| `T-407` | Frontend | Enquiry capture form | 8 | T-402,T-107 | Duplicate candidates appear as the name and DOB are typed. |
| `T-408` | Frontend | Enquiry pipeline board | 12 | T-404 | An administrator sees every open enquiry and what it is waiting on. |
| `T-409` | Frontend | Follow-up panel and reminder list | 6 | T-403 | Nothing sits in the pipeline without a next action date. |
| `T-410` | Frontend | Public enquiry widget | 6 | T-405 | Embeds in the existing site with one script tag. |
| `T-411` | Backend | Conversion analytics | 4 | T-404 | Rates are computable from data with no manual counting. |
| `T-412` | QA | Sprint 4 test pass, M2 release | 4 | T-408 | Administration begins capturing real enquiries in production. |

## Sprint 5 — Weeks 9-10  (68h)

*Trial management, including offline-tolerant assessment on a tablet.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-501` | Backend | Trial, slot and registration models | 6 | T-404 | A slot cannot be overbooked. |
| `T-502` | Backend | Slot booking and trial fee handling | 5 | T-501 | Trial fee is recognised with no student attached. |
| `T-503` | Backend | Trial assessment model | 7 | T-501 | Criteria and scale change without a code release. |
| `T-504` | Backend | Result declaration workflow | 5 | T-503,T-201 | A declared result cannot be silently changed. |
| `T-505` | Backend | Bulk result notification | 4 | T-504,T-204 | Fifty parents are notified of trial outcomes in one operation. |
| `T-506` | Backend | Trial API and trial-sheet export | 6 | T-503 | Coaches can print the day's trial sheet as a fallback. |
| `T-507` | Frontend | Trial calendar and slot booking | 9 | T-502 | An administrator books a candidate into a slot in under 30 seconds. |
| `T-508` | Frontend | Coach assessment screen | 10 | T-503 | A coach scores a candidate on a tablet without pinch-zooming. |
| `T-509` | Frontend | Offline assessment queue | 8 | T-508 | Assessments recorded with no network sync automatically when connectivity returns. |
| `T-510` | Frontend | Result declaration screen | 6 | T-505 | Head Coach declares a full trial day's results in one screen. |
| `T-511` | QA | Sprint 5 test pass, M3 release | 2 | T-509 | Trial management live in production. |

## Sprint 6 — Weeks 11-12  (68h)

*Admission with its seven gated steps and document verification.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-601` | Backend | Admission model and checklist | 6 | T-504 | An admission opens only from a Selected trial or an approved direct-admission waiver. |
| `T-602` | Backend | Admission state machine | 7 | T-003,T-205 | No step can be skipped. Attempting to skip returns a clear error. |
| `T-603` | Backend | Pre-fill from enquiry and trial | 5 | T-601 | Opening an admission from a trial requires entering only genuinely new data. SOP Sec.79. |
| `T-604` | Backend | Document checklist and verification gate | 6 | T-203,T-601 | Approval is impossible with an unverified mandatory document. |
| `T-605` | Backend | Fee payment stub | 4 | T-602 | Admission fee gate passes on a recorded payment or an approved waiver. |
| `T-606` | Backend | Approval routing | 4 | T-205,T-602 | Approver is recorded; unauthorised users cannot approve. |
| `T-607` | Backend | Direct admission (trial waiver) | 3 | T-602 | Reputation or referral admissions are traceable, not disguised. |
| `T-608` | Frontend | Admission wizard | 12 | T-603 | An administrator completes an admission in one sitting without losing work. |
| `T-609` | Frontend | Document verification queue | 8 | T-604 | A rejected document notifies the parent with the reason. |
| `T-610` | Frontend | Admission approval screen | 6 | T-606 | Academy Head approves without opening five screens. |
| `T-611` | QA | Sprint 6 test pass, M4 release | 7 | T-610 | Admission and document verification live in production. |

## Sprint 7 — Week 13  (34h)

*Student Master Profile and the 11-status state machine.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-701` | Backend | Student model and code generator | 5 | T-606 | Student ID issued on approval, following the signed format. |
| `T-702` | Backend | Student status state machine | 7 | T-003,T-701 | Only authorised users change status; every change is explained and logged. |
| `T-703` | Backend | Composite profile endpoint | 4 | T-701 | The profile screen loads from one request. |
| `T-704` | Backend | Re-admission flow | 6 | T-102,T-701 | Re-admitting a former student creates no second profile. SOP Sec.67 and 78. |
| `T-705` | Frontend | Student Master Profile screen | 10 | T-703 | A coach sees the cricket tab but cannot edit fee fields. |
| `T-706` | Frontend | Status change dialog | 2 | T-702 | Status changes require a reason before the save button enables. |

## Sprint 8 — Week 14  (34h)

*ID card, parent view, and the Phase 2 handoff stubs. Feature complete.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-801` | Backend | ID card model and QR | 5 | T-701 | Replacement history is retained; old cards are invalidated. |
| `T-802` | Backend | ID card PDF rendering | 8 | T-801 | Fifty cards render to a single print-ready PDF. |
| `T-803` | Backend | QR resolution endpoint | 3 | T-801,T-104 | An unauthenticated scan reveals nothing beyond validity. |
| `T-804` | Backend | Batch and coach allocation stubs | 4 | T-701 | Steps 11 and 12 of the SOP chain complete without waiting for Phase 2. |
| `T-805` | Backend | Training activation event | 4 | T-804,T-204 | The parent receives the training schedule on activation. |
| `T-806` | Frontend | ID card designer and batch print | 6 | T-802 | Administration prints a term's cards without a developer. |
| `T-807` | Frontend | Parent child-profile view | 4 | T-703,T-105 | A parent sees only their own children, proven by an authorisation test. |

## Sprint 9 — Week 15  (34h)

*Integration, legacy migration, performance and security hardening.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-901` | QA | End-to-end chain test | 6 | T-805 | The full chain passes in CI on every commit. |
| `T-902` | Data | Legacy data migration | 8 | T-704 | Every migrated record traces back to its original register. |
| `T-903` | Data | Duplicate sweep on migrated data | 4 | T-902 | Zero duplicate Persons at go-live. Migrating duplicates would break SOP Sec.78 on day one. |
| `T-904` | Backend | Performance pass | 5 | T-901 | Profile and pipeline screens load under 400 ms p95 on migrated data volumes. |
| `T-905` | QA | Object-level authorisation sweep | 5 | T-807 | A parent cannot reach another child's record by changing an id. |
| `T-906` | QA | Playwright end-to-end suite | 6 | T-901 | Journeys run headless in CI before each deploy. |

## Sprint 10 — Week 16  (34h)

*UAT, fixes, training, production cutover.*

| ID | Stream | Task | h | Depends | Acceptance |
|---|---|---|---|---|---|
| `T-1001` | Delivery | User acceptance testing | 8 | T-906 | Real users complete real admissions on staging without assistance. |
| `T-1002` | Delivery | Defect triage and fixes | 12 | T-1001 | No open blocker or critical defect at go-live. |
| `T-1003` | Delivery | Training and quick-reference guides | 5 | T-1001 | Administration runs the funnel unaided the day after training. |
| `T-1004` | DevOps | Production cutover | 6 | T-1002 | Backup restore drill completed successfully before cutover. |
| `T-1005` | Delivery | Phase 1 gate sign-off and hypercare | 3 | T-1004 | Academy Management sign the Phase 1 gate. |

---

## Phase 0 exit criteria (gate at end of Week 6)

1. A user can be created, assigned a role, and sees only the menu items that role permits - enforced server-side, not merely hidden in the UI.
2. Every create, update and delete on an audited model writes a field-level AuditLog row that no application role can edit or delete.
3. A document uploads to S3 via a presigned URL and moves through Pending, Submitted, Verified, Rejected and Expired.
4. A test SMS, WhatsApp message and email each dispatch through the provider sandbox and record a delivery status.
5. The approval workflow is demonstrable end to end on one object type and is reusable by later modules.

## Phase 1 exit criteria (gate at end of Week 16)

1. The full SOP Section 9 chain runs end to end for one real candidate: Enquiry, Registration, Trial, Assessment, Selection, Admission, Document Verification, Fee Payment, Approval, ID Card, Batch Allocation, Coach Allocation, Training Activation.
2. Attempting to admit a former student surfaces the existing Person record; no duplicate profile can be created (SOP Sections 67 and 78).
3. All 11 student statuses from SOP Section 11 are enforced by a state machine, and only authorised roles can transition them.
4. Enquiry-to-trial and trial-to-admission conversion rates are computable from the data with no manual counting.
5. The ID card prints with a QR code that resolves to the student profile for authorised scanners only.
6. A coach completes a trial assessment on a tablet with no network connection, and it syncs when connectivity returns.
7. A parent logging in sees only their own children's records, proven by an object-level authorisation test.

---

## Boundaries — what Phase 1 deliberately does NOT build

These are Phase 2 and Phase 3. Phase 1 stubs them. If a task starts drifting into one of
these, stop and put it in the backlog.

| Not in Phase 1 | Phase 1 stub | Real phase |
|---|---|---|
| Fee plans, invoicing, receipts, GST, dunning | Manual payment flag + reference, or an approved waiver | Phase 3 |
| Batch composition, capacity, schedules | `BatchAllocation` with a text `batch_ref` | Phase 2 |
| Training calendar and sessions | none — `student.activated` event only | Phase 2 |
| Attendance | none | Phase 2 |
| Coach profiles, assignment, session reports | `CoachAllocation` FK to Staff only | Phase 2 |
| Performance assessment and IDP | none (trial assessment is separate and stays here) | Phase 4 |
| Medical records | `Person.blood_group` only | Phase 5 |
| Full parent portal | Read-only child profile + document upload | Phase 12 |
| Dashboards and MIS | Enquiry conversion query only | Phase 12 |
