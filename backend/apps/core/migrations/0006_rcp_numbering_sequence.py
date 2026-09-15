from django.db import migrations

CREATE_SEQUENCE = "CREATE SEQUENCE IF NOT EXISTS core_numbering_rcp_seq;"
DROP_SEQUENCE = "DROP SEQUENCE IF EXISTS core_numbering_rcp_seq;"


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_consenttype_feehead_documenttype_required_stage_and_more"),
    ]

    operations = [
        migrations.RunSQL(CREATE_SEQUENCE, reverse_sql=DROP_SEQUENCE),
    ]
