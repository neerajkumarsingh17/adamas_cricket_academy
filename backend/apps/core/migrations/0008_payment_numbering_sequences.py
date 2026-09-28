from django.db import migrations

CREATE_SEQUENCES = """
CREATE SEQUENCE IF NOT EXISTS core_numbering_pcf_seq;
CREATE SEQUENCE IF NOT EXISTS core_numbering_inv_seq;
"""

DROP_SEQUENCES = """
DROP SEQUENCE IF EXISTS core_numbering_pcf_seq;
DROP SEQUENCE IF EXISTS core_numbering_inv_seq;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_paymenttype"),
    ]

    operations = [
        migrations.RunSQL(CREATE_SEQUENCES, reverse_sql=DROP_SEQUENCES),
    ]
