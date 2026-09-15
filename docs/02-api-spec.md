# API specification — Phase 0 and Phase 1

Base: `/api/v1/`. All endpoints require authentication unless marked **public**.
`M` column = the module slug checked against `RolePermission`; `V` = the verb required.

Error envelope on every non-2xx:
```json
{ "code": "admission_step_invalid", "message": "Documents are not yet verified.",
  "field_errors": {}, "request_id": "0f3c…" }
```

---

## Auth (`apps/iam`)

| Method | Path | M / V | Notes |
|---|---|---|---|
| POST | `/auth/login` | public | `{login_id, password}` → access + refresh |
| POST | `/auth/otp/request` | public | `{mobile}` → sends OTP. Rate-limited 3/10min |
| POST | `/auth/otp/verify` | public | `{mobile, otp}` → tokens. Parent and student login |
| POST | `/auth/refresh` | public | Rotating refresh; old token invalidated |
| POST | `/auth/logout` | any | Blacklists the refresh token |
| GET | `/auth/me` | any | User, person, roles, and the flattened permission set |

Dev-only (LOCAL-SETUP.md): setting `DEV_STATIC_OTP` in `.env` makes `/auth/otp/request` issue
that fixed code for every mobile number instead of a random one — never set in staging/prod.

## IAM

| Method | Path | M / V | Notes |
|---|---|---|---|
| GET POST | `/iam/users` | `iam` / view, add | |
| GET PATCH | `/iam/users/{id}` | `iam` / view, edit | |
| POST | `/iam/users/{id}/roles` | `iam` / edit | Assign a role with validity dates |
| GET | `/iam/roles` | `iam` / view | |
| GET PUT | `/iam/roles/{id}/permissions` | `iam` / edit | The matrix editor writes here |
| GET | `/iam/permissions` | `iam` / view | The 19 modules × 6 verbs |

## Audit

| Method | Path | M / V | Notes |
|---|---|---|---|
| GET | `/audit/logs` | `audit` / view | Filters: `model_label`, `object_id`, `actor`, `action`, `from`, `to` |
| POST | `/audit/logs/export` | `audit` / export | Async job. **The export is itself audited** |

No POST, PATCH or DELETE on individual log rows. Ever.

## Documents

| Method | Path | M / V | Notes |
|---|---|---|---|
| POST | `/documents/presign` | `documents` / add | `{document_type, owner_type, owner_id, filename, mime}` → S3 presigned PUT |
| POST | `/documents/confirm` | `documents` / add | Confirms the upload, sets `submitted` |
| GET | `/documents` | `documents` / view | Scoped: a parent sees only their children's. `?status=`, `?document_type=`, `?owner_object_id=` narrow the list — the parent portal's child detail page uses the last one so a multi-child parent doesn't see every child's documents mixed together |
| PATCH | `/documents/{id}/verify` | `documents` / approve | |
| PATCH | `/documents/{id}/reject` | `documents` / approve | `rejection_reason` required |
| GET | `/documents/{id}/download` | `documents` / view | Presigned GET, 5-minute expiry |

## Notifications

| Method | Path | M / V | Notes |
|---|---|---|---|
| GET POST PATCH | `/notifications/templates` | `communication` / view, add, edit | |
| POST | `/notifications/send` | `communication` / add | `{template_code, recipients[], context}`. Async |
| GET | `/notifications/logs` | `communication` / view | Delivery status per recipient |

## Approvals

| Method | Path | M / V | Notes |
|---|---|---|---|
| GET | `/approvals` | any | Returns only requests this user may decide |
| POST | `/approvals/{id}/approve` | module of the subject / approve | |
| POST | `/approvals/{id}/reject` | module of the subject / approve | `reason` required |

## Master data

`GET POST PATCH /master/{programmes|age-categories|venues|seasons|enquiry-sources|assessment-criteria|document-types}`
— `master` / view, add, edit.

---

## Enquiry

| Method | Path | M / V | Notes |
|---|---|---|---|
| POST | `/public/enquiries` | **public** | Rate-limited, captcha. Website widget posts here |
| GET POST | `/enquiries` | `enquiry` / view, add | Filters: `status`, `source`, `owner`, `from`, `to`, `search` |
| GET PATCH | `/enquiries/{id}` | `enquiry` / view, edit | |
| POST | `/enquiries/{id}/follow-ups` | `enquiry` / add | |
| POST | `/enquiries/{id}/convert-to-trial` | `enquiry` / edit | Body: `{slot_id}`. Carries every captured field forward |
| GET | `/enquiries/analytics/conversion` | `enquiry` / view | Enquiry→trial→admission rates by source and period |
| GET | `/persons/search` | `students` / view | `?name=&dob=&mobile=` — the duplicate check. Called by every intake form |

## Trials

| Method | Path | M / V | Notes |
|---|---|---|---|
| GET POST | `/trials/slots` | `trial` / view, add | |
| POST | `/trials/slots/{id}/book` | `trial` / add | `select_for_update`; 409 when full |
| GET | `/trials/registrations` | `trial` / view | Filters: `slot`, `date`, `outcome` |
| PATCH | `/trials/registrations/{id}/attendance` | `trial` / edit | |
| POST | `/trials/registrations/{id}/assess` | `trial` / add | Full scored assessment in one payload. 409 if locked |
| POST | `/trials/registrations/{id}/result` | `trial` / approve | Head Coach. Locks the assessment |
| POST | `/trials/results/bulk-notify` | `trial` / approve | One action notifies a whole trial day |
| GET | `/trials/slots/{id}/sheet.pdf` | `trial` / print | Printable ground fallback |

**Offline:** `POST /trials/registrations/{id}/assess` accepts an `Idempotency-Key` header.
The frontend queues assessments in IndexedDB and replays them with a stable key, so a retry
after reconnection cannot double-write.

## Admissions

| Method | Path | M / V | Notes |
|---|---|---|---|
| GET POST | `/admissions` | `admission` / view, add | POST requires a selected trial or an approved waiver |
| GET PATCH | `/admissions/{id}` | `admission` / view, edit | |
| GET | `/admissions/{id}/checklist` | `admission` / view | |
| POST | `/admissions/{id}/advance` | `admission` / edit | `{to_step, reason?}`. Runs the guard. 409 on an invalid transition |
| POST | `/admissions/{id}/record-payment` | `admission` / edit **or** the `accounts` role¹ | Phase 1 stub: `{reference, payment_method, amount}`, `{waiver_reason}`, or `{mark_unpaid: true}` to correct a mistaken entry. Collected via UPI/card/cash. Auto-advances `fee_pending → fee_cleared` itself (or the reverse, on `mark_unpaid`) — no separate `/advance` call needed |
| POST | `/admissions/{id}/approve` | `admission` / approve | Creates `Student`, issues `student_code` |
| POST | `/admissions/{id}/reject` | `admission` / approve | `reason` required |
| POST | `/admissions/direct` | `admission` / approve | Trial waiver path. `reason` required, raises an approval |

¹ docs/04-state-machines.md section 1 names Accounts as permitted on `fee_pending → fee_cleared`
alongside Administration, but docs/03-rbac.md's matrix gives Accounts only `view` on this module —
one of the documented "rules that override the matrix" cases. Enforced in
`AdmissionRecordPaymentView` directly (a plain `APIView`, not the `ModuleScopedViewSet` action
every other admission endpoint uses), not via a `RolePermission` row.

## Students

| Method | Path | M / V | Notes |
|---|---|---|---|
| GET | `/students` | `students` / view | Scope `own` filters to a parent's children |
| GET | `/students/{id}` | `students` / view | Composite profile: Personal, Parent, Cricket, Academy |
| PATCH | `/students/{id}` | `students` / edit | Field-level permission — a coach may edit cricket fields only |
| POST | `/students/{id}/status` | `students` / edit | `{to_status, reason}`. Some transitions raise an approval |
| GET | `/students/{id}/status-history` | `students` / view | |
| POST | `/students/re-admission` | `students` / add | `{person_id, programme}`. **Refuses** to create a second Person |
| GET | `/students/export` | `students` / export | Async. Audited with the filter and row count |
| GET | `/students/{id}/guardians` | `students` / edit | Management view of the Parent tab — a parent/student already sees their own via the composite profile |
| POST | `/students/{id}/guardians` | `students` / edit | `{person_id}` **or** `{first_name, last_name, date_of_birth, gender, mobile, email}`, plus `{relationship, is_primary, is_emergency_contact, grant_portal_access}`. Resolves/creates the `Person` (never bypasses `resolve_person()`), gets-or-creates the `Guardian`, and — if `grant_portal_access` — provisions their OTP login with role `parent` |
| DELETE | `/students/{id}/guardians/{guardian_link_id}` | `students` / edit | Removes the `StudentGuardian` mapping only — the `Guardian`/login are untouched (a sibling may still need them) |
| POST | `/students/{id}/login-access` | `students` / edit | `{mobile?}`. Provisions the student's own OTP login (role `student`). Not automatic on approval — see docs/04-state-machines.md's note on the guardian-mobile collision this avoids |

## ID cards

| Method | Path | M / V | Notes |
|---|---|---|---|
| POST | `/students/{id}/id-card` | `idcard` / add | Issues; supersedes any active card |
| GET | `/id-cards/{id}/render.pdf` | `idcard` / print | |
| POST | `/id-cards/batch-print` | `idcard` / print | `{student_ids[]}` → one PDF |
| GET | `/id-cards/resolve/{token}` | `idcard` / view | QR scan. Unauthenticated returns validity only |

## Parent portal

| Method | Path | M / V | Notes |
|---|---|---|---|
| GET | `/parents/me/children` | `students` / view (scope own) | |
| GET | `/parents/me/children/{id}` | `students` / view (scope own) | Read-only profile |
| POST | `/parents/me/documents` | `documents` / add (scope own) | Upload for their own child |

**Every one of these has an object-level authorisation test.** Changing the id in the URL to
another parent's child must return 404 (not 403 — do not confirm the record exists).
