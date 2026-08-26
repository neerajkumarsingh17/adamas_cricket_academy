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
| **Enquiry / Trial / Admission** | `enquiry, trial, admission` | VX | VAEPX | VAE | VAE | V | VAE | VA | - | - | - | - | - | V | - | - | V |
| **Student Master Profile** | `students` | VX | VAEPX | VAE | VAE | V | V | V | V | V | V | V | V | V | O | O | V |
| **Documents** | `documents` | VX | VAEPX | VAE | VAEP | V | - | - | - | V | - | V | - | V | O | OA | V |
| Batch / Training / Attendance | `batch, training, attendance` | VX | VAEPX | VAE | VAE | - | VAEP | VAE | VAE | V | V | V | - | V | O | O | V |
| Fees / Payments / Discounts | `fees` | VX | VAEPX | V | VAE | VAEPX | - | - | - | - | - | V | V | - | O | O | V |
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
