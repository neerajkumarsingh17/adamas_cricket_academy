from django.db import migrations, models


def backfill_source_and_reason(apps, schema_editor):
    """Every existing row was created before `source` existed — 0006 gave
    them all the blanket default 'enquiry', which is wrong for any row
    that actually has no `enquiry` (the pre-existing direct-admission and
    re-admission rows). Fix those to source='direct', and copy
    trial_waiver_reason's text across before 0008 drops that column —
    losing an already-recorded traceability reason on migration would be
    exactly the kind of silent data loss CLAUDE.md rule 7 warns about.

    Kept in its own migration, separate from 0008's ALTER TABLE operations
    (RemoveField/AddConstraint) — Postgres refuses to ALTER TABLE while a
    deferred FK constraint trigger event from this UPDATE is still pending
    in the same transaction; a fresh migration means a fresh, committed
    transaction by the time 0008 runs.
    """
    Admission = apps.get_model("admission", "Admission")
    Admission.objects.filter(enquiry__isnull=True).update(source="direct")
    Admission.objects.exclude(trial_waiver_reason="").update(
        direct_admission_reason=models.F("trial_waiver_reason")
    )


def noop_reverse(apps, schema_editor):
    # trial_waiver_reason/trial_waiver_approval no longer exist to reverse
    # into once 0008 has run forward past its RemoveField — a real
    # reversal would need those columns back first. Nothing else here
    # needs undoing (the source/reason backfill is idempotent data, not a
    # structural change).
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("admission", "0006_admissionintake_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_source_and_reason, noop_reverse),
    ]
