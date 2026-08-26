# Phase 1 screen prompts for Claude Code

Paste one at a time. Build a screen **after** its API exists, so the generated types are real.

Order: design system → app shell → auth → then each module's backend prompt (in `PROMPTS.md`)
followed immediately by its screen prompt below.

---

## 0. The design system — paste this once, before any screen

```
Set up the design system in frontend/src/styles/tokens.css and configure
Tailwind to use it. Every screen we build after this reads from these tokens.
No component may hardcode a colour.

:root{
  --ground:#F6F4F1; --surface:#FCFCFB; --surface-2:#F0EDE8; --surface-3:#E8E3DD;
  --ink:#201C1A; --ink-2:#574F4B; --ink-3:#8A807A;
  --line:#E2DCD6; --line-2:#D2C9C1;
  --accent:#A6332A; --accent-ink:#8C2A22; --accent-soft:#F6E5E2;
  --good:#008B7A; --good-soft:#DDF0ED;
  --on-accent:#FFFFFF;
}
Dark mode, applied under BOTH @media (prefers-color-scheme:dark) guarded as
:root:not([data-theme="light"]) AND :root[data-theme="dark"]:
  --ground:#161311; --surface:#211E1C; --surface-2:#2A2523; --surface-3:#332D2A;
  --ink:#F2EDE8; --ink-2:#B3A9A2; --ink-3:#857A73;
  --line:#35302C; --line-2:#443D39;
  --accent:#DD5A49; --accent-ink:#E9705F; --accent-soft:#3A211D;
  --good:#1FA895; --good-soft:#152E2A;
  --on-accent:#1B0F0D;

Fonts from Google Fonts: Chivo (600/700/800) for headings, Source Sans 3
(400/500/600/700) for UI, IBM Plex Mono (400/500/600) for IDs, dates and
stat numerals. Every ID like ENQ/2627/00142 uses the mono face with
font-variant-numeric: tabular-nums.

Colour rules, enforce these in review:
- --accent means "needs action" and nothing else: urgent stat tiles, queue
  stripes, the current step in a flow, primary buttons.
- --good means complete, and carries every chart fill.
- Waiting and neutral states use --ink-3 on --surface-2. There is no third
  status hue — attention is encoded by form (a 3px left stripe, weight) as
  well as colour.

Build these primitives in src/components/: Button (primary/secondary/ghost,
sm), Field (label + input + hint + error), Pill (done/action/waiting),
Card (header with title + right-aligned subtitle, body), StatTile
(label, value, meta, urgent flag), Table, EmptyState, ErrorState, Skeleton.

Check: a Storybook or a /kitchen-sink route renders every primitive in both
themes, and toggling data-theme="dark" on <html> changes all of them with no
component-level overrides.
```

---

## 1. App shell

```
Build the app shell in src/components/AppShell.tsx.

Left sidebar 224px: brand mark (a filled circle in --accent with a
ball-seam detail), nav items rendered FROM the user's permission set — never
a hardcoded role check. Active item gets --accent-soft background and
--accent text. A count badge sits right-aligned in the item when the nav
entry has pending work.

Top bar: sticky, page-scoped, user avatar with initials + name + role name
on the right.

Main: max-width 1240px, 22px padding, page header (h1 + one-line
description), then content.

Responsive: under 780px the sidebar becomes a horizontal scrolling strip
above the content.

Check: a user with only the enquiry permission sees one nav item, and
navigating directly to /admissions by URL is refused by the route guard AND
by the API.
```

---

## 2. Auth screens

```
Build the auth screens in src/features/auth/.

LOGIN — split layout. Left panel (hidden under 860px): brand, a headline,
a short lede, and a numbered list of the onboarding chain. Right panel:
a two-tab form.
  Staff tab:  login_id (mobile or email) + password
  Parent tab: registered mobile -> "Send code" -> 6-digit OTP entry
Show the OTP expiry (10 minutes) and a resend that is disabled for 30s.
On success, redirect by permission: land the user on the first nav item
their role can see, not a fixed /dashboard.

REGISTER — this is the PUBLIC enquiry form, not an account sign-up. Say so
on the page. Fields per docs/01-data-model.md Enquiry: player name, DOB,
playing role, guardian name, mobile, source, residential requirement.
On submit, POST /public/enquiries and show a success state with the
generated ENQ/2627/xxxxx in the mono face, plus a plain-language "what
happens next".

Copy that must appear, because it prevents support calls:
- "No account is created yet — that happens if your child is admitted."
- "Already registered before? Use the same mobile and date of birth. The
  system will find the existing record rather than creating a second one."

Check: an invalid OTP shows a field-level error and does not clear the
mobile; the 4th OTP request in 10 minutes is throttled with a clear message;
the register success state shows a real enquiry number from the API.
```

---

## 3. Role dashboards

Four dashboards, one per role. Each answers exactly one question — build them one at a time.

```
Build the Administration dashboard at src/features/dashboard/AdminDashboard.tsx.

The question it answers: what is stuck in my queue?

Four stat tiles: New enquiries this week · Follow-ups overdue (urgent) ·
Trials booked this weekend · Documents to verify (urgent).

Main column:
  "Your queue" card — a list of only the items this user can move. Each row:
  name + ID in mono, one line of context, an action button on the right, and
  a 3px --accent left stripe when it needs action. Overdue follow-ups,
  admissions stuck on documents, admissions stuck on fees, documents
  awaiting verification.
  "Recent enquiries" table — last 10, with a status Pill per row.

Side column:
  "This season's funnel" — horizontal bars, single series, --good fill,
  direct value labels, no legend. Below it a one-sentence insight callout
  naming the biggest drop-off.
  "Trial slots" — this weekend, with booked/capacity and the coach.

Every number comes from an API call. No hardcoded figures.

Check: with an empty database every card shows a real empty state that says
what to do next, not a blank box or a zero.
```

```
Build the Head Coach dashboard.
Question: what needs my decision?

Tiles: Assessments outstanding (urgent) · Results to declare (urgent) ·
Selected but not yet admitted · Waiver requests.
Main: "Awaiting your decision" queue — trial days where all assessments are
in and results can be declared (primary button), days still incomplete
(secondary), and trial-waiver requests. Plus assessment progress per coach
as horizontal bars with a callout naming whoever is behind.
Side: candidate list for the next slot, and selected candidates awaiting
admission.

Check: "Declare results" is disabled with an explanatory tooltip while any
candidate in that slot is unassessed.
```

```
Build the Coach dashboard. Mobile-first — a coach uses this on a tablet at
a ground, standing up, in sunlight. Design at 768px and 360px first.

Question: who do I assess next?

Tiles: To assess today (urgent) · Assessed this weekend · Waiting to sync
(urgent) · Next slot.
Main: today's candidate list. Each row is a large touch target with the
candidate name, trial ID, category and role, and a single button — Assess,
Continue, or a Done pill. Nothing else competes for the tap.
Side: the offline queue, showing what is saved on the device and not yet
uploaded, with the time it was scored. Below it, the nine assessment
criteria pulled from master data.

Check: every interactive target is at least 44px tall, the list is usable
one-handed at 360px, and the offline queue renders from IndexedDB with no
network.
```

```
Build the Academy Head dashboard.
Question: what is waiting on my approval, and is the funnel healthy?

Tiles: Waiting on your approval (urgent) · New admissions this month ·
Active students · Enquiry-to-student conversion.
Main: the approval queue — each row has the subject, who raised it, how long
it has waited, and Reject / Approve buttons. Anything over 24 hours gets an
"N days waiting" action pill. Below it the funnel chart with an insight
callout.
Side: enquiries by source (horizontal bars with percentages) and the last
five audit trail entries.

Check: approving from this screen posts to the approval engine, the row
disappears optimistically, and a failure rolls it back with an error toast.
```

---

## 4. Enquiry screens — after the enquiry API

```
Build the enquiry screens in src/features/enquiry/.

CAPTURE FORM — staff-side. As the user types name and DOB, debounce 400ms
and call GET /persons/search, then show any duplicate candidates inline
above the form with "This may be <name>, enquired <date>. Use existing
record?" Do not let the user past it silently — SOP §78.

PIPELINE BOARD — Kanban by enquiry status, drag to advance. Each card:
name, enquiry number in mono, source, days since last contact. Cards with an
overdue follow-up get the --accent left stripe. Filters in one row above the
board: status, source, owner, date range.

FOLLOW-UP PANEL — a slide-over on a card. Call log, mode, notes, and a
mandatory next-action date. The save button stays disabled until a next
action is set.

Check: a duplicate is surfaced before submit, not after; dragging a card
persists and rolls back visually on API failure; an enquiry cannot be saved
from the follow-up panel without a next action date.
```

```
Build the public enquiry widget as a separate entry point that bundles to a
single JS file the academy can embed on their WordPress site with one script
tag. It must not import the app shell, the auth code, or anything requiring
a session — check the bundle size and tell me what it is.

Check: the built file drops into a plain HTML page and posts successfully to
/public/enquiries with no login.
```

---

## 5. Trial screens — after the trial API

```
Build the trial screens in src/features/trial/.

TRIAL CALENDAR — month and day views. Each slot shows date, time, venue,
age category, coach, and booked/capacity with a fill indicator. Booking
dialog picks a candidate from converted enquiries. A full slot is visibly
full and cannot be selected.

RESULT DECLARATION — one screen per trial day. Every candidate with their
score, a result dropdown (the five SOP outcomes), and a bulk-apply control.
Shortlisted and Waitlisted force a review date. Preview the notification
each parent will receive before sending, then declare and notify in one
action.

Check: the declare button is disabled while any candidate is unassessed;
selecting Waitlisted without a review date blocks submit with a field error;
the notification preview shows the real rendered template text.
```

```
Build the coach assessment screen — this is the most important screen in
Phase 1 and the one most likely to fail in the field.

Tablet-first, 768px landscape primary. One candidate per screen. The nine
criteria from master data as large tap-to-score controls (not dropdowns, not
tiny radio buttons). Show the candidate's previous score beside each
criterion when one exists. A free-text remarks field. Previous / Next
candidate navigation that saves as it moves.

OFFLINE, and this is not optional:
- Register a service worker so the screen loads with no network.
- Queue submissions in IndexedDB with a stable idempotency key per
  assessment, generated once when the form opens.
- Replay the queue on reconnect, with visible per-item status.
- Show a persistent, honest connection indicator: "3 saved on this device,
  will upload when you're back online."
- Never block scoring on network. Never show a spinner that cannot resolve.

Check: put the browser in offline mode, score three candidates, close the
tab, reopen it, go online — all three upload exactly once and the server has
no duplicates. Test this specific sequence before calling it done.
```

---

## 6. Admission screens — after the admission API

```
Build the admission screens in src/features/admission/.

ADMISSION WIZARD — multi-step matching the seven states in
docs/04-state-machines.md. A step rail down the left showing done, current
and locked steps. Every field already captured at enquiry or trial is
pre-filled and shown as read-only with a "from enquiry" marker — SOP §79.
Save as draft on every step change so nothing is lost.

DOCUMENT CHECKLIST — inside the wizard. Each required document with its
status pill, upload control (presigned S3, direct from the browser), and for
rejected ones the reason and a re-upload. Mandatory items are visually
distinct from optional.

VERIFICATION QUEUE — administration-side. Document preview beside the
metadata, Verify and Reject buttons, and rejection requires a reason from a
preset list plus optional free text. The parent is notified on reject.

APPROVAL SCREEN — Academy Head. The entire application on one page:
applicant, trial result, every document with its status, fee status, and who
raised it. Approve and Reject at the bottom. Reject requires a reason.

Check: advancing to fee payment with an unverified mandatory document
returns a 409 and the UI shows which document is blocking; the approval
screen requires no other tab to make a decision.
```

---

## 7. Student screens — after the student API

```
Build the student screens in src/features/student/.

STUDENT MASTER PROFILE — tabbed: Personal, Parent, Cricket, Academy. Edit
is per-field and governed by permission: a coach sees the Cricket tab
editable and the Academy tab read-only. Header carries photo, name, student
code in mono, and the current status pill.

STATUS CHANGE DIALOG — a dropdown of only the transitions valid from the
current status (read from the API, never a hardcoded list), a mandatory
reason, and a warning when the transition will raise an approval request.

RE-ADMISSION — search by name, DOB or guardian mobile. Results show any
prior enrolment with its history. Selecting one creates a NEW student record
against the SAME person. There must be no path on this screen that creates a
second person.

Check: a coach cannot edit a fee field even by tampering with the request;
the status dropdown for a Withdrawn student does not offer Active; the
re-admission flow preserves and displays the prior enrolment.
```

```
Build the ID card screens.

DESIGNER — live preview of the card with the academy logo, photo, name,
student code, category, residential status, validity and QR. Photo crop
control.
BATCH PRINT — select students by batch or filter, preview the sheet, and
generate one print-ready PDF from the server.

Check: 50 cards render to a single PDF; issuing a replacement invalidates
the previous card and both appear in the issuance history.
```

```
Build the parent view in src/features/parent/.

A read-only profile of their own child: photo, name, student code, status,
programme, and the document checklist with upload for anything outstanding.
This is the first slice of the parent portal — do not build fees,
attendance or performance here, they do not exist until Phases 2 and 3.

Check: an object-level authorisation test proves that changing the child ID
in the URL returns 404 — not 403, because 403 confirms the record exists.
```

---

## Screen inventory

| # | Screen | Sprint | Notes |
|---|---|---|---|
| 1 | Login (staff + parent OTP) | 1 | Redirect by permission, not to a fixed route |
| 2 | Register / public enquiry | 4 | Creates an enquiry, not an account |
| 3 | App shell + nav | 1 | Nav rendered from the permission set |
| 4 | User & role admin | 1 | |
| 5 | Permission matrix editor | 1 | Writes the RBAC rows |
| 6 | Audit log viewer | 2 | Filters + export (separate permission) |
| 7 | Document library + verification queue | 2 | |
| 8 | Notification template manager | 2 | |
| 9 | Master data screens | 2 | Django admin is acceptable here |
| 10 | Administration dashboard | 4 | |
| 11 | Enquiry capture form | 4 | Inline duplicate detection |
| 12 | Enquiry pipeline board | 4 | |
| 13 | Public enquiry widget | 4 | Separate bundle, no auth |
| 14 | Head Coach dashboard | 5 | |
| 15 | Coach dashboard | 5 | Mobile-first |
| 16 | Trial calendar + booking | 5 | |
| 17 | **Coach assessment (tablet, offline)** | 5 | The riskiest screen in Phase 1 |
| 18 | Result declaration + bulk notify | 5 | |
| 19 | Admission wizard | 6 | |
| 20 | Document verification queue | 6 | |
| 21 | Admission approval | 6 | |
| 22 | Academy Head dashboard | 6 | |
| 23 | Student Master Profile | 7 | |
| 24 | Status change dialog | 7 | |
| 25 | Re-admission | 7 | Cannot create a second person |
| 26 | ID card designer + batch print | 8 | |
| 27 | Parent child profile | 8 | 404 not 403 on someone else's child |

## Rules for every screen

Say this once and hold Claude Code to it:

```
For every screen from now on:
- Three states, always: loading skeleton, empty with a next action, error
  with a retry. Not just the happy path.
- Permission-gate the UI with a <Can module verb> component, but never rely
  on it — the server check is the real one.
- Types come from npm run generate:api. Never hand-write an API type.
- Mobile-first. Test at 360px before saying it's done.
- Money is never a float. Dates render DD-MM-YYYY, IST.
- IDs, dates and stat numbers use the mono face with tabular-nums.
- Visible keyboard focus on every interactive element.
```
