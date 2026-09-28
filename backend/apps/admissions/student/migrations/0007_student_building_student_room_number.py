import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_building"),
        ("student", "0006_alter_student_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="building",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="students",
                to="core.building",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="room_number",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
