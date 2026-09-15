"""next_number(series, **ctx) — docs/01-data-model.md section 6.

Each series is backed by its own PostgreSQL sequence (created in migration
0002_numbering_sequences), so `nextval()` is atomic under concurrency —
never `Model.objects.count() + 1`, which races.

ID Card numbering (`{student_code}-{issue_seq}`) is scoped per student, not
a flat series, so it isn't part of this registry — the idcard app (T-801)
handles it with its own counter, once it exists.
"""

import datetime
from typing import NamedTuple

from django.db import connection


class _SeriesConfig(NamedTuple):
    sequence: str
    digits: int


SERIES_FORMATS: dict[str, _SeriesConfig] = {
    "ENQ": _SeriesConfig("core_numbering_enq_seq", 5),
    "TRL": _SeriesConfig("core_numbering_trl_seq", 5),
    "ADM": _SeriesConfig("core_numbering_adm_seq", 5),
    "ACA": _SeriesConfig("core_numbering_aca_seq", 4),
    "RCP": _SeriesConfig("core_numbering_rcp_seq", 5),
}


def _financial_year_code(on: datetime.date | None = None) -> str:
    """2026-04-01..2027-03-31 -> "2627" (Indian financial year, April-March)."""
    on = on or datetime.date.today()
    start_year = on.year if on.month >= 4 else on.year - 1
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def next_number(series: str, **ctx: object) -> str:
    """Return the next number in `series`, e.g. next_number("ENQ") -> "ENQ/2627/00142"."""
    try:
        config = SERIES_FORMATS[series]
    except KeyError:
        raise ValueError(f"Unknown numbering series: {series!r}") from None

    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [config.sequence])
        seq = cursor.fetchone()[0]

    year_code = _financial_year_code()
    return f"{series}/{year_code}/{seq:0{config.digits}d}"
