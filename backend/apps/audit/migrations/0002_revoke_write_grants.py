"""docs/01-data-model.md section 3: "the application role holds INSERT and
SELECT on audit_auditlog and nothing else."

Best-effort, not a guarantee: in this project's single-role local/dev
setup the connecting database role owns this table (it ran the migration
that created it), and PostgreSQL always lets a table's owner bypass its
own REVOKEs. Real enforcement needs a second, non-owning runtime role in
staging/production — see the long comment on
`apps.audit.models._AppendOnlyQuerySet`, which is the enforcement this
codebase can actually rely on today. This migration is still applied
because it is correct and harmless everywhere, and becomes fully effective
the day that second role exists, with no further code change.
"""

from django.db import migrations

REVOKE_SQL = "REVOKE UPDATE, DELETE ON audit_auditlog FROM PUBLIC;"
# No safe reverse: re-granting would have to know who to grant to. A
# reversible no-op is honest about that rather than guessing a role name.
NOOP_SQL = "SELECT 1;"


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=REVOKE_SQL, reverse_sql=NOOP_SQL),
    ]
