"""Realistic starting master data for an Indian cricket academy.

Idempotent via update_or_create() throughout — re-running updates existing
rows rather than duplicating them. These are starting points, not fixed
policy: Administration edits all of this through Django admin afterward
(docs/01-data-model.md section 4).
"""

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import (
    AgeCategory,
    ApprovalRule,
    AssessmentCriterion,
    DocumentType,
    EnquirySource,
    Programme,
    Season,
    TrainingType,
    Venue,
)
from apps.iam.models import Role

PROGRAMMES = [
    ("junior_development", "Junior Development"),
    ("elite_pathway", "Elite Pathway"),
]

# "U-10 to U-19", each a single-year band (Under-N = completed age N-1),
# on a single academy-wide September 1st cutoff. Used for trial-slot
# eligibility (TrialSlot.age_category) — fine-grained by design, since a
# trial day is run for one specific age year.
AGE_CATEGORY_CUTOFF = "09-01"
AGE_CATEGORIES = [(f"u{n}", f"Under-{n}", n - 1, n - 1) for n in range(10, 20)]

# The coarser playing-group brackets a *seat* is admitted into
# (AdmissionIntake.age_category, direct-admission feature) — a different
# granularity than the trial bands above, so distinct codes rather than
# colliding with "u12"/"u14"/etc, which already mean a single age year.
ADMISSION_AGE_BRACKETS = [
    ("under12", "Under-12", 5, 11),
    ("under14", "Under-14", 12, 13),
    ("under16", "Under-16", 14, 15),
    ("under19", "Under-19", 16, 18),
    ("under23", "Under-23", 19, 22),
    ("senior", "Senior", 23, 45),
]

VENUES = [
    ("main_ground", "Main Ground"),
    ("indoor_nets", "Indoor Nets"),
]

SEASONS = [
    # (code, name, start_date, end_date, age_cutoff_date)
    (
        "2026-27",
        "2026-27 Season",
        datetime.date(2026, 4, 1),
        datetime.date(2027, 3, 31),
        datetime.date(2026, 4, 1),
    ),
]

# docs/01-data-model.md section 5, Enquiry.source — verbatim, not invented.
ENQUIRY_SOURCES = [
    ("website", "Website"),
    ("social", "Social Media"),
    ("walk_in", "Walk-in"),
    ("school", "School"),
    ("club", "Club"),
    ("referral", "Referral"),
    ("tournament", "Tournament"),
    ("trial", "Trial"),
    ("advertisement", "Advertisement"),
]

TRAINING_TYPES = [
    ("batting", "Batting"),
    ("bowling", "Bowling"),
    ("fielding", "Fielding"),
    ("fitness_conditioning", "Fitness & Conditioning"),
    ("match_practice", "Match Practice"),
]

# docs/07-storage.md's own examples (birth certificate, Aadhaar, school ID,
# medical certificate) plus the other two documents every Indian school/
# academy admission checklist routinely requires.
DOCUMENT_TYPES = [
    # (code, name, is_mandatory_default, has_expiry)
    ("birth_certificate", "Birth Certificate", True, False),
    ("aadhaar_card", "Aadhaar Card", True, False),
    ("school_id", "School ID", False, False),
    ("medical_certificate", "Medical Certificate", True, True),
    ("address_proof", "Address Proof", True, False),
    ("transfer_certificate", "Transfer Certificate", False, False),
]

# The nine SOP §8 dimensions — one criterion per group, scored 1-10,
# equally weighted. The Head Coach adjusts these through admin.
ASSESSMENT_CRITERIA = [
    # (code, name, group)
    ("batting", "Batting", "batting"),
    ("bowling", "Bowling", "bowling"),
    ("fielding", "Fielding", "fielding"),
    ("wicketkeeping", "Wicketkeeping", "wicketkeeping"),
    ("fitness", "Fitness", "fitness"),
    ("game_awareness", "Game Awareness", "game_awareness"),
    ("discipline", "Discipline", "discipline"),
    ("attitude", "Attitude", "attitude"),
    ("potential", "Potential", "potential"),
]


class Command(BaseCommand):
    help = "Seed realistic starting master data for an Indian cricket academy."

    @transaction.atomic
    def handle(self, *args, **options):
        counts = {}

        counts["programmes"] = self._seed(Programme, PROGRAMMES, lambda code, name: {"name": name})
        counts["age categories"] = self._seed(
            AgeCategory,
            AGE_CATEGORIES,
            lambda code, name, min_age, max_age: {
                "name": name,
                "min_age": min_age,
                "max_age": max_age,
                "as_on_date_rule": AGE_CATEGORY_CUTOFF,
            },
        )
        counts["admission age brackets"] = self._seed(
            AgeCategory,
            ADMISSION_AGE_BRACKETS,
            lambda code, name, min_age, max_age: {
                "name": name,
                "min_age": min_age,
                "max_age": max_age,
                "as_on_date_rule": AGE_CATEGORY_CUTOFF,
            },
        )
        counts["venues"] = self._seed(Venue, VENUES, lambda code, name: {"name": name})
        counts["seasons"] = self._seed(
            Season,
            SEASONS,
            lambda code, name, start_date, end_date, age_cutoff_date: {
                "name": name,
                "start_date": start_date,
                "end_date": end_date,
                "age_cutoff_date": age_cutoff_date,
            },
        )
        counts["enquiry sources"] = self._seed(
            EnquirySource, ENQUIRY_SOURCES, lambda code, name: {"name": name}
        )
        counts["training types"] = self._seed(
            TrainingType, TRAINING_TYPES, lambda code, name: {"name": name}
        )
        counts["document types"] = self._seed(
            DocumentType,
            DOCUMENT_TYPES,
            lambda code, name, is_mandatory_default, has_expiry: {
                "name": name,
                "is_mandatory_default": is_mandatory_default,
                "has_expiry": has_expiry,
                "applies_to": "admission",
            },
        )
        counts["assessment criteria"] = self._seed(
            AssessmentCriterion,
            ASSESSMENT_CRITERIA,
            lambda code, name, group: {
                "name": name,
                "group": group,
                "scale_min": 1,
                "scale_max": 10,
                "weight": 1,
            },
        )

        counts["approval rules"] = self._seed_approval_rules()

        summary = ", ".join(f"{count} {label}" for label, count in counts.items())
        self.stdout.write(self.style.SUCCESS(f"Seeded {summary}."))

    def _seed_approval_rules(self) -> int:
        """`apps.core` is allowed to know about `apps.iam` here for the same
        reason `seed_roles.py` is — seed commands are bootstrapping scripts,
        not core's reusable framework code (docs/00-project-structure.md).
        Requires `seed_roles` to have already run (`make seed` always runs
        it first); skips with a warning rather than crashing the rest of
        this command if it hasn't.
        """
        try:
            academy_head = Role.objects.get(code="academy_head")
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped approval rules — run seed_roles first (no 'academy_head' role)."
                )
            )
            return 0

        rules = [
            # (module, action) -> required_role. admission:approve is
            # docs/04-state-machines.md section 1's fee_cleared -> approved
            # gate; admission:trial_waiver is the direct-admission path
            # (docs/05-build-sequence.md T-607). students:suspended and
            # students:withdrawn are docs/04-state-machines.md section 2's
            # "active -> suspended and -> withdrawn require an
            # ApprovalRequest" rule (apps.admissions.student.state's
            # APPROVAL_GATED_TARGETS).
            ("admission", "approve", academy_head),
            ("admission", "trial_waiver", academy_head),
            ("students", "suspended", academy_head),
            ("students", "withdrawn", academy_head),
        ]
        for module, action, role in rules:
            ApprovalRule.objects.update_or_create(
                module=module, action=action, defaults={"required_role": role}
            )
        return len(rules)

    @staticmethod
    def _seed(model, rows, build_defaults) -> int:
        for row in rows:
            code = row[0]
            model.objects.update_or_create(code=code, defaults=build_defaults(*row))
        return len(rows)
