"""Tests for template field extraction functions."""

import pytest

from extend_ai_document_processor.prefill.extraction import (
    _normalize_value,
    _field_key,
)


class TestNormalizeValue:
    """Test value normalization."""

    @pytest.mark.parametrize("value,expected", [
        (None, None),
        ("text", "text"),
        ("  spaced  ", "spaced"),
        ("", None),
        ([], None),
        (["a", "b"], "a, b"),
        (["single"], "single"),
        ({"value": "nested"}, "nested"),
        ({"value": "  spaced  "}, "spaced"),
        ({"value": None}, None),
        ({"other": "key"}, "{'other': 'key'}"),
        (123, "123"),
        ([None, "a", "", "b"], "a, b"),
        ({"value": ["a", "b"]}, "a, b"),
    ])
    def test_normalization(self, value, expected):
        assert _normalize_value(value) == expected


class TestFieldKey:
    """Test field key generation."""

    def test_valid_code(self):
        class MockField:
            code = "11580-8"
            label = "Test Name"

        assert _field_key(MockField()) == "11580-8"

    def test_code_with_whitespace(self):
        class MockField:
            code = "  11580-8  "
            label = "Test Name"

        assert _field_key(MockField()) == "11580-8"

    def test_invalid_code_falls_back_to_label(self):
        class MockField:
            code = "N/A"
            label = "Test Name"

        assert _field_key(MockField()) == "Test Name"

    def test_empty_code_falls_back_to_label(self):
        class MockField:
            code = ""
            label = "Test Name"

        assert _field_key(MockField()) == "Test Name"

    def test_none_code_falls_back_to_label(self):
        class MockField:
            code = None
            label = "Test Name"

        assert _field_key(MockField()) == "Test Name"

    def test_both_none_returns_none(self):
        class MockField:
            code = None
            label = None

        assert _field_key(MockField()) is None

    def test_both_empty_returns_none(self):
        class MockField:
            code = ""
            label = "  "

        assert _field_key(MockField()) is None

    def test_missing_attributes(self):
        class MockField:
            pass

        assert _field_key(MockField()) is None

    def test_label_with_whitespace(self):
        class MockField:
            code = None
            label = "  Test Name  "

        assert _field_key(MockField()) == "Test Name"
