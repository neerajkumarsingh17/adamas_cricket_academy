"""CLAUDE.md rule 4: "Audit is automatic ... Never write manual audit
calls." These tests exercise the signal wiring in apps.audit.signals
directly against a real AuditedModel (apps.core.models.Programme), rather
than mocking anything, since the whole point is that no view/service code
has to know auditing is happening.
"""

import pytest

from apps.audit.models import AuditAction, AuditLog
from apps.core.models import Programme


@pytest.mark.django_db
def test_create_writes_a_create_row_with_no_before_state():
    programme = Programme.objects.create(code="junior", name="Junior")

    log = AuditLog.objects.get(model_label="core.Programme", object_id=str(programme.pk))
    assert log.action == AuditAction.CREATE
    assert log.changes["name"] == {"from": None, "to": "Junior"}
    assert log.changes["code"] == {"from": None, "to": "junior"}


@pytest.mark.django_db
def test_update_writes_only_the_changed_fields():
    programme = Programme.objects.create(code="junior", name="Junior")

    programme.name = "Junior Development"
    programme.save()

    logs = AuditLog.objects.filter(
        model_label="core.Programme", object_id=str(programme.pk), action=AuditAction.UPDATE
    )
    assert logs.count() == 1
    log = logs.get()
    assert log.changes == {"name": {"from": "Junior", "to": "Junior Development"}}


@pytest.mark.django_db
def test_update_with_no_actual_change_writes_nothing():
    programme = Programme.objects.create(code="junior", name="Junior")
    before_count = AuditLog.objects.count()

    programme.save()  # no field changed

    assert AuditLog.objects.count() == before_count


@pytest.mark.django_db
def test_delete_writes_a_delete_row():
    programme = Programme.objects.create(code="junior", name="Junior")
    pk = str(programme.pk)

    programme.delete()

    log = AuditLog.objects.get(
        model_label="core.Programme", object_id=pk, action=AuditAction.DELETE
    )
    assert log.changes["name"] == {"from": "Junior", "to": None}


@pytest.mark.django_db
def test_create_with_a_time_field_serializes_correctly():
    """Regression: datetime.time isn't a datetime.date subclass, so an
    earlier version of _json_safe() missed it and crashed on the first
    audited model with a bare TimeField (TrialSlot.reporting_time).
    """
    import datetime as dt

    from apps.admissions.trial.tests.factories import TrialSlotFactory

    slot = TrialSlotFactory(reporting_time=dt.time(7, 30))

    log = AuditLog.objects.get(model_label="trial.TrialSlot", object_id=str(slot.pk))
    assert log.changes["reporting_time"]["to"] == "07:30:00"


@pytest.mark.django_db
def test_audit_log_is_append_only():
    programme = Programme.objects.create(code="junior", name="Junior")
    log = AuditLog.objects.get(model_label="core.Programme", object_id=str(programme.pk))

    with pytest.raises(TypeError):
        log.action = AuditAction.UPDATE
        log.save()

    with pytest.raises(TypeError):
        log.delete()

    with pytest.raises(TypeError):
        AuditLog.objects.filter(pk=log.pk).update(action=AuditAction.DELETE)

    with pytest.raises(TypeError):
        AuditLog.objects.filter(pk=log.pk).delete()
