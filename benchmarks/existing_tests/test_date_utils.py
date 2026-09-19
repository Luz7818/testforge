"""Existing (baseline) tests for date_utils. Deliberately partial."""
import pytest

from date_utils import age_in_days, days_in_month, is_leap_year


def test_leap_year_simple():
    assert is_leap_year(2024) is True


def test_leap_year_not():
    assert is_leap_year(2023) is False


def test_leap_year_century_not_div_400():
    assert is_leap_year(1900) is False


def test_days_in_month_feb_leap():
    assert days_in_month(2024, 2) == 29


def test_days_in_month_jan():
    assert days_in_month(2023, 1) == 31


def test_age_in_days_basic():
    assert age_in_days("2024-01-01", "2024-01-31") == 30
