"""Existing (baseline) tests for parsers. Deliberately partial."""
import pytest

from parsers import parse_csv_line, parse_kv_pairs, parse_version


def test_csv_simple():
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_csv_quoted_comma():
    assert parse_csv_line('"x,y",z') == ["x,y", "z"]


def test_csv_escaped_quote():
    assert parse_csv_line('"a""b"') == ['a"b']


def test_version_basic():
    assert parse_version("1.2.3") == (1, 2, 3)


def test_kv_basic():
    assert parse_kv_pairs("a=1, b=2") == {"a": "1", "b": "2"}
