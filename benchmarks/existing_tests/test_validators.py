"""Existing (baseline) tests for validators. Deliberately partial."""
import pytest

from validators import normalize_hex_color, validate_port, validate_username


def test_username_ok():
    assert validate_username("tom_99") == "tom_99"


def test_username_too_short():
    with pytest.raises(ValueError):
        validate_username("ab")


def test_port_ok():
    assert validate_port(8080) == 8080


def test_port_zero_raises():
    with pytest.raises(ValueError):
        validate_port(0)


def test_hex_expand_short():
    assert normalize_hex_color("#abc") == "#AABBCC"
