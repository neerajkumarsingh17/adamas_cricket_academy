"""docs/00-project-structure.md's academics/batch app (M08)."""

import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from .models import Batch, BatchEnrollment, TrainingSession


class BatchFull(APIException):
    status_code = 409
    default_code = "batch_full"
    default_detail = "This batch has no remaining capacity."


class StudentAlreadyEnrolled(APIException):
    status_code = 409
    default_code = "student_already_enrolled"
    default_detail = "This student already has an active batch enrolment."


class BatchAlreadyStarted(APIException):
    status_code = 409
    default_code = "batch_already_started"
    default_detail = "This batch has already started and can no longer be edited or deleted."


class BatchHasEnrollments(APIException):
    status_code = 409
    default_code = "batch_has_enrollments"
    default_detail = "This batch has students enrolled and cannot be deleted."


def _check_capacity(batch: Batch) -> None:
    if batch.enrollments.filter(is_active=True).count() >= batch.capacity:
        raise BatchFull()


@transaction.atomic
def enrol(student, batch: Batch, from_date: datetime.date) -> BatchEnrollment:
    """`select_for_update` on the batch (not a denormalised counter — see
    the model's own docstring) so two admins both reading "24 of 25" and
    both writing can't both succeed; the second writer blocks until the
    first commits, then re-reads a now-full batch.
    """
    batch = Batch.objects.select_for_update().get(pk=batch.pk)
    _check_capacity(batch)
    if BatchEnrollment.objects.filter(student=student, is_active=True).exists():
        raise StudentAlreadyEnrolled()
    return BatchEnrollment.objects.create(student=student, batch=batch, from_date=from_date)


@transaction.atomic
def transfer(
    enrollment: BatchEnrollment, to_batch: Batch, effective_date: datetime.date
) -> BatchEnrollment:
    """Closes the current row, then opens a new one — in that order, one
    transaction. The spec for this function doesn't call out
    select_for_update explicitly the way enrol()'s does, but a transfer is
    another path that adds a student to a batch, so it re-runs the same
    locked capacity check against `to_batch` rather than leaving that
    second path unguarded against the exact overbooking enrol() exists to
    prevent.
    """
    to_batch = Batch.objects.select_for_update().get(pk=to_batch.pk)
    _check_capacity(to_batch)

    enrollment.to_date = effective_date
    enrollment.is_active = False
    enrollment.save(update_fields=["to_date", "is_active", "updated_at"])

    return BatchEnrollment.objects.create(
        student=enrollment.student, batch=to_batch, from_date=effective_date
    )


def assert_batch_editable(batch: Batch) -> None:
    """"Started" means the batch's first real session date has arrived —
    not merely that TrainingSession rows exist, since generate_sessions()
    auto-creates them up to 4 weeks ahead of every active batch regardless
    of whether anyone has edited the batch since. A batch with only
    future-dated sessions is still freely editable/deletable.
    """
    if batch.sessions.filter(date__lte=timezone.localdate()).exists():
        raise BatchAlreadyStarted()


@transaction.atomic
def delete_batch(batch: Batch) -> None:
    assert_batch_editable(batch)
    if batch.enrollments.exists():
        raise BatchHasEnrollments()
    # assert_batch_editable already proved every session on this batch is
    # in the future — these are generate_sessions()'s auto-created
    # placeholders, safe to clear. Required: both BatchEnrollment.batch and
    # TrainingSession.batch are on_delete=PROTECT, so a plain batch.delete()
    # would otherwise raise ProtectedError even on a batch that has
    # genuinely never started.
    batch.sessions.all().delete()
    batch.delete()


def generate_sessions(days: int = 28) -> dict[str, int]:
    """Creates TrainingSession rows from each active batch's `weekdays`
    for the next `days` calendar days. Idempotent by construction: relies
    on the (batch, date) unique constraint and catches IntegrityError per
    attempt rather than checking existence first (get_or_create's usual
    initial SELECT is exactly the "check first" this is told not to do) —
    a deliberate deviation from this codebase's normal idempotency idiom,
    made explicitly for this function.
    """
    today = timezone.localdate()
    created = 0
    skipped = 0

    for batch in Batch.objects.filter(is_active=True):
        weekday_numbers = {int(d) for d in batch.weekdays.split(",") if d.strip()}
        for offset in range(days):
            date = today + datetime.timedelta(days=offset)
            if date.isoweekday() not in weekday_numbers:
                continue
            try:
                with transaction.atomic():
                    TrainingSession.objects.create(
                        batch=batch,
                        date=date,
                        start_time=batch.start_time,
                        end_time=batch.end_time,
                        coach=batch.coach,
                    )
                created += 1
            except IntegrityError:
                skipped += 1

    return {"created": created, "skipped": skipped}
