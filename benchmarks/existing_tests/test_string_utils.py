"""Existing (baseline) tests for string_utils. Deliberately partial: the
TestForge agent augments this suite."""
import pytest

from string_utils import mask_email, slugify, truncate_with_ellipsis


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_strips_edges():
    assert slugify("  Hi!  ") == "hi"


def test_slugify_empty():
    assert slugify("") == ""


def test_mask_email_basic():
    assert mask_email("jsmith@example.com") == "j*****@example.com"


def test_mask_email_missing_at_raises():
    with pytest.raises(ValueError):
        mask_email("not-an-email")


def test_truncate_short():
    assert truncate_with_ellipsis("hi", 10) == "hi"


def test_truncate_long():
    assert truncate_with_ellipsis("hello world", 8) == "hello..."
