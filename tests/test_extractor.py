"""Numara ayıklama kuralları testleri."""

import pytest

from forklift_barcode.config import ExtractionConfig
from forklift_barcode.processing.extractor import Extractor


def make(**kw):
    return Extractor(ExtractionConfig(**kw))


def test_full_returns_whole_barcode():
    ex = make(mode="full")
    assert ex.extract("PLT0012345678TR") == "PLT0012345678TR"


def test_full_with_digits_only():
    ex = make(mode="full", digits_only=True)
    assert ex.extract("PLT0012345678TR") == "0012345678"


def test_slice_basic():
    ex = make(mode="slice", start=1, length=5)
    assert ex.extract("1234567890") == "12345"


def test_slice_middle():
    """Barkodun ortasındaki numara: 6. karakterden 4 karakter."""
    ex = make(mode="slice", start=6, length=4)
    assert ex.extract("PALET12345678") == "1234"


def test_slice_beyond_end_returns_short_or_none():
    ex = make(mode="slice", start=8, length=10, min_length=10)
    assert ex.extract("KISA") is None


def test_digits_only_before_slice():
    ex = make(mode="slice", start=1, length=6, digits_only=True)
    assert ex.extract("AB-12CD34EF56") == "123456"


def test_regex_group():
    ex = make(mode="regex", regex=r"PLT(\d+)", regex_group=1)
    assert ex.extract("PLT00012345-TR") == "00012345"


def test_regex_no_match_returns_none():
    ex = make(mode="regex", regex=r"^\d{20}$")
    assert ex.extract("ABC") is None


def test_regex_last_digits():
    ex = make(mode="regex", regex=r"(\d{8})$", regex_group=1)
    assert ex.extract("003400123456789099887766") == "99887766"


def test_min_length_enforced():
    ex = make(mode="slice", start=1, length=10, min_length=5)
    assert ex.extract("123") is None
    assert ex.extract("12345") == "12345"
