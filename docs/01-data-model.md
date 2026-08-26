# Data model — Phase 0 and Phase 1

Read this before writing any model. Field types are Django field types. `FK` means
`ForeignKey`, `O2O` means `OneToOneField`.

Nothing here may be changed without updating this file in the same commit.

---

## 1. The identity spine (`apps/people`, `apps/iam`)

This is the most consequential part of the schema and the part most expensive to change
after go-live. Build it first, get it reviewed, then build everything else on top.

### Person

The human being. Created once, never duplicated.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID pk | |
| `first_name`, `middle_name`, `last_name` | CharField | `middle_name` blank-able |
| `date_of_birth` | DateField | required — part of the dedupe key |
| `gender` | CharField(choices) | M / F / O |
| `photograph` | FK Document, null | |
| `mobile` | CharField(15), index | E.164 normalised |
| `email` | EmailField, blank | |
| `address_line1`, `line2`, `city`, `state`, `pincode` | CharField | |
| `blood_group` | CharField(choices), blank | |
| `dedupe_key` | CharField(64), db_index | see below |
| `created_at`, `updated_at` | DateTimeField | |

**`dedupe_key`** = `sha256(slugify(first+last) + "|" + dob.isoformat() + "|" + primary_guardian_mobile)`.
Computed on save. **Not unique** at the database level — a match is a signal for the
resolution service to act on, not a hard constraint, because two real siblings can share a
guardian mobile and a birthday is not impossible.

`people.services.resolve_person(data) -> PersonMatch`

Returns exact matches on `dedupe_key`, plus fuzzy candidates scoring on
(normalised name similarity ≥ 0.85) AND (DOB exact OR guardian mobile exact).
Every entry point calls this. See rule 1 in `CLAUDE.md`.

### Guardian

| Field | Type | Notes |
|---|---|---|
| `id` | UUID pk | |
| `person` | O2O Person | a guardian is a Person |
| `occupation` | CharField, blank | |
| `portal_access` | BooleanField | can log into the parent portal |

### StudentGuardian

| Field | Type | Notes |
|---|---|---|
| `student` | FK Student | |
| `guardian` | FK Guardian | |
| `relationship` | CharField(choices) | Father / Mother / Guardian / Other |
| `is_primary` | BooleanField | exactly one per student — enforce in `clean()` |
| `is_emergency_contact` | BooleanField | |

Unique together: `(student, guardian)`.

### Staff

| Field | Type | Notes |
|---|---|---|
| `person` | O2O Person | |
| `employee_code` | CharField, unique | |
| `staff_type` | CharField(choices) | Coach / Medical / Physio / Hostel / Transport / Admin / AthleteMgmt |
| `joining_date`, `exit_date` | DateField | |
| `is_active` | BooleanField | |

### User (`apps/iam`)

`AbstractBaseUser` + `PermissionsMixin`. `USERNAME_FIELD = "login_id"` (mobile or email).

| Field | Type | Notes |
|---|---|---|
| `login_id` | CharField, unique | mobile number or email |
| `person` | FK Person, null | null only for the system/IT admin account |
| `is_active`, `is_staff` | BooleanField | |
| `last_login_at` | DateTimeField | |
| `mfa_enabled` | BooleanField | |

`User.has_perm_for(module: str, verb: str) -> bool` — the only permission check in the
codebase. Cached per request.

---

## 2. Access control (`apps/iam`)

### Role
`code` (slug, unique), `name`, `description`, `is_system` (system roles cannot be deleted).

Seeded with the 16 SOP §5 roles — see `docs/03-rbac.md`.

### Permission
`module` (slug — matches the module groups in `docs/03-rbac.md`), `verb` (choices:
`view`, `add`, `edit`, `approve`, `export`, `print`). Unique together `(module, verb)`.

### RolePermission
`role` FK, `permission` FK, `scope` (choices: `all`, `own`). Unique together `(role, permission)`.

`scope="own"` means the queryset is filtered to records belonging to that user — used for
Student and Parent roles.

### UserRole
`user` FK, `role` FK, `valid_from`, `valid_to` (nullable). A user may hold several roles;
permissions are the union.

---

## 3. Audit (`apps/audit`)

### AuditLog

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField pk | |
| `actor` | FK User, null on_delete=PROTECT | null for system actions |
| `action` | CharField(choices) | create / update / delete / read / export / login / approve |
| `model_label` | CharField | `app_label.ModelName` |
| `object_id` | CharField | stringified pk |
| `changes` | JSONField | `{field: {"from": x, "to": y}}` |
| `ip_address` | GenericIPAddressField, null | |
| `user_agent` | TextField, blank | |
| `request_id` | CharField(36), index | |
| `created_at` | DateTimeField, index | |

`AuditedModel` mixin: `pre_save` captures the diff, `post_save` writes the row.

**Database grants:** the application role holds `INSERT` and `SELECT` on `audit_auditlog`
and nothing else. Add this as a data migration with `RunSQL`. Retention: 7 years.

Reads are audited **selectively** — only medical records and contracts (Phase 5 and 9).
Auditing every read would swamp the table. Exports are always audited, with the filter
applied and the row count.

---

## 4. Shared core (`apps/core`)

### Document / DocumentType / DocumentVersion

`DocumentType`: `code`, `name`, `is_mandatory_default`, `has_expiry`, `applies_to`
(person / student / staff / admission).

`Document`: `document_type` FK, `owner_content_type` + `owner_object_id` (generic FK),
`s3_key`, `original_filename`, `mime_type`, `size_bytes`, `status`
(`pending` / `submitted` / `verified` / `rejected` / `expired`), `verified_by` FK User null,
`verified_at`, `rejection_reason`, `expires_on`.

Upload flow: client asks `POST /api/v1/documents/presign` → uploads directly to S3 →
`POST /api/v1/documents/confirm`. The file never touches the API server.

### ApprovalRequest / ApprovalRule

`ApprovalRule`: `module`, `action`, `required_role` FK Role, `threshold` (JSON, optional).

`ApprovalRequest`: generic FK to the subject, `rule` FK, `requested_by`, `status`
(`pending` / `approved` / `rejected`), `decided_by`, `decided_at`, `reason`.

Reused by: admission approval, trial waiver, fee waiver, status change (Phase 1); discounts
and scholarships (Phase 3); disciplinary action (Phase 11); contracts (Phase 9).

### NotificationTemplate / NotificationLog

`NotificationTemplate`: `code`, `channel` (`sms` / `whatsapp` / `email` / `push` / `inapp`),
`subject`, `body` (with `{{placeholders}}`), `provider_template_id` (WhatsApp needs Meta's
pre-approved id), `is_active`.

`NotificationLog`: `template` FK, `channel`, `recipient`, `rendered_body`, `status`
(`queued` / `sent` / `delivered` / `failed`), `provider_message_id`, `error`, `sent_at`.

Dispatch is always async via Celery. `notifications.send(code, recipient, context)` is the
only public entry point.

### Master data

`Programme`, `AgeCategory` (`min_age`, `max_age`, `as_on_date_rule`), `Venue`, `Season`,
`EnquirySource`, `TrainingType`, `FeeHead`. All editable through Django admin by
Administration. Never hardcode these.

---

## 5. Admissions (`apps/admissions`)

### Enquiry

| Field | Type | Notes |
|---|---|---|
| `enquiry_no` | CharField, unique | generated — see numbering below |
| `person` | FK Person, null | set once resolved; null while it is a raw web lead |
| `student_name`, `date_of_birth`, `gender` | | captured before a Person is resolved |
| `guardian_name`, `guardian_mobile`, `guardian_email` | | |
| `address`, `school`, `class_grade` | | |
| `cricket_experience` | TextField | |
| `playing_role` | CharField(choices) | Batsman / Bowler / All-rounder / Wicketkeeper |
| `batting_style`, `bowling_style` | CharField(choices) | |
| `current_club` | CharField, blank | |
| `residential_required` | BooleanField | |
| `source` | FK EnquirySource | website / social / walk-in / school / club / referral / tournament / trial / advertisement |
| `referred_by` | CharField, blank | |
| `status` | CharField(choices) | new / contacted / trial_scheduled / converted / not_interested / lost |
| `remarks` | TextField, blank | |
| `owner` | FK User, null | who is chasing it |

### EnquiryFollowUp
`enquiry` FK, `contacted_on`, `mode` (call / whatsapp / email / visit), `notes`,
`next_action_on` (DateField), `created_by`.

### Trial / TrialSlot / TrialRegistration

`TrialSlot`: `date`, `venue` FK, `reporting_time`, `age_category` FK, `capacity`,
`booked_count` (denormalised, updated in a transaction).

`TrialRegistration`: `trial_id` (CharField unique, generated), `enquiry` FK,
`person` FK null, `slot` FK, `trial_fee` Decimal, `payment_status`
(`not_applicable` / `pending` / `paid` / `waived`), `payment_reference`, `attended` Boolean.

Booking must use `select_for_update` on the slot. Overbooking is a defect.

### TrialAssessment / TrialAssessmentScore

`TrialAssessment`: `registration` O2O, `assessed_by` FK Staff, `assessed_at`,
`overall_remarks`, `is_locked` (True once a result is declared).

`TrialAssessmentScore`: `assessment` FK, `criterion` FK `AssessmentCriterion`, `score` Decimal.

`AssessmentCriterion` (master data): `code`, `name`, `group`
(batting / bowling / fielding / wicketkeeping / fitness / game_awareness / discipline /
attitude / potential), `scale_min`, `scale_max`, `weight`, `is_active`.

The nine SOP §8 dimensions are **seed data**, not model fields. The Head Coach changes them
without a release.

### TrialResult
`registration` O2O, `outcome` (`selected` / `shortlisted` / `waitlisted` / `not_selected` /
`re_trial`), `declared_by` FK, `declared_at`, `review_on` (DateField, for waitlisted),
`notes`.

Declaring a result sets `TrialAssessment.is_locked = True`. Any later edit requires an
approval and writes an audit row.

### Admission / AdmissionChecklistItem

`Admission`: `application_no` unique, `person` FK, `enquiry` FK null, `trial_registration`
FK null, `programme` FK, `residential` Boolean, `step` (see the state machine),
`trial_waiver_reason` (blank; set only on direct admission), `trial_waiver_approval` FK
ApprovalRequest null, `fee_payment_reference`, `fee_payment_status`, `approved_by`,
`approved_at`, `rejected_reason`.

`AdmissionChecklistItem`: `admission` FK, `document_type` FK, `is_mandatory`,
`document` FK Document null, `status` (mirrors the document status).

### Student

| Field | Type | Notes |
|---|---|---|
| `student_code` | CharField, unique | generated |
| `person` | O2O Person | **reused** on re-admission |
| `admission` | FK Admission | the admission that created this enrolment |
| `admission_date` | DateField | |
| `programme` | FK Programme | |
| `residential` | BooleanField | |
| `status` | CharField(choices) | 11 values — see the state machine |
| `withdrawn_on`, `completed_on` | DateField null | |

`StudentStatusHistory`: `student` FK, `from_status`, `to_status`, `reason` (required),
`changed_by` FK User, `approval` FK ApprovalRequest null, `changed_at`.

### IDCard
`student` FK, `card_no` unique, `issued_on`, `valid_until`, `qr_payload` (signed token,
not the raw student id), `status` (`active` / `replaced` / `expired` / `lost`),
`replaces` FK self null, `issued_by` FK User.

### Phase 2 handoff stubs

`BatchAllocation` (`student`, `batch_ref` CharField, `allocated_on`, `allocated_by`) and
`CoachAllocation` (`student`, `coach` FK Staff, `allocated_on`).

These are **deliberately thin**. Phase 2 replaces `batch_ref` with a real `Batch` FK.
Do not build batch management here.

---

## 6. Numbering

All sequential numbers come from `core.services.numbering.next_number(series, **ctx)`,
backed by a PostgreSQL sequence per series. Never `count() + 1`.

| Series | Format | Example |
|---|---|---|
| Enquiry | `ENQ/{YY}{YY+1}/{seq:05d}` | `ENQ/2627/00142` |
| Trial | `TRL/{YY}{YY+1}/{seq:05d}` | `TRL/2627/00087` |
| Admission | `ADM/{YY}{YY+1}/{seq:05d}` | `ADM/2627/00061` |
| Student | `ACA/{YY}{YY+1}/{seq:04d}` | `ACA/2627/0043` |
| ID Card | `{student_code}-{issue_seq}` | `ACA/2627/0043-1` |

**The exact format is decision D-01 and must be confirmed by the Academy Head in Week 1.**
The table above is the proposal, not the decision. Once ID cards are printed, changing it
means reprinting every card.
