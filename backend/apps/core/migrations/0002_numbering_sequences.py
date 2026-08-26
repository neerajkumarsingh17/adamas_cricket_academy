from django.db import migrations

CREATE_SEQUENCES = """
CREATE SEQUENCE IF NOT EXISTS core_numbering_enq_seq;
CREATE SEQUENCE IF NOT EXISTS core_numbering_trl_seq;
CREATE SEQUENCE IF NOT EXISTS core_numbering_adm_seq;
CREATE SEQUENCE IF NOT EXISTS core_numbering_aca_seq;
"""

DROP_SEQUENCES = """
DROP SEQUENCE IF EXISTS core_numbering_enq_seq;
DROP SEQUENCE IF EXISTS core_numbering_trl_seq;
DROP SEQUENCE IF EXISTS core_numbering_adm_seq;
DROP SEQUENCE IF EXISTS core_numbering_aca_seq;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_postgres_extensions"),
    ]

    operations = [
        migrations.RunSQL(CREATE_SEQUENCES, reverse_sql=DROP_SEQUENCES),
    ]
