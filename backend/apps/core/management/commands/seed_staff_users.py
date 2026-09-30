"""Creates named staff logins with roles (login_id, one role each).

Idempotent: update_or_create on User.login_id, so re-running just resets the
password/role rather than duplicating anything.

The Person fields the requester didn't supply (mobile, date_of_birth,
gender, address) are filled with an obvious PLACEHOLDER_* marker rather than
guessed real values — CLAUDE.md rule 1 (SOP §78) makes the identity model
the one place a wrong guess is expensive, and `mobile` in particular is a
real identifier used elsewhere (OTP, dedupe). Every placeholder Person this
command creates is listed in the command's own output so they get corrected
with real details before being treated as real records.
"""

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.iam.models import Role, User, UserRole
from apps.people.models import Gender, Person, Staff, StaffType
from apps.people.services import resolve_person

PLACEHOLDER_PASSWORD = "demo1234"
PLACEHOLDER_DOB = datetime.date(1990, 1, 1)
PLACEHOLDER_MOBILE_PREFIX = "99999000"  # obviously-fake block, distinct from real Indian ranges
PLACEHOLDER_ADDRESS = {
    "address_line1": "Address pending",
    "city": "Kolkata",
    "state": "West Bengal",
    "pincode": "700001",
}
PLACEHOLDER_EMPLOYEE_CODE_PREFIX = "STAFF-"

# (login_id, first_name, last_name, gender, role_code)
STAFF_USERS = [
    ("priya.sen@adamascricket.in", "Priya", "Sen", Gender.FEMALE, "administration"),
    ("debashish.roy@adamascricket.in", "Debashish", "Roy", Gender.MALE, "head_coach"),
    ("rakesh.nandi@adamascricket.in", "Rakesh", "Nandi", Gender.MALE, "coach"),
    ("anirban.basu@adamascricket.in", "Anirban", "Basu", Gender.MALE, "academy_head"),
]

# docs/01-data-model.md's Staff.staff_type choices don't distinguish
# head_coach/academy_head from coach/administration — those are RBAC roles,
# a different axis from HR staff_type. Best-effort mapping, not a guess at
# a field that doesn't exist: every role here lands on the closest of the
# two staff_type categories the SOP-derived model actually has.
ROLE_TO_STAFF_TYPE = {
    "administration": StaffType.ADMIN,
    "academy_head": StaffType.ADMIN,
    "head_coach": StaffType.COACH,
    "coach": StaffType.COACH,
}


class Command(BaseCommand):
    help = (
        "Create/update the named staff logins with one role each, using "
        "placeholder Person details (mobile/DOB/address) pending real data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only",
            help="Comma-separated login_id(s) to seed, instead of the full STAFF_USERS list.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        only = {v.strip() for v in options["only"].split(",")} if options.get("only") else None
        # Index is each entry's fixed position in STAFF_USERS, not its position
        # in the filtered subset — --only rakesh.nandi@... must still mint the
        # same placeholder mobile/employee_code a full run would give them,
        # or a later full run collides with what this run already created.
        indexed_staff_users = list(enumerate(STAFF_USERS, start=1))
        if only is not None:
            indexed_staff_users = [(i, u) for i, u in indexed_staff_users if u[0] in only]
            missing = only - {u[0] for _, u in indexed_staff_users}
            if missing:
                raise CommandError(f"Unknown login_id(s) in --only: {', '.join(sorted(missing))}")

        try:
            roles = {
                code: Role.objects.get(code=code)
                for _, (_, _, _, _, code) in indexed_staff_users
            }
        except Role.DoesNotExist as exc:
            raise CommandError(
                "Role master data missing — run `manage.py seed_roles` first."
            ) from exc

        today = datetime.date.today()
        placeholder_people = []

        for i, (login_id, first, last, gender, role_code) in indexed_staff_users:
            existing_user = User.objects.filter(login_id=login_id).select_related("person").first()
            if existing_user is not None and existing_user.person is not None:
                person = existing_user.person
            else:
                mobile = f"{PLACEHOLDER_MOBILE_PREFIX}{i:02d}"
                match = resolve_person(
                    {
                        "first_name": first,
                        "last_name": last,
                        "date_of_birth": PLACEHOLDER_DOB,
                        "guardian_mobile": mobile,
                    }
                )
                if match.found:
                    person = match.exact[0] if match.exact else match.fuzzy[0]
                else:
                    person = Person.objects.create(
                        first_name=first,
                        last_name=last,
                        date_of_birth=PLACEHOLDER_DOB,
                        gender=gender,
                        mobile=mobile,
                        **PLACEHOLDER_ADDRESS,
                    )
                placeholder_people.append((login_id, person))

            user, _ = User.objects.update_or_create(
                login_id=login_id, defaults={"person": person, "is_active": True}
            )
            user.set_password(PLACEHOLDER_PASSWORD)
            user.save()

            UserRole.objects.update_or_create(
                user=user,
                role=roles[role_code],
                defaults={"valid_from": today},
            )

            Staff.objects.update_or_create(
                person=person,
                defaults={
                    "employee_code": f"{PLACEHOLDER_EMPLOYEE_CODE_PREFIX}{i:04d}",
                    "staff_type": ROLE_TO_STAFF_TYPE[role_code],
                    "joining_date": today,
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(indexed_staff_users)} staff user(s) with roles.")
        )
        if placeholder_people:
            self.stdout.write(
                self.style.WARNING(
                    "PLACEHOLDER identity data used for the following — replace with real "
                    "mobile/date of birth/address before treating these as real records:"
                )
            )
            for login_id, person in placeholder_people:
                self.stdout.write(
                    self.style.WARNING(f"  - {login_id}: Person id={person.id}, mobile={person.mobile}")
                )
