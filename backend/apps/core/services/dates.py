"""Small date-window helpers shared by seed_demo and the dashboards service,
so "this weekend" means the same two dates in both places."""

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
