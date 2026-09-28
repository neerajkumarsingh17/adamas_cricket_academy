from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("batch", "0002_alter_trainingsession_training_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="batch",
            name="residential_monthly_fee",
            # Existing batches default to 0.00 until Administration prices
            # them — same "must be set explicitly, not guessed" reasoning
            # as leaving it non-nullable; this default only exists to let
            # the migration apply against rows that predate the field.
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
    ]
