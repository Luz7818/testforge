"""Calendar helpers in the style of small OSS helper libraries."""

from datetime import date


def is_leap_year(year: int) -> bool:
    """Gregorian leap year rule: divisible by 4, except centuries not
    divisible by 400."""
    if year % 4 != 0:
        return False
    if year % 100 != 0:
        return True
    return year % 400 == 0


_DAYS = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
}


def days_in_month(year: int, month: int) -> int:
    """Number of days in the given month (1-12) of the given year.

    February accounts for leap years. Raise ValueError when month is not
    in 1..12.
    """
    if month < 1 or month > 12:
        raise ValueError("month must be in 1..12")
    if month == 2 and is_leap_year(year):
        return 29
    return _DAYS[month]


def age_in_days(birth: str, today: str) -> int:
    """Whole days between two ISO dates (YYYY-MM-DD), ``birth <= today``.

    Raise ValueError when a date is malformed or birth is after today.
    """
    b = date.fromisoformat(birth)
    t = date.fromisoformat(today)
    if b > t:
        raise ValueError("birth is after today")
    return (t - b).days
