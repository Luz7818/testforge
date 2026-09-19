"""Existing (baseline) tests for containers. Deliberately partial."""
import pytest

from containers import chunk, flatten, most_frequent


def test_flatten_nested():
    assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]


def test_flatten_strings_atomic():
    assert flatten(["ab", ["c"]]) == ["ab", "c"]


def test_chunk_even():
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_chunk_uneven():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def test_most_frequent_basic():
    assert most_frequent(["a", "b", "a"]) == "a"
