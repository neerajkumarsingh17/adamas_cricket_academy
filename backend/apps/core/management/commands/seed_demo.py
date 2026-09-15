"""Demo dataset for the stakeholder prototype (docs/05-build-sequence.md).

Idempotent: every business-key number this command mints uses a "DEMO"
series segment (`ENQ/DEMO/00001`, not `ENQ/2627/00001`) so it can never
collide with a real number minted later by core.services.numbering, and so
a second plain run can detect "already seeded" by checking for exactly
that marker and exit without writing anything. `--flush` deletes every row
carrying that marker (and only those rows) and rebuilds from scratch.

Known gap, not guessed at: the "5 recent audit entries across different
actors" line in the brief can't be satisfied — apps.audit has no AuditLog
model yet (models.py is empty; it's Phase 0 work this prompt didn't cover).
Flagged in the command's own output rather than silently skipped.
"""

import datetime
import itertools
import random

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.admissions.admission.models import Admission, AdmissionChecklistItem, AdmissionStep
from apps.admissions.document.models import Document, DocumentStatus
from apps.admissions.enquiry.models import (
    Enquiry,
    EnquiryFollowUp,
    EnquiryStatus,
    FollowUpMode,
    PlayingRole,
)
from apps.admissions.idcard.models import IDCard
from apps.admissions.student.models import Student, StudentStatus, StudentStatusHistory
from apps.admissions.trial.models import (
    PaymentStatus,
    TrialAssessment,
    TrialAssessmentScore,
    TrialOutcome,
    TrialRegistration,
    TrialResult,
    TrialSlot,
)
from apps.core.models import (
    AgeCategory,
    ApprovalRequest,
    ApprovalRule,
    AssessmentCriterion,
    DocumentType,
    EnquirySource,
    Programme,
    Venue,
)
from apps.core.services.dates import upcoming_weekend
from apps.iam.models import Role, User, UserRole
from apps.people.models import Gender, Person, Staff, StaffType
from apps.people.services import resolve_person

DEMO_SERIES = "DEMO"
DEMO_MOBILE_PREFIX = "70000"

FIRST_NAMES_MALE = [
    "Arjun",
    "Rohan",
    "Aditya",
    "Sourav",
    "Debjit",
    "Abhishek",
    "Rajat",
    "Suman",
    "Anik",
    "Rahul",
    "Amit",
    "Vikram",
    "Ankit",
    "Soham",
    "Ritwik",
    "Pritam",
    "Sayan",
    "Arnab",
    "Shubham",
    "Kunal",
    "Ayan",
    "Dipankar",
    "Joydeep",
    "Arindam",
    "Sandip",
    "Biswajit",
    "Tanmoy",
    "Subhankar",
    "Rudra",
    "Ishaan",
]
FIRST_NAMES_FEMALE = [
    "Ananya",
    "Priyanka",
    "Ishita",
    "Sneha",
    "Riya",
    "Sohini",
    "Debolina",
    "Sreya",
    "Trisha",
    "Ankita",
    "Poulami",
    "Ritika",
    "Diya",
    "Pooja",
    "Nabanita",
    "Mousumi",
    "Payel",
    "Sriparna",
    "Aditi",
    "Swastika",
    "Baishakhi",
    "Mahua",
]
LAST_NAMES = [
    "Ganguly",
    "Chatterjee",
    "Mukherjee",
    "Banerjee",
    "Bhattacharya",
    "Das",
    "Dutta",
    "Bose",
    "Chakraborty",
    "Ghosh",
    "Sarkar",
    "Saha",
    "Pal",
    "Mondal",
    "Dey",
    "Adhikari",
    "Majumdar",
    "Chowdhury",
    "Basu",
    "Sinha",
    "Kar",
    "Bhowmik",
    "Biswas",
    "Karmakar",
]
KOLKATA_AREAS = [
    "Salt Lake",
    "Behala",
    "Garia",
    "Howrah",
    "Ballygunge",
    "New Town",
    "Rajarhat",
    "Dum Dum",
    "Tollygunge",
    "Jadavpur",
    "Baguiati",
    "Kasba",
]

# The 4 named demo users. login_id doubles as email per docs/01-data-model.md
# ("login_id: mobile number or email").
DEMO_USERS = [
    ("priya.sen@adamascricket.in", "Priya", "Sen", Gender.FEMALE, "administration"),
    ("debashish.roy@adamascricket.in", "Debashish", "Roy", Gender.MALE, "head_coach"),
    ("rakesh.nandi@adamascricket.in", "Rakesh", "Nandi", Gender.MALE, "coach"),
    ("anirban.basu@adamascricket.in", "Anirban", "Basu", Gender.MALE, "academy_head"),
    # Added for the manual fee-collection flow (record-payment) — Accounts
    # has only "view" on the enquiry/admission RBAC row, so a demo login
    # for it is what actually exercises that override in the UI.
    ("sunita.ghosh@adamascricket.in", "Sunita", "Ghosh", Gender.FEMALE, "accounts"),
]
DEMO_PASSWORD = "demo1234"

SOURCE_COUNTS = [
    ("website", 38),
    ("referral", 31),
    ("school", 24),
    ("walk_in", 18),
    ("tournament", 13),
    ("social", 11),
    ("club", 7),
]
assert sum(n for _, n in SOURCE_COUNTS) == 142


class Command(BaseCommand):
    help = "Seed the stakeholder-prototype demo dataset. DEBUG-only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true", help="Wipe existing demo data and rebuild."
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo refuses to run when DEBUG is False.")

        if options["flush"]:
            self._flush()
        elif Enquiry.objects.filter(enquiry_no=f"ENQ/{DEMO_SERIES}/00142").exists():
            self.stdout.write("Demo data already seeded — nothing to do.")
            return

        self.rng = random.Random(20260826)
        self._mobile_counter = itertools.count(1)
        self._trl_counter = itertools.count(1)
        self._adm_counter = itertools.count(1)
        self._aca_counter = itertools.count(1)

        with transaction.atomic():
            self._run()

        self.stdout.write(self.style.SUCCESS("Demo dataset seeded."))
        self.stdout.write(
            self.style.WARNING(
                "Not seeded: 'recent audit entries' — apps.audit has no AuditLog model "
                "yet (Phase 0 work outside this prompt's scope)."
            )
        )

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #

    @transaction.atomic
    def _flush(self):
        admission_ids = list(
            Admission.objects.filter(application_no__startswith=f"ADM/{DEMO_SERIES}/").values_list(
                "id", flat=True
            )
        )
        ApprovalRequest.objects.filter(
            content_type=ContentType.objects.get_for_model(Admission),
            object_id__in=admission_ids,
        ).delete()
        IDCard.objects.filter(card_no__startswith=f"ACA/{DEMO_SERIES}/").delete()
        Student.objects.filter(student_code__startswith=f"ACA/{DEMO_SERIES}/").delete()
        Admission.objects.filter(id__in=admission_ids).delete()
        Document.objects.filter(s3_key__startswith="demo/").delete()
        TrialResult.objects.filter(
            registration__trial_id__startswith=f"TRL/{DEMO_SERIES}/"
        ).delete()
        TrialAssessment.objects.filter(
            registration__trial_id__startswith=f"TRL/{DEMO_SERIES}/"
        ).delete()
        TrialRegistration.objects.filter(trial_id__startswith=f"TRL/{DEMO_SERIES}/").delete()
        TrialSlot.objects.filter(venue__code__in=["ground_a", "ground_b"]).delete()
        Enquiry.objects.filter(enquiry_no__startswith=f"ENQ/{DEMO_SERIES}/").delete()
        # Users/Staff before Person: both hold a PROTECT FK to Person.
        User.objects.filter(login_id__in=[u[0] for u in DEMO_USERS]).delete()
        Staff.objects.filter(employee_code__startswith="DEMO-").delete()
        Person.objects.filter(mobile__startswith=f"+91{DEMO_MOBILE_PREFIX}").delete()

    # ------------------------------------------------------------------ #
    # Orchestration
    # ------------------------------------------------------------------ #

    def _run(self):
        self.now = timezone.now()
        self.today = self.now.date()

        self.users = self._seed_users()
        self._seed_staff()
        ground_a, ground_b = self._seed_demo_venues()
        self.age_categories = {c.min_age: c for c in AgeCategory.objects.all()}
        self.criteria = list(AssessmentCriterion.objects.all())
        self.doc_types = {d.code: d for d in DocumentType.objects.all()}
        programme = Programme.objects.first()
        if programme is None:
            raise CommandError("No Programme rows found — run seed_master_data first.")
        self.programme: Programme = programme
        self.approver = self.users["academy_head"]

        self.approval_rule, _ = ApprovalRule.objects.get_or_create(
            module="admission",
            action="approve",
            defaults={"required_role": Role.objects.get(code="academy_head")},
        )

        generic_slots = self._seed_generic_slots()
        enquiries = self._seed_enquiries()
        recent10, older132 = enquiries[:10], enquiries[10:]
        sat_slot, sun_slot = self._seed_weekend_slots(ground_a, ground_b)
        recent_converted = self._classify_recent(recent10, sat_slot)
        self._seed_in_flight_admissions(recent_converted, generic_slots)
        self._seed_older_funnel(older132, sat_slot, sun_slot, generic_slots)

        # booked_count is denormalised — recompute from the real rows just
        # written, rather than trusting a hand-derived number a second time.
        for slot in (sat_slot, sun_slot):
            TrialSlot.objects.filter(pk=slot.pk).update(booked_count=slot.registrations.count())

    # ------------------------------------------------------------------ #
    # Users, staff, venues
    # ------------------------------------------------------------------ #

    def _seed_users(self) -> dict[str, User]:
        users = {}
        for login_id, first, last, gender, role_code in DEMO_USERS:
            person = self._get_or_create_person(first, last, gender=gender)
            user, _ = User.objects.update_or_create(
                login_id=login_id, defaults={"person": person, "is_active": True}
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            role = Role.objects.get(code=role_code)
            UserRole.objects.update_or_create(
                user=user,
                role=role,
                defaults={"valid_from": self.today - datetime.timedelta(days=365)},
            )
            users[role_code] = user
        return users

    def _seed_staff(self) -> None:
        coach_person = self.users["coach"].person
        assert coach_person is not None
        self.coach_rakesh, _ = Staff.objects.update_or_create(
            person=coach_person,
            defaults={
                "employee_code": "DEMO-STAFF-001",
                "staff_type": StaffType.COACH,
                "joining_date": self.today - datetime.timedelta(days=900),
            },
        )
        sujoy_person = self._get_or_create_person("Sujoy", "Halder", gender=Gender.MALE)
        self.coach_sujoy, _ = Staff.objects.update_or_create(
            person=sujoy_person,
            defaults={
                "employee_code": "DEMO-STAFF-002",
                "staff_type": StaffType.COACH,
                "joining_date": self.today - datetime.timedelta(days=700),
            },
        )
        self.generic_coaches: list[Staff] = []
        for i, (first, last) in enumerate(
            [("Debjit", "Sarkar"), ("Soham", "Dey"), ("Ritwik", "Basu")], start=3
        ):
            person = self._get_or_create_person(first, last, gender=Gender.MALE)
            s, _ = Staff.objects.update_or_create(
                person=person,
                defaults={
                    "employee_code": f"DEMO-STAFF-{i:03d}",
                    "staff_type": StaffType.COACH,
                    "joining_date": self.today - datetime.timedelta(days=500),
                },
            )
            self.generic_coaches.append(s)

    def _seed_demo_venues(self) -> tuple[Venue, Venue]:
        ground_a, _ = Venue.objects.get_or_create(code="ground_a", defaults={"name": "Ground A"})
        ground_b, _ = Venue.objects.get_or_create(code="ground_b", defaults={"name": "Ground B"})
        return ground_a, ground_b

    # ------------------------------------------------------------------ #
    # Person helper (SOP §78: never create a Person without resolving it)
    # ------------------------------------------------------------------ #

    def _next_mobile(self) -> str:
        return f"{DEMO_MOBILE_PREFIX}{next(self._mobile_counter):05d}"

    def _get_or_create_person(
        self, first: str, last: str, *, gender: str, dob: datetime.date | None = None
    ) -> Person:
        dob = dob or (self.today - datetime.timedelta(days=365 * self.rng.randint(30, 45)))
        mobile = self._next_mobile()
        match = resolve_person(
            {
                "first_name": first,
                "last_name": last,
                "date_of_birth": dob,
                "guardian_mobile": mobile,
            }
        )
        if match.found:
            return match.exact[0] if match.exact else match.fuzzy[0]

        area = self.rng.choice(KOLKATA_AREAS)
        return Person.objects.create(
            first_name=first,
            last_name=last,
            date_of_birth=dob,
            gender=gender,
            mobile=mobile,
            address_line1=f"{self.rng.randint(1, 200)}, {area}",
            city="Kolkata",
            state="West Bengal",
            pincode=f"7000{self.rng.randint(10, 99)}",
        )

    def _random_name(self) -> tuple[str, str, str]:
        gender = self.rng.choice([Gender.MALE, Gender.FEMALE])
        pool = FIRST_NAMES_MALE if gender == Gender.MALE else FIRST_NAMES_FEMALE
        return self.rng.choice(pool), self.rng.choice(LAST_NAMES), gender

    # ------------------------------------------------------------------ #
    # Base 142 enquiries, source-distributed
    # ------------------------------------------------------------------ #

    def _seed_enquiries(self) -> list[Enquiry]:
        source_lookup = {s.code: s for s in EnquirySource.objects.all()}
        plan: list[str] = []
        for code, count in SOURCE_COUNTS:
            plan.extend([code] * count)
        self.rng.shuffle(plan)

        enquiries = []
        for i, source_code in enumerate(plan, start=1):
            first, last, gender = self._random_name()
            guardian_first, guardian_last, _ = self._random_name()
            dob = self.today - datetime.timedelta(days=365 * self.rng.randint(8, 18))
            enquiry = Enquiry.objects.create(
                enquiry_no=f"ENQ/{DEMO_SERIES}/{i:05d}",
                student_name=f"{first} {last}",
                date_of_birth=dob,
                gender=gender,
                guardian_name=f"{guardian_first} {guardian_last}",
                guardian_mobile=f"+91{self._next_mobile()}",
                guardian_email=f"{guardian_first.lower()}.{guardian_last.lower()}@example.com",
                address=f"{self.rng.randint(1, 200)}, {self.rng.choice(KOLKATA_AREAS)}, Kolkata",
                playing_role=self.rng.choice(PlayingRole.values),
                source=source_lookup[source_code],
                status=EnquiryStatus.NEW,
                owner=self.users["administration"],
            )
            self._backdate(enquiry, days=self.rng.randint(15, 150))
            enquiries.append(enquiry)
        return enquiries

    def _backdate(self, enquiry: Enquiry, *, days: int):
        Enquiry.objects.filter(pk=enquiry.pk).update(
            created_at=self.now - datetime.timedelta(days=days)
        )

    # ------------------------------------------------------------------ #
    # Weekend trial slots
    # ------------------------------------------------------------------ #

    def _seed_weekend_slots(self, ground_a: Venue, ground_b: Venue):
        sat_date, _sun_date = upcoming_weekend(self.today)
        sat_slot = TrialSlot.objects.create(
            date=sat_date,
            venue=ground_a,
            reporting_time=datetime.time(7, 0),
            age_category=self.age_categories[13],  # U-14
            capacity=20,
            booked_count=14,
        )
        sun_slot = TrialSlot.objects.create(
            date=sat_date + datetime.timedelta(days=1),
            venue=ground_b,
            reporting_time=datetime.time(7, 0),
            age_category=self.age_categories[15],  # U-16
            capacity=20,
            booked_count=9,
        )
        return sat_slot, sun_slot

    # ------------------------------------------------------------------ #
    # The 10 "recent" enquiries
    # ------------------------------------------------------------------ #

    def _classify_recent(self, recent10, sat_slot):
        new_batch = recent10[0:2]
        for e in new_batch:
            self._backdate(e, days=self.rng.randint(1, 13))
            e.status = EnquiryStatus.NEW
            e.save(update_fields=["status"])

        contacted_batch = recent10[2:5]
        for e, days_ago in zip(contacted_batch, (6, 8, 12), strict=True):
            self._backdate(e, days=days_ago + 1)
            e.status = EnquiryStatus.CONTACTED
            e.save(update_fields=["status"])
            contacted_on = self.now - datetime.timedelta(days=days_ago)
            EnquiryFollowUp.objects.create(
                enquiry=e,
                contacted_on=contacted_on,
                mode=FollowUpMode.CALL,
                notes="Discussed trial slots.",
                next_action_on=(contacted_on - datetime.timedelta(days=2)).date(),
                created_by=self.users["administration"],
            )

        trial_booked_batch = recent10[5:7]
        for e in trial_booked_batch:
            self._backdate(e, days=self.rng.randint(1, 5))
            e.status = EnquiryStatus.TRIAL_SCHEDULED
            e.save(update_fields=["status"])
            self._make_trial_registration(e, sat_slot, attended=False)

        converted_batch = recent10[7:10]
        for e in converted_batch:
            self._backdate(e, days=self.rng.randint(2, 10))

        return converted_batch

    # ------------------------------------------------------------------ #
    # Trial / assessment / result / admission / student helpers
    # ------------------------------------------------------------------ #

    def _resolve_enquiry_person(self, enquiry: Enquiry) -> Person:
        existing = enquiry.person
        if existing is not None:
            return existing
        first, _, last = enquiry.student_name.partition(" ")
        person = self._get_or_create_person(
            first, last or "Athlete", gender=enquiry.gender, dob=enquiry.date_of_birth
        )
        enquiry.person = person
        enquiry.save(update_fields=["person"])
        return person

    def _make_trial_registration(
        self, enquiry: Enquiry, slot: TrialSlot, *, attended: bool
    ) -> TrialRegistration:
        person = self._resolve_enquiry_person(enquiry)
        return TrialRegistration.objects.create(
            trial_id=f"TRL/{DEMO_SERIES}/{next(self._trl_counter):05d}",
            enquiry=enquiry,
            person=person,
            slot=slot,
            payment_status=PaymentStatus.PAID,
            attended=attended,
        )

    def _register_and_assess(
        self, enquiry: Enquiry, slot: TrialSlot, coach: Staff
    ) -> TrialRegistration:
        reg = self._make_trial_registration(enquiry, slot, attended=True)
        assessed_at = timezone.make_aware(datetime.datetime.combine(slot.date, slot.reporting_time))
        assessment = TrialAssessment.objects.create(
            registration=reg,
            assessed_by=coach,
            assessed_at=assessed_at,
            overall_remarks="Solid technique, good attitude.",
        )
        TrialAssessmentScore.objects.bulk_create(
            TrialAssessmentScore(
                assessment=assessment, criterion=criterion, score=self.rng.randint(5, 9)
            )
            for criterion in self.criteria
        )
        return reg

    def _declare_result(self, reg: TrialRegistration, outcome: str):
        TrialResult.objects.create(
            registration=reg,
            outcome=outcome,
            declared_by=self.users["head_coach"],
            declared_at=self.now,
            review_on=(
                self.today + datetime.timedelta(days=7)
                if outcome in (TrialOutcome.SHORTLISTED, TrialOutcome.WAITLISTED)
                else None
            ),
        )

    def _make_admission(
        self, reg: TrialRegistration, *, step: str, rejected_birth_certificate: bool = False
    ) -> Admission:
        person = reg.person
        assert person is not None
        admission = Admission.objects.create(
            application_no=f"ADM/{DEMO_SERIES}/{next(self._adm_counter):05d}",
            person=person,
            enquiry=reg.enquiry,
            trial_registration=reg,
            programme=self.programme,
            step=step,
        )
        if rejected_birth_certificate:
            doc = Document.objects.create(
                document_type=self.doc_types["birth_certificate"],
                owner=reg.person,
                s3_key=f"demo/{admission.application_no}/birth_certificate.pdf",
                original_filename="birth_certificate.pdf",
                mime_type="application/pdf",
                size_bytes=204_800,
                status=DocumentStatus.REJECTED,
                verified_by=self.users["administration"],
                verified_at=self.now,
                rejection_reason="Document is illegible — please re-upload a clearer scan.",
            )
            AdmissionChecklistItem.objects.create(
                admission=admission,
                document_type=self.doc_types["birth_certificate"],
                document=doc,
                status="rejected",
            )
        return admission

    def _make_student(self, admission: Admission, *, status: str, admission_date) -> Student:
        # Every demo admission comes from _make_admission(), which always
        # sets both — true for every admission this seed command builds.
        assert admission.person is not None
        assert admission.programme is not None
        student = Student.objects.create(
            student_code=f"ACA/{DEMO_SERIES}/{next(self._aca_counter):04d}",
            person=admission.person,
            admission=admission,
            admission_date=admission_date,
            programme=admission.programme,
            status=StudentStatus.ACTIVE,
        )
        StudentStatusHistory.objects.create(
            student=student,
            from_status="",
            to_status=StudentStatus.ACTIVE,
            reason="Admission approved.",
            changed_by=self.approver,
        )
        if status != StudentStatus.ACTIVE:
            StudentStatusHistory.objects.create(
                student=student,
                from_status=StudentStatus.ACTIVE,
                to_status=status,
                reason="Demo data variety.",
                changed_by=self.approver,
            )
            Student.objects.filter(pk=student.pk).update(status=status)
        IDCard.objects.create(
            student=student,
            card_no=f"{student.student_code}-1",
            issued_on=admission_date,
            valid_until=admission_date + datetime.timedelta(days=365 * 3),
            qr_payload=f"demo-signed-token-{student.student_code}",
            issued_by=self.approver,
        )
        return student

    # ------------------------------------------------------------------ #
    # The 3 recent "converted" -> in-flight admissions
    # ------------------------------------------------------------------ #

    def _seed_in_flight_admissions(self, recent_converted, generic_slots):
        for e in recent_converted:
            e.status = EnquiryStatus.CONVERTED
            e.save(update_fields=["status"])

        fee_pending_e, awaiting_now_e, awaiting_2days_e = recent_converted

        reg = self._register_and_assess(
            fee_pending_e, self.rng.choice(generic_slots), self.rng.choice(self.generic_coaches)
        )
        self._declare_result(reg, TrialOutcome.SELECTED)
        self._make_admission(reg, step=AdmissionStep.FEE_PENDING)

        reg = self._register_and_assess(
            awaiting_now_e, self.rng.choice(generic_slots), self.rng.choice(self.generic_coaches)
        )
        self._declare_result(reg, TrialOutcome.SELECTED)
        admission = self._make_admission(reg, step=AdmissionStep.FEE_CLEARED)
        ApprovalRequest.objects.create(
            rule=self.approval_rule,
            content_type=ContentType.objects.get_for_model(Admission),
            object_id=admission.id,
            requested_by=self.users["administration"],
        )

        reg = self._register_and_assess(
            awaiting_2days_e, self.rng.choice(generic_slots), self.rng.choice(self.generic_coaches)
        )
        self._declare_result(reg, TrialOutcome.SELECTED)
        admission = self._make_admission(reg, step=AdmissionStep.FEE_CLEARED)
        approval = ApprovalRequest.objects.create(
            rule=self.approval_rule,
            content_type=ContentType.objects.get_for_model(Admission),
            object_id=admission.id,
            requested_by=self.users["administration"],
        )
        ApprovalRequest.objects.filter(pk=approval.pk).update(
            created_at=self.now - datetime.timedelta(days=2)
        )

    # ------------------------------------------------------------------ #
    # The 132 "older" enquiries: the season's historical funnel
    # ------------------------------------------------------------------ #

    def _seed_older_funnel(self, older132, sat_slot, sun_slot, generic_slots):
        older_iter = iter(older132)

        # 93 older-attended: 58 selected (1 doc-pending in-flight, 43
        # approved, 14 selected-only) + 35 non-selected. The first 18 land
        # on the two weekend slots (9 Sat + 9 Sun), coaches per the brief.
        plan: list[tuple[TrialOutcome, str]] = (
            [(TrialOutcome.SELECTED, "doc_pending")]
            + [(TrialOutcome.SELECTED, "approved")] * 43
            + [(TrialOutcome.SELECTED, "selected_only")] * 14
            + [(TrialOutcome.SHORTLISTED, "non_selected")] * 8
            + [(TrialOutcome.WAITLISTED, "non_selected")] * 7
            + [(TrialOutcome.NOT_SELECTED, "non_selected")] * 15
            + [(TrialOutcome.RE_TRIAL, "non_selected")] * 5
        )
        self.rng.shuffle(plan)
        assert len(plan) == 93

        doc_pending_reg: TrialRegistration | None = None
        approved_regs: list[TrialRegistration] = []

        for i, (outcome, role) in enumerate(plan):
            e = next(older_iter)
            if i < 9:
                slot, coach = sat_slot, self.coach_rakesh
            elif i < 18:
                slot, coach = sun_slot, self.coach_sujoy
            else:
                slot, coach = self.rng.choice(generic_slots), self.rng.choice(self.generic_coaches)

            reg = self._register_and_assess(e, slot, coach)
            self._declare_result(reg, outcome)

            if role == "doc_pending":
                doc_pending_reg = reg
                e.status = EnquiryStatus.CONVERTED
            elif role == "approved":
                approved_regs.append(reg)
                e.status = EnquiryStatus.CONVERTED
            elif role == "selected_only":
                e.status = EnquiryStatus.CONVERTED
            elif outcome == TrialOutcome.NOT_SELECTED:
                e.status = EnquiryStatus.LOST
            else:
                e.status = EnquiryStatus.TRIAL_SCHEDULED
            e.save(update_fields=["status"])

        # documents_pending in-flight admission (the 4th "in flight").
        assert doc_pending_reg is not None
        self._make_admission(
            doc_pending_reg, step=AdmissionStep.DOCUMENTS_PENDING, rejected_birth_certificate=True
        )

        # 43 approved -> students. 3 with a recent admission_date, 2 with a
        # non-active status (so 41 of the 43 end up active).
        recent_admission_idx = set(self.rng.sample(range(43), 3))
        for i, reg in enumerate(approved_regs):
            admission = self._make_admission(reg, step=AdmissionStep.APPROVED)
            Admission.objects.filter(pk=admission.pk).update(
                approved_by=self.users["academy_head"], approved_at=self.now
            )
            if i in recent_admission_idx:
                admission_date = self.today - datetime.timedelta(days=self.rng.randint(1, 13))
            else:
                admission_date = self.today - datetime.timedelta(days=self.rng.randint(20, 140))
            student_status = StudentStatus.ACTIVE
            if i == 0:
                student_status = StudentStatus.LEAVE
            elif i == 1:
                student_status = StudentStatus.WITHDRAWN
            self._make_student(admission, status=student_status, admission_date=admission_date)

        # 3 more pending (unattended) registrations, filling Saturday's
        # remaining 3 of its 5 pending seats (2 already came from recent10).
        for _ in range(3):
            e = next(older_iter)
            e.status = EnquiryStatus.TRIAL_SCHEDULED
            e.save(update_fields=["status"])
            self._make_trial_registration(e, sat_slot, attended=False)

        # No-trial filler for the rest of the older pool.
        no_trial_plan = (
            [EnquiryStatus.NOT_INTERESTED] * 13
            + [EnquiryStatus.LOST] * 11
            + [EnquiryStatus.CONTACTED] * 7
            + [EnquiryStatus.NEW] * 5
        )
        for status in no_trial_plan:
            e = next(older_iter, None)
            if e is None:
                break
            e.status = status
            e.save(update_fields=["status"])

        # 7 documents awaiting verification, 2 rejected — 1 already created
        # (the tied birth-certificate rejection above); 5 submitted + 1
        # more rejected here.
        submitted_owners = self.rng.sample(approved_regs, 5)
        for i, reg in enumerate(submitted_owners):
            Document.objects.create(
                document_type=self.rng.choice(list(self.doc_types.values())),
                owner=reg.person,
                s3_key=f"demo/misc/{i}-submitted.pdf",
                original_filename="document.pdf",
                mime_type="application/pdf",
                size_bytes=150_000,
                status=DocumentStatus.SUBMITTED,
            )
        rejected_owner = approved_regs[-1]
        Document.objects.create(
            document_type=self.doc_types["aadhaar_card"],
            owner=rejected_owner.person,
            s3_key="demo/misc/other-rejected.pdf",
            original_filename="aadhaar_card.pdf",
            mime_type="application/pdf",
            size_bytes=120_000,
            status=DocumentStatus.REJECTED,
            verified_by=self.users["administration"],
            verified_at=self.now,
            rejection_reason="Photo does not match.",
        )

    def _seed_generic_slots(self) -> list[TrialSlot]:
        main_ground = Venue.objects.get(code="main_ground")
        indoor_nets = Venue.objects.get(code="indoor_nets")
        slots = []
        for week in range(12):
            venue = main_ground if week % 2 == 0 else indoor_nets
            age = self.rng.choice(list(self.age_categories.values()))
            slot = TrialSlot.objects.create(
                date=self.today - datetime.timedelta(weeks=week, days=self.rng.randint(0, 6)),
                venue=venue,
                reporting_time=datetime.time(7, 0),
                age_category=age,
                capacity=20,
                booked_count=0,
            )
            slots.append(slot)
        return slots
