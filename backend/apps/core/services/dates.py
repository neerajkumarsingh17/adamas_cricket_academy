"""Small date-window helpers shared by seed_demo and the dashboards service,
so "this weekend" means the same two dates in both places."""

import calendar
import datetime


def upcoming_weekend(today: datetime.date) -> tuple[datetime.date, datetime.date]:
    """The nearest Saturday/Sunday from `today`. If `today` is itself a
    Saturday, rolls to *next* week's weekend rather than "today" — this
    keeps "trials booked this weekend" meaningfully forward-looking rather
    than describing a slot that's already underway.
    """
    days_to_saturday = (5 - today.weekday()) % 7
    saturday = today + datetime.timedelta(days=days_to_saturday or 7)
    return saturday, saturday + datetime.timedelta(days=1)


def week_start(today: datetime.date) -> datetime.date:
    """Monday of `today`'s week."""
    return today - datetime.timedelta(days=today.weekday())


def month_start(today: datetime.date) -> datetime.date:
    return today.replace(day=1)


def month_end(today: datetime.date) -> datetime.date:
    return today.replace(day=calendar.monthrange(today.year, today.month)[1])


def last_n_months(today: datetime.date, n: int) -> list[datetime.date]:
    """The 1st of each of the last `n` calendar months, including the
    current one, oldest first — e.g. n=6 in April returns Nov..Apr.
    """
    months = []
    year, month = today.year, today.month
    for _ in range(n):
        months.append(datetime.date(year, month, 1))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    months.reverse()
    return months
