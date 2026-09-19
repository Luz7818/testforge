"""Existing (baseline) tests for numeric. Deliberately partial."""
import pytest

from numeric import clamp, integer_sqrt, moving_average


def test_clamp_inside():
    assert clamp(5, 0, 10) == 5


def test_clamp_low():
    assert clamp(-1, 0, 10) == 0


def test_clamp_high():
    assert clamp(11, 0, 10) == 10


def test_isqrt_interior():
    assert integer_sqrt(8) == 2


def test_isqrt_perfect_square():
    assert integer_sqrt(16) == 4


def test_moving_average_basic():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]
