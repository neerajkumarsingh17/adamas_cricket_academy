"""docs/05-build-sequence.md T-701..T-704. `apps.admissions.student` is
allowed to import `apps.admissions.admission` going forward along the
`enquiry -> trial -> admission -> student` chain
(docs/00-project-structure.md) — the reverse is not allowed, which is why
`approve_admission()` (the transition that actually creates a `Student`)
lives here rather than in `apps.admissions.admission`, even though
docs/02-api-spec.md names its URL `/admissions/{id}/approve`.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.admissions.admission.models import Admission, AdmissionSource, AdmissionStep
from apps.admissions.admission.state import AdmissionStateMachine, DirectAdmissionStateMachine
from apps.core.models import ApprovalRequest, ApprovalStatus
from apps.core.services import approvals
from apps.core.services.numbering import next_number
from apps.iam.services import get_or_create_user_for_person
from apps.people.models import Guardian, Person, StudentGuardian
from apps.people.services import (
    normalize_mobile_e164,
    resolve_person,
    resolve_person_by_name,
    split_name,
)

from .models import Student, StudentProfile, StudentStatus, StudentStatusHistory
from .state import APPROVAL_GATED_TARGETS, StudentStatusMachine


@transaction.atomic
def approve_admission(admission: Admission, *, user) -> Student:
    """POST /admissions/{id}/approve — docs/02-api-spec.md: "Creates
    Student, issues student_code." For an admission going through the
    trial-based or old trial-waiver chain (`AdmissionStateMachine`),
    requires an already-*approved* `ApprovalRequest` (created via
    `POST /approvals/{id}/approve`) — this call is the domain-specific act
    of *committing* that decision, mirroring how that machine's own
    `fee_cleared -> approved` guard only checks the approval exists rather
    than deciding it itself. The fee-first direct-admission chain
    (`DirectAdmissionStateMachine`) has no such approval object to check —
    its own guard re-verifies the documents gate directly, and Academy
    Head sign-off is enforced by the `admission.approve` permission on
    this endpoint instead.

    `hasattr(admission, "intake")`, not `source`, is what picks the state
    machine: the pre-existing trial-waiver direct-admission path
    (`open_direct_admission`) also sets `source=DIRECT` but still moves
    through `AdmissionStateMachine`'s own step names via its own
    unchanged endpoints (`/advance`, `/enable-portal`) — only the new
    wizard's `open_direct_admission_intake()` ever creates an
    `AdmissionIntake`, so its presence is the real signal for "this row
    is on the new fee-first chain."
    """
    is_direct = hasattr(admission, "intake")
    machine: DirectAdmissionStateMachine | AdmissionStateMachine = (
        DirectAdmissionStateMachine(admission) if is_direct else AdmissionStateMachine(admission)
    )
    machine.apply(AdmissionStep.APPROVED, user=user)

    approval_request = None
    if not is_direct:
        approval_request = (
            ApprovalRequest.objects.filter(
                content_type=ContentType.objects.get_for_model(Admission),
                object_id=admission.id,
                rule__module="admission",
                rule__action="approve",
                status=ApprovalStatus.APPROVED,
            )
            .order_by("-decided_at")
            .first()
        )

    # `.decided_at` is nullable on the field too (though never actually
    # null once `.status == APPROVED`, which is what got us here) — `or`
    # rather than a plain ternary so the fallback also covers that case,
    # not just "no approval_request at all".
    approved_at = (approval_request.decided_at if approval_request else None) or timezone.now()
    admission.approved_by = approval_request.decided_by if approval_request else user
    admission.approved_at = approved_at
    admission.save(update_fields=["step", "approved_by", "approved_at", "updated_at"])

    if is_direct and admission.person_id is None:
        _resolve_direct_admission_identity(admission)

    # Every source=ENQUIRY admission already has both (open_admission()
    # requires them as arguments); _resolve_direct_admission_identity()
    # above guarantees them for source=DIRECT before this point.
    assert admission.person is not None

    student = Student.objects.create(
        student_code=next_number("ACA"),
        person=admission.person,
        admission=admission,
        admission_date=approved_at.date(),
        programme=admission.programme,
        residential=admission.residential,
        status=StudentStatus.ACTIVE,
    )
    StudentStatusHistory.objects.create(
        student=student,
        from_status="",
        to_status=StudentStatus.ACTIVE,
        reason="Admission approved.",
        changed_by=user,
        approval=approval_request,
    )

    if is_direct:
        _link_direct_admission_guardian(admission, student)

    _notify_training_activation(student)

    return student


def _resolve_direct_admission_identity(admission: Admission) -> None:
    """The one place a direct admission's Person gets resolved or created
    — CLAUDE.md rule 1: never without resolve_person() checking for a
    duplicate first. A returning candidate (same name, DOB, guardian
    mobile as a prior enrolment) keeps their existing Person; this is the
    single most important behaviour in the whole direct-admission feature.
    """
    intake = admission.intake
    match = resolve_person_by_name(
        full_name=intake.full_name,
        date_of_birth=intake.date_of_birth,
        guardian_mobile=intake.guardian_mobile,
    )
    if match.exact:
        person = match.exact[0]
    else:
        first_name, last_name = split_name(intake.full_name)
        person = Person.objects.create(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=intake.date_of_birth,
            gender=intake.gender,
            # A minor's own mobile is optional on intake — the guardian's
            # is the fallback, same convention the trial-based chain uses.
            mobile=intake.student_mobile or intake.guardian_mobile,
            address_line1=intake.present_address[:255],
            city=intake.city,
            state=intake.state,
            pincode=intake.pin_code,
        )

    admission.person = person
    admission.save(update_fields=["person", "updated_at"])


def _link_direct_admission_guardian(admission: Admission, student: Student) -> None:
    """AdmissionIntake now collects guardian_date_of_birth/guardian_gender
    alongside guardian_name/guardian_mobile, so — like
    _resolve_direct_admission_identity() above — the guardian's Person goes
    through the same resolve_person_by_name() dedupe as the student's,
    instead of a mobile-only lookup that could only reuse an existing
    Person and had no way to create a genuinely new one (CLAUDE.md rule 1:
    never create a Person without resolve_person() checking first; a
    first-time family has no prior guardian Person to find).
    """
    intake = admission.intake
    # Nullable on the model only for migration safety (see AdmissionIntake's
    # own comment) — state.py's _guard_ready_for_payment already ran
    # intake.clean() before this admission could leave DRAFT, and every
    # later PATCH re-runs it too, so it's never actually blank by the time
    # a direct admission reaches approval.
    assert intake.guardian_date_of_birth is not None
    match = resolve_person_by_name(
        full_name=intake.guardian_name,
        date_of_birth=intake.guardian_date_of_birth,
        guardian_mobile=intake.guardian_mobile,
    )
    exact = [person for person in match.exact if person.pk != student.person_id]
    if exact:
        guardian_person = exact[0]
    else:
        first_name, last_name = split_name(intake.guardian_name)
        guardian_person = Person.objects.create(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=intake.guardian_date_of_birth,
            gender=intake.guardian_gender,
            mobile=intake.guardian_mobile,
            address_line1=intake.present_address[:255],
            city=intake.city,
            state=intake.state,
            pincode=intake.pin_code,
        )

    guardian, _ = Guardian.objects.get_or_create(person=guardian_person)
    StudentGuardian.objects.create(
        student=student,
        guardian=guardian,
        relationship=intake.guardian_relationship,
        is_primary=True,
    )


def _notify_training_activation(student: Student) -> None:
    """docs/04-state-machines.md section 1, SOP step 13: "Domain event
    student.activated -> schedule notification to parent." Phase 2 (batch/
    training) doesn't exist yet to listen for a real event bus message, so
    this sends the notification directly — the same outcome the event is
    documented to produce, without inventing an event-bus mechanism this
    phase has no other consumer for.
    """
    from apps.engagement.communication.services import NoActiveTemplate
    from apps.engagement.communication.services import send as send_notification

    try:
        send_notification(
            code="training_activation",
            recipient=student.person.mobile,
            context={
                "student_code": student.student_code,
                # A direct-admission student has no programme yet — batch
                # allotment assigns one afterward (see Student.programme's
                # docstring) — so this can't assume one exists here.
                "programme": student.programme.name if student.programme else "your programme",
            },
        )
    except NoActiveTemplate:
        pass


@transaction.atomic
def re_admit(*, person, programme, requested_by, residential: bool = False) -> Student:
    """docs/02-api-spec.md: "POST /students/re-admission ... Refuses to
    create a second Person." docs/04-state-machines.md section 5: a *new*
    `Student` row against the *same* `Person`; the prior row keeps its
    `withdrawn` status and full history untouched.

    Bypasses the normal enquiry/trial/admission-approval chain by design —
    SOP §67 treats a returning student as a known quantity, not a fresh
    applicant — but still opens a real `Admission` row (`step=approved`
    directly) so the student's second enrolment has the same paper trail
    shape as the first, rather than a `Student` with no `Admission` behind
    it that every other view assumes exists.
    """
    if Student.objects.filter(person=person, status=StudentStatus.WITHDRAWN).count() == 0:
        raise ValidationError(
            {"person": "This person has no prior withdrawn enrolment to re-admit from."}
        )

    admission = Admission.objects.create(
        application_no=next_number("ADM"),
        # Neither an enquiry nor a trial precedes a re-admission (SOP §67)
        # — DIRECT is the closer fit of the two sources the CheckConstraint
        # allows, even though this bypasses the direct-admission wizard
        # entirely too (goes straight to `approved`, not through
        # DirectAdmissionStateMachine).
        source=AdmissionSource.DIRECT,
        person=person,
        programme=programme,
        residential=residential,
        step=AdmissionStep.APPROVED,
        approved_by=requested_by,
    )
    admission.approved_at = timezone.now()
    admission.save(update_fields=["approved_at"])

    student = Student.objects.create(
        student_code=next_number("ACA"),
        person=person,
        admission=admission,
        admission_date=admission.approved_at.date(),
        programme=programme,
        residential=residential,
        status=StudentStatus.ACTIVE,
    )
    StudentStatusHistory.objects.create(
        student=student,
        from_status="",
        to_status=StudentStatus.ACTIVE,
        reason="Re-admission (SOP §67) — same Person, new enrolment.",
        changed_by=requested_by,
    )
    return student


def change_status(student: Student, *, to_status: str, reason: str, user) -> dict:
    """POST /students/{id}/status — docs/02-api-spec.md: "Some transitions
    raise an approval." For `suspended`/`withdrawn`, the first call (while
    no *approved* request yet exists) creates the `ApprovalRequest` and
    returns without changing status; once an authorised approver has
    decided it via `POST /approvals/{id}/approve`, calling this endpoint
    again with the same `to_status` completes the transition — the same
    two-step shape `apps.admissions.student.services.approve_admission`
    uses for `Admission`.
    """
    machine = StudentStatusMachine(student)

    if to_status in APPROVAL_GATED_TARGETS:
        transition = machine.transition_for(to_status)
        if transition is None:
            # No matching transition from the current state — apply()
            # always raises the real InvalidTransition (409) in this case;
            # let it, rather than special-casing "invalid" here too.
            machine.apply(to_status, user=user, reason=reason)
            raise AssertionError("apply() must have raised for a missing transition")

        assert transition.guard is not None, (
            f"{to_status!r} is APPROVAL_GATED_TARGETS but its Transition has no guard"
        )
        if not transition.guard(student):
            pending = ApprovalRequest.objects.filter(
                content_type=ContentType.objects.get_for_model(Student),
                object_id=student.id,
                rule__module="students",
                rule__action=to_status,
                status=ApprovalStatus.PENDING,
            ).first()
            if pending is None:
                if transition.roles is not None:
                    held = {role.code for role in user.current_roles()}
                    if not held & transition.roles:
                        raise PermissionDenied(
                            "Your role is not permitted to request this transition."
                        )
                if not reason:
                    raise ValidationError(
                        {"reason": "A reason is required to request this transition."}
                    )
                try:
                    pending = approvals.request(student, "students", to_status, user)
                except approvals.NoApprovalRuleConfigured as exc:
                    raise ValidationError({"detail": str(exc)}) from None
            return {"pending_approval": True, "approval_request_id": pending.id}

    approval_request = None
    if to_status in APPROVAL_GATED_TARGETS:
        approval_request = (
            ApprovalRequest.objects.filter(
                content_type=ContentType.objects.get_for_model(Student),
                object_id=student.id,
                rule__module="students",
                rule__action=to_status,
                status=ApprovalStatus.APPROVED,
            )
            .order_by("-decided_at")
            .first()
        )

    from_status = student.status
    machine.apply(to_status, user=user, reason=reason)
    student.save(update_fields=["status", "updated_at"])
    StudentStatusHistory.objects.create(
        student=student,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        changed_by=user,
        approval=approval_request,
    )
    return {"pending_approval": False, "student": student}


def composite_profile(student: Student) -> dict:
    """GET /students/{id} — docs/02-api-spec.md: "Composite profile:
    Personal, Parent, Cricket, Academy... loads from one request"
    (docs/05-build-sequence.md T-703). "Cricket" fields are Phase 2+
    (batch/coach/performance) and don't exist yet — that tab is
    necessarily empty in Phase 1, not fabricated.
    """
    from apps.people.serializers import PersonSerializer

    guardians = StudentGuardian.objects.filter(student=student).select_related("guardian__person")
    return {
        "personal": PersonSerializer(student.person).data,
        "parent": [
            {
                "id": sg.id,
                "guardian_id": sg.guardian_id,
                "relationship": sg.relationship,
                "is_primary": sg.is_primary,
                "is_emergency_contact": sg.is_emergency_contact,
                "person": PersonSerializer(sg.guardian.person).data,
            }
            for sg in guardians
        ],
        "cricket": {},
        "academy": {
            "student_code": student.student_code,
            # None until Head Coach batch allotment for a direct-admission
            # student — the frontend renders that as "not yet assigned".
            "programme": student.programme.name if student.programme else None,
            "admission_date": student.admission_date,
            "residential": student.residential,
            "status": student.status,
        },
    }


@transaction.atomic
def link_guardian(
    student: Student,
    *,
    person_id: str | None = None,
    new_person: dict | None = None,
    relationship: str,
    is_primary: bool = False,
    is_emergency_contact: bool = False,
    grant_portal_access: bool = True,
) -> StudentGuardian:
    """The management side of the read-only "parent" tab
    `composite_profile()` already renders — `StudentGuardian` previously
    had no API-reachable way to be created at all, only Django admin.

    Either `person_id` (an existing Person, e.g. picked from
    `/persons/search/`, or a sibling's already-registered guardian) or
    `new_person` (fresh identity fields) must be given, never both — the
    serializer enforces that split so this function can trust its inputs.
    """
    if person_id is not None:
        person = get_object_or_404(Person, pk=person_id)
    else:
        assert new_person is not None
        # CLAUDE.md rule 1: no Person is created without resolve_person()
        # checking for a duplicate first (SOP §78) — the same pattern
        # apps.admissions.trial.services._resolve_or_create_person uses.
        match = resolve_person(
            {
                "first_name": new_person["first_name"],
                "last_name": new_person["last_name"],
                "date_of_birth": new_person["date_of_birth"],
                "guardian_mobile": new_person["mobile"],
            }
        )
        if match.exact:
            person = match.exact[0]
        else:
            person = Person.objects.create(
                first_name=new_person["first_name"],
                last_name=new_person["last_name"],
                date_of_birth=new_person["date_of_birth"],
                gender=new_person["gender"],
                mobile=new_person["mobile"],
                email=new_person.get("email", ""),
                address_line1="",
                address_line2="",
                city="",
                state="",
                pincode="",
            )

    if person.id == student.person_id:
        raise ValidationError({"person_id": "A student cannot be their own guardian."})

    guardian, _ = Guardian.objects.get_or_create(person=person)

    try:
        student_guardian = StudentGuardian.objects.create(
            student=student,
            guardian=guardian,
            relationship=relationship,
            is_primary=is_primary,
            is_emergency_contact=is_emergency_contact,
        )
    except DjangoValidationError as exc:
        # StudentGuardian.save() calls full_clean() itself (the
        # one-primary-guardian guard) — this is the first API-reachable
        # caller of that path, so this is where Django's ValidationError
        # needs translating into DRF's or it would 500 instead of 400.
        errors = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        raise ValidationError(errors) from exc

    if grant_portal_access:
        guardian.portal_access = True
        guardian.save(update_fields=["portal_access"])
        get_or_create_user_for_person(person, role_code="parent")

    return student_guardian


def unlink_guardian(student: Student, guardian_link_id: str) -> None:
    student_guardian = get_object_or_404(StudentGuardian, pk=guardian_link_id, student=student)
    student_guardian.delete()


def grant_student_login(student: Student, *, mobile: str | None = None) -> tuple:
    """POST /students/{id}/login-access — deliberately not automatic at
    `approve_admission()` time (see apps.admissions.trial.services.
    _resolve_or_create_person: a candidate's own Person.mobile is set to
    their *guardian's* mobile at trial-registration, since a minor usually
    doesn't have their own phone yet). Provisioning a login immediately on
    approval would collide with the guardian's own login for that same
    number in `get_or_create_user_for_person`'s uniqueness guard — this
    action lets Administration supply the student's own distinct number
    first, whenever that becomes available, rather than failing silently
    or blocking approval on a phone number Phase 1 has no other source for.

    Returns `(user, created)`.
    """
    person = student.person
    if mobile:
        person.mobile = normalize_mobile_e164(mobile)
        person.save(update_fields=["mobile", "dedupe_key"])
    return get_or_create_user_for_person(person, role_code="student")


# ---------------------------------------------------------------------- #
# Profile completion (Prompt G, student/parent side) — the offline form's
# deferred 33 fields, minus the three coach-assessed and three
# office-assigned ones (not modelled yet; see StudentProfile's docstring).
# ---------------------------------------------------------------------- #

_PROFILE_DOCUMENT_CODES = [
    "address_proof",
    "school_id",
    "previous_cricket_records",
    "second_passport_photo",
]


def _profile_field_status(student: Student) -> list[tuple[str, str, bool]]:
    """[(field_name, label, is_filled), ...] in the order a desk would
    naturally chase them. `aadhaar_number` is the one field the spec says
    to never chase — deliberately excluded from this list entirely rather
    than always marked "filled", so it affects neither the percentage nor
    ever surfaces as "the next field".
    """
    profile = getattr(student, "profile", None)
    person = student.person
    is_residential = student.residential

    def v(field: str) -> str:
        return getattr(profile, field, "") if profile else ""

    fields: list[tuple[str, str, bool]] = [
        ("blood_group", "blood group", bool(person.blood_group)),
        ("student_email", "student email", bool(person.email)),
        ("nationality", "nationality", bool(v("nationality"))),
        ("permanent_address", "permanent address", bool(v("permanent_address"))),
        ("occupation", "guardian's occupation", bool(v("occupation"))),
        ("annual_income", "annual income", bool(v("annual_income"))),
        ("guardian_email", "guardian email", bool(v("guardian_email"))),
        ("second_guardian", "second guardian", bool(v("second_guardian"))),
        ("school_name", "school name", bool(v("school_name"))),
        ("board", "board", bool(v("board"))),
        ("class_or_course", "class or course", bool(v("class_or_course"))),
        ("medium_of_instruction", "medium of instruction", bool(v("medium_of_instruction"))),
        ("academic_session", "academic session", bool(v("academic_session"))),
        (
            "playing_experience_years",
            "playing experience",
            profile is not None and profile.playing_experience_years is not None,
        ),
        ("previous_academy", "previous academy", bool(v("previous_academy"))),
        ("achievements", "achievements", bool(v("achievements"))),
        ("allergies", "allergies", bool(v("allergies"))),
        ("existing_conditions", "existing conditions", bool(v("existing_conditions"))),
        ("past_injuries", "past injuries", bool(v("past_injuries"))),
        ("family_doctor_contact", "family doctor contact", bool(v("family_doctor_contact"))),
    ]
    if is_residential:
        fields += [
            ("food_preference", "food preference", bool(v("food_preference"))),
            ("room_preference", "room preference", bool(v("room_preference"))),
            (
                "local_guardian_address",
                "local guardian address",
                bool(v("local_guardian_address")),
            ),
        ]

    from apps.admissions.document.models import Document, DocumentStatus
    from apps.core.models import DocumentType

    uploaded_codes = set(
        Document.objects.filter(
            document_type__code__in=_PROFILE_DOCUMENT_CODES,
            owner_content_type__model="student",
            owner_object_id=student.id,
            status__in=[DocumentStatus.SUBMITTED, DocumentStatus.VERIFIED],
        ).values_list("document_type__code", flat=True)
    )
    doc_labels = dict(
        DocumentType.objects.filter(code__in=_PROFILE_DOCUMENT_CODES).values_list("code", "name")
    )
    for code in _PROFILE_DOCUMENT_CODES:
        fields.append((code, doc_labels.get(code, code).lower(), code in uploaded_codes))

    return fields


def profile_completeness(student: Student) -> dict:
    """{"percent": int, "next_field": str | None} — a specific next field
    to chase, not a bare percentage (Prompt G: "'add a blood group' is
    actionable, '68% complete' is not").
    """
    fields = _profile_field_status(student)
    filled = sum(1 for _, _, is_filled in fields if is_filled)
    total = len(fields)
    percent = round((filled / total) * 100) if total else 100
    next_field = next((label for _, label, is_filled in fields if not is_filled), None)
    return {"percent": percent, "next_field": next_field}


def get_or_create_profile(student: Student) -> StudentProfile:
    profile, _ = StudentProfile.objects.get_or_create(student=student)
    return profile


def update_profile(
    student: Student, *, profile_fields: dict, person_fields: dict
) -> StudentProfile:
    """PATCH /students/{id}/profile/ — `person_fields` covers blood_group/
    email specifically (see StudentProfile's docstring: both already live
    on Person, captured once there rather than duplicated).
    """
    profile = get_or_create_profile(student)
    if profile_fields:
        for field, value in profile_fields.items():
            setattr(profile, field, value)
        profile.save()
    if person_fields:
        person = student.person
        for field, value in person_fields.items():
            setattr(person, field, value)
        person.save(update_fields=[*person_fields.keys(), "updated_at"])
    return profile
