from django.db import migrations, models


class Migration(migrations.Migration):
    """Safe to drop trial_waiver_reason/trial_waiver_approval and enforce
    the source/enquiry/trial_registration CheckConstraint now — 0007
    already committed the backfill that makes every existing row comply.
    """

    dependencies = [
        ("admission", "0007_backfill_source_and_reason"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="admission",
            name="trial_waiver_approval",
        ),
        migrations.RemoveField(
            model_name="admission",
            name="trial_waiver_reason",
        ),
        migrations.AddConstraint(
            model_name="admission",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("enquiry__isnull", False), ("source", "enquiry")),
                    models.Q(
                        ("enquiry__isnull", True),
                        ("source", "direct"),
                        ("trial_registration__isnull", True),
                    ),
                    _connector="OR",
                ),
                name="admission_source_matches_enquiry_and_trial",
            ),
        ),
    ]
