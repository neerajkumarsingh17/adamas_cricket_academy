import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from django.db import connection

from apps.core.services.numbering import _financial_year_code, next_number

ENQ_PATTERN = re.compile(r"^ENQ/(\d{4})/(\d{5})$")


def _seq(number: str) -> int:
    match = ENQ_PATTERN.match(number)
    assert match is not None, number
    return int(match.group(2))


@pytest.mark.django_db
def test_next_number_matches_documented_format():
    result = next_number("ENQ")

    match = ENQ_PATTERN.match(result)
    assert match is not None, result
    assert match.group(1) == _financial_year_code()


@pytest.mark.django_db
def test_next_number_increments():
    first = next_number("ENQ")
    second = next_number("ENQ")

    assert _seq(second) == _seq(first) + 1


def test_unknown_series_raises():
    with pytest.raises(ValueError):
        next_number("NOPE")


@pytest.mark.parametrize(
    ("on", "expected"),
    [
        (datetime.date(2026, 4, 1), "2627"),
        (datetime.date(2027, 3, 31), "2627"),
        (datetime.date(2026, 3, 31), "2526"),
    ],
)
def test_financial_year_code(on, expected):
    assert _financial_year_code(on) == expected


@pytest.mark.django_db(transaction=True)
def test_next_number_is_collision_safe_under_concurrency():
    """500 concurrent next_number("ENQ") calls -> 500 distinct numbers,
    no gaps, no duplicates. Proves the PostgreSQL sequence (not
    count() + 1) is what's generating these — CLAUDE.md rule 7.
    """
    call_count = 500

    def call() -> str:
        try:
            return next_number("ENQ")
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(call) for _ in range(call_count)]
        results = [future.result() for future in as_completed(futures)]

    assert len(results) == call_count

    seqs = sorted(_seq(r) for r in results)
    assert len(set(seqs)) == call_count, "duplicate sequence value"
    assert seqs == list(range(seqs[0], seqs[0] + call_count)), "gap in sequence"
