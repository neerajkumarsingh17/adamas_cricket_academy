import pytest

from apps.admissions.admission import services
from apps.core.tests.factories import ConsentTypeFactory

from .factories import DirectAdmissionFactory


@pytest.mark.django_db
def test_admission_cannot_advance_with_a_mandatory_consent_ungranted():
    admission = DirectAdmissionFactory()
    medical = ConsentTypeFactory(code="medical_emergency", is_mandatory=True)
    ConsentTypeFactory(code="fee_policy", is_mandatory=True)

    services.record_consents(
        admission,
        decisions=[{"consent_type": medical, "granted": True}],
        declared_by_name="Guardian Name",
    )
    # fee_policy (the other mandatory type) was never decided at all.

    assert services.mandatory_consents_granted(admission) is False


@pytest.mark.django_db
def test_admission_can_advance_with_every_mandatory_consent_granted():
    admission = DirectAdmissionFactory()
    medical = ConsentTypeFactory(code="medical_emergency", is_mandatory=True)
    fee_policy = ConsentTypeFactory(code="fee_policy", is_mandatory=True)

    services.record_consents(
        admission,
        decisions=[
            {"consent_type": medical, "granted": True},
            {"consent_type": fee_policy, "granted": True},
        ],
        declared_by_name="Guardian Name",
    )

    assert services.mandatory_consents_granted(admission) is True


@pytest.mark.django_db
def test_admission_can_advance_with_media_use_refused():
    admission = DirectAdmissionFactory()
    medical = ConsentTypeFactory(code="medical_emergency", is_mandatory=True)
    media_use = ConsentTypeFactory(code="media_use", is_mandatory=False)

    services.record_consents(
        admission,
        decisions=[
            {"consent_type": medical, "granted": True},
            {"consent_type": media_use, "granted": False},
        ],
        declared_by_name="Guardian Name",
    )

    assert services.mandatory_consents_granted(admission) is True
    record = admission.consent_records.get(consent_type=media_use)
    assert record.granted is False


@pytest.mark.django_db
def test_consent_version_is_copied_at_grant_time_not_looked_up_live():
    admission = DirectAdmissionFactory()
    consent_type = ConsentTypeFactory(version="1.0")

    services.record_consents(
        admission,
        decisions=[{"consent_type": consent_type, "granted": True}],
        declared_by_name="Guardian Name",
    )

    consent_type.version = "2.0"
    consent_type.save()

    record = admission.consent_records.get(consent_type=consent_type)
    assert record.version == "1.0"


@pytest.mark.django_db
def test_media_use_can_be_revoked_later_without_touching_admission_step():
    admission = DirectAdmissionFactory()
    media_use = ConsentTypeFactory(code="media_use", is_mandatory=False)

    services.record_consents(
        admission,
        decisions=[{"consent_type": media_use, "granted": True}],
        declared_by_name="Guardian Name",
    )
    step_before = admission.step

    services.record_consents(
        admission,
        decisions=[{"consent_type": media_use, "granted": False}],
        declared_by_name="Guardian Name",
    )

    admission.refresh_from_db()
    assert admission.step == step_before
    assert admission.consent_records.get(consent_type=media_use).granted is False
