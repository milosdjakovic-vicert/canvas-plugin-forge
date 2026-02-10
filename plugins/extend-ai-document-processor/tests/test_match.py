"""Tests for patient and reviewer matching module."""

import pytest

from extend_ai_document_processor.match import _parse_full_name


class TestParseFullName:
    """Test name parsing helper."""

    def test_both_provided(self):
        first, last = _parse_full_name("John", "Doe", None)
        assert first == "John"
        assert last == "Doe"

    def test_from_full_name(self):
        first, last = _parse_full_name(None, None, "John Doe")
        assert first == "John"
        assert last == "Doe"

    def test_full_name_with_middle(self):
        first, last = _parse_full_name(None, None, "John Michael Doe")
        assert first == "John"
        assert last == "Doe"

    def test_partial_override(self):
        first, last = _parse_full_name("Jane", None, "John Doe")
        assert first == "Jane"
        assert last == "Doe"

    def test_single_name(self):
        first, last = _parse_full_name(None, None, "John")
        assert first == "John"
        assert last is None

    def test_all_none(self):
        first, last = _parse_full_name(None, None, None)
        assert first is None
        assert last is None
