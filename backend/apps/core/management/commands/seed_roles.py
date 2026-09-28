"""Loads the 16 SOP §5 roles and the docs/03-rbac.md permission matrix.

Idempotent: re-running this updates existing rows (role names, permission
scopes) rather than duplicating them, via update_or_create() throughout.

This is the one place apps.core is allowed to know about apps.iam: seed
commands are bootstrapping scripts, not apps.core's reusable framework
code, so they sit outside the "core imports nothing from apps/" rule
(docs/00-project-structure.md) that governs core's actual Python package.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.iam.models import Permission, Role, RolePermission, Scope, Verb

# docs/03-rbac.md — column order. Every MATRIX row's cell string must have
# exactly one token per role, in this same order.
ROLES = [
    ("academy_management", "Academy Management"),
    ("academy_head", "Academy Head"),
    ("sports_ops", "Sports Operations"),
    ("administration", "Administration"),
    ("accounts", "Accounts"),
    ("head_coach", "Head Coach"),
    ("coach", "Coach"),
    ("strength_conditioning", "Strength & Conditioning"),
    ("medical_team", "Medical Team"),
    ("physiotherapist", "Physiotherapist"),
    ("hostel", "Hostel"),
    ("transport", "Transport"),
    ("athlete_management", "Athlete Management"),
    ("student", "Student"),
    ("parent", "Parent"),
    ("it_admin", "IT Admin"),
]
ROLE_CODES = [code for code, _ in ROLES]

VERB_LETTERS = {
    "V": Verb.VIEW,
    "A": Verb.ADD,
    "E": Verb.EDIT,
    "P": Verb.APPROVE,
    "X": Verb.EXPORT,
}

# One row per docs/03-rbac.md module group; cells in ROLE_CODES order.
#
# "idcard" previously had no row at all (absent from docs/03-rbac.md,
# flagged rather than guessed at). Phase 1 now builds the idcard module, so
# it needs one to be reachable at all — docs/03-rbac.md has been updated
# with a provisional row (Administration issues, Academy Head oversees,
# Head Coach/Student/Parent view only), flagged there for Academy Head
# sign-off the same way D-01/D-02/D-03 are, rather than left unbuildable.
MATRIX: list[tuple[list[str], str]] = [
    # Split from a single bundled "enquiry, trial, admission" row: SOP
    # narrative and docs/02-api-spec.md ("POST /trials/registrations/{id}/
    # result | trial/approve | Head Coach. Locks the assessment") are
    # explicit that Head Coach declares trial results — an `approve`
    # action — but the originally-bundled row gave Head Coach only "VAE"
    # (no P) across all three modules. Granting `approve` on the *bundled*
    # row would also have let Head Coach decide admissions and rejections,
    # which nothing in the SOP supports (that's Academy Head's job,
    # enforced separately by `ApprovalRule.required_role` regardless of
    # this coarse verb grant) — so `trial` gets its own row instead, equal
    # to the original bundle except Head Coach also has `P`.
    # `student` gained own-scope `V` here for the direct-admission
    # feature's `GET /admissions/mine` (step 2.1's self-service candidate
    # portal) — `AdmissionViewSet.filter_to_own` still returns nothing for
    # the ordinary list/retrieve routes (unaffected; `mine` bypasses
    # get_queryset() with its own person-scoped query), and the matching
    # `enquiry` grant this bundled row also implies is inert: no candidate
    # is ever an `Enquiry.owner` (EnquiryViewSet.filter_to_own's "enquiries
    # this user is chasing"), so it never actually surfaces anything.
    (["enquiry", "admission"], "VX VAEPX VAE VAE V VAE VA - - - - - V O - V"),
    (["trial"], "VX VAEPX VAE VAE V VAEP VA - - - - - V - - V"),
    (["idcard"], "VX VAX V VA - V - - - - - - - O O V"),
    (["students"], "VX VAEPX VAE VAE V V V V V V V V V O O V"),
    # Split from `students` on purpose (Prompt G): that module's own-scope
    # grant for Student/Parent is view-only, and several of its `edit`
    # actions (status changes, guardian management, login access) are
    # staff-only — widening `students`' own edit to cover student/parent
    # would have handed them those too. This module covers only the
    # profile-completion form itself.
    (["student_profile"], "VX VAEPX VAE VAE V V V V V V V V V OE OE V"),
    # `student` gained `A` here for the direct-admission feature's step
    # 2.1: once Administration enables portal access post-payment, the
    # candidate uploads their own admission documents themselves, the
    # same way `parent` already uploads for a child — see
    # apps.admissions.document.views._check_owner_scope's "admission"
    # branch, the object-level check that keeps this to their *own*
    # admission rather than opening self-service uploads generally.
    (["documents"], "VX VAEPX VAE VAEP V - - - V - V - V OA OA V"),
    # "training" dropped from this row's slug list — it was seeded
    # alongside `batch` from the start but no ViewSet has ever used
    # module="training" (confirmed by direct inspection); keeping it would
    # have implied a second real module that doesn't exist.
    (["batch"], "VX VAEPX VAE VAE - VAEP VAE VAE V V V - V O O V"),
    # Split from `batch` on purpose: creating/editing/deleting the Batch
    # record itself (docs/05-build-sequence.md's later batch-management
    # prompt) needs a narrower role set than enrolling/transferring
    # students, which the row above already grants broadly to Sports Ops,
    # Coach and S&C. Only Administration, Academy Head and Head Coach get
    # `A`/`E` here — `DELETE` also maps to verb "edit"
    # (ModuleScopedViewSet._METHOD_VERBS), so no separate delete verb is
    # needed. Everyone else keeps `V` for matrix completeness even though
    # no endpoint checks batch_admin:view yet, same as any other
    # not-yet-bold row in docs/03-rbac.md.
    (["batch_admin"], "V VAEX V VAE - VAE V V V V V - V - - V"),
    # Split from the bundled row above, same reasoning as `trial`'s own
    # split (comment further up): approving an AttendanceCorrection was
    # originally "Head Coach only" (SOP §70) — since extended to
    # Administration and Academy Head too (both P now), matching the same
    # dual/triple-role decision-maker precedent `payment`'s row already
    # uses for settling a payment. Coach's cell is now `OAE` (own scope)
    # instead of `VAE` (all scope) — a Coach only sees/marks/cancels
    # attendance for sessions they are TrainingSession.coach on, enforced
    # via SessionAttendanceViewSet/AttendanceViewSet/
    # AttendanceCorrectionViewSet/BatchReportViewSet's filter_to_own.
    # Administration/Academy Head/Head Coach/Sports Ops/S&C are unaffected
    # (still `all` scope).
    (["attendance"], "VX VAEPX VAE VAEP - VAEP OAE VAE V V V - V O O V"),
    (["fees"], "VX VAEPX V VAE VAEPX - - - - - V V - O O V"),
    # New for the fee-first direct-admission wizard: verifying a recorded
    # payment (Prompt D's /admissions/{id}/verify-payment/) is its own
    # module+verb rather than riding on `admission`/edit the way the old
    # trial-chain's Accounts fee-clearance carve-out did — the whole point
    # was to replace that hardcoded role check with real RBAC data
    # (CLAUDE.md rule 3). Administration and Accounts both get `approve`,
    # matching the same dual-role precedent docs/04-state-machines.md
    # already documents for the trial chain's own fee_pending -> fee_cleared.
    # `student`/`parent` gained own-scope `V` here for the unified payment
    # ledger's portal view (GET /students/me/payments,
    # /parents/me/children/{id}/payments/) — record/settle stay
    # Administration+Accounts only, same as before.
    (["payment"], "V V - VAEP VAEP - - - - - - - - O O V"),
    (["performance"], "VX VAEPX VAE V - VAEP VAE VAE V V - - V O O V"),
    (["coach_evaluation"], "VX VAEPX VAE V - VAE O - - - - - - - - V"),
    (["medical"], "V V - - - V - V VAEPX VAE V - - O O -"),
    (["competition"], "VX VAEPX VAE VAE - VAEP VAE V V V - - VX O O V"),
    (["athlete"], "VX VAEPX V - - VAE V V V - - - VAEPX O O V"),
    (["scouting"], "VX VAEPX V - - V - - - - - - VAEPX - - V"),
    (["commercial"], "VAEPX VAEPX - - VX - - - - - - - VAE - - -"),
    (["residential", "transport"], "VX VAEPX VAE VAE V - - - V - VAEP VAEP - O O V"),
    (["equipment", "facility"], "VX VAEPX VAEP VAE V VAE VA VAE - - VA VA - - - V"),
    (["communication"], "VAEPX VAEPX VAE VAE VA VAE VA - VA - VA VA VAE O O V"),
    (["grievance"], "VAEPX VAEPX VAEP VAE V VAEP VA VA VA VA VAE VA V OA OA V"),
    (["reporting"], "VX VX VX VX VX VX V V V V V V VX - - VX"),
    (["iam"], "V VP - - - - - - - - - - - - - VAEPX"),
    (["audit"], "VX VX - - V - - - - - - - - - - VX"),
]


# docs/03-rbac.md: "Print is a distinct verb on `idcard` and `trial` only".
# The VAEPX-style cell letters can't express it — "P" there already means
# Approve — so it's a separate additive grant rather than a MATRIX column.
# `trial`: Administration books/organises, Head Coach and Coach print the
# ground-side trial sheet (docs/05-build-sequence.md T-506), IT Admin per
# its usual view-everywhere role. `idcard`: whoever can issue also prints.
PRINT_ROLES: dict[str, frozenset[str]] = {
    "trial": frozenset({"administration", "head_coach", "coach", "it_admin"}),
    "idcard": frozenset({"administration", "academy_head", "it_admin"}),
}


def parse_cell(cell: str) -> tuple[str, set[str]] | None:
    """ "VAEPX" -> (all, {view,add,edit,approve,export}); "O" -> (own, {view});
    "OA" -> (own, {view, add}); "-" -> None. "O" always implies view, even
    alone — every bare-O cell in the matrix is a read-your-own-record grant.
    """
    if cell == "-":
        return None
    if "O" in cell:
        letters = cell.replace("O", "")
        return Scope.OWN, {Verb.VIEW} | {VERB_LETTERS[ch] for ch in letters}
    return Scope.ALL, {VERB_LETTERS[ch] for ch in cell}


def row_for_module(module: str) -> str | None:
    """The raw cell-string row (ROLE_CODES order) covering `module`, or None
    if docs/03-rbac.md has no row for it at all — used by
    tests/test_permission_matrix.py to fail (not skip) undocumented modules.
    """
    for modules, cell_row in MATRIX:
        if module in modules:
            return cell_row
    return None


def expected_access(module: str, verb: str, role_code: str) -> bool:
    """Does docs/03-rbac.md's matrix grant `role_code` access to
    module+verb? Raises if `module` has no row at all — callers must
    handle that as a failure, not silently treat it as "no access".

    `print` is checked against PRINT_ROLES instead of the row's letters —
    see the comment there — but a module still needs a MATRIX row (even a
    print-only one would, if that ever comes up) to prove it's a
    documented, not guessed-at, module.
    """
    row = row_for_module(module)
    if row is None:
        raise LookupError(f"No docs/03-rbac.md row for module {module!r}")
    if verb == Verb.PRINT:
        return role_code in PRINT_ROLES.get(module, frozenset())
    cell = dict(zip(ROLE_CODES, row.split(), strict=True))[role_code]
    parsed = parse_cell(cell)
    return parsed is not None and verb in parsed[1]


class Command(BaseCommand):
    help = "Seed the 16 SOP roles and the docs/03-rbac.md permission matrix."

    @transaction.atomic
    def handle(self, *args, **options):
        roles = {}
        for code, name in ROLES:
            role, _ = Role.objects.update_or_create(
                code=code, defaults={"name": name, "is_system": True}
            )
            roles[code] = role

        permissions: dict[tuple[str, str], Permission] = {}
        grants = 0

        for modules, cell_row in MATRIX:
            cells = cell_row.split()
            if len(cells) != len(ROLE_CODES):
                raise ValueError(
                    f"Matrix row for {modules} has {len(cells)} cells, expected {len(ROLE_CODES)}"
                )

            for module in modules:
                for role_code, cell in zip(ROLE_CODES, cells, strict=True):
                    parsed = parse_cell(cell)
                    if parsed is None:
                        continue
                    scope, verbs = parsed

                    for verb in verbs:
                        key = (module, verb)
                        if key not in permissions:
                            permissions[key], _ = Permission.objects.update_or_create(
                                module=module, verb=verb
                            )
                        RolePermission.objects.update_or_create(
                            role=roles[role_code],
                            permission=permissions[key],
                            defaults={"scope": scope},
                        )
                        grants += 1

        for module, role_codes in PRINT_ROLES.items():
            key = (module, Verb.PRINT)
            if key not in permissions:
                permissions[key], _ = Permission.objects.update_or_create(
                    module=module, verb=Verb.PRINT
                )
            for role_code in role_codes:
                RolePermission.objects.update_or_create(
                    role=roles[role_code],
                    permission=permissions[key],
                    defaults={"scope": Scope.ALL},
                )
                grants += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(ROLES)} roles, {len(permissions)} permissions, "
                f"{grants} role-permission grants."
            )
        )
