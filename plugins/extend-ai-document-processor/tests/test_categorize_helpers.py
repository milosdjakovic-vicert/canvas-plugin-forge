"""Tests for categorize module helper functions."""

import pytest

from extend_ai_document_processor.categorize import (
    _slugify,
    _build_slug_map,
    _extract_min_confidence,
    _parse_extraction,
)
from extend_ai_document_processor.models import DocumentExtraction


class TestSlugify:
    """Test name slugification."""

    @pytest.mark.parametrize("value,expected", [
        ("Lab Report", "lab_report"),
        ("Imaging Report", "imaging_report"),
        ("CT Scan - Head", "ct_scan_head"),
        ("  spaced  ", "spaced"),
        ("MRI/CT", "mri_ct"),
        ("Test (with parens)", "test_with_parens"),
        ("UPPERCASE", "uppercase"),
        ("a--b", "a_b"),
        ("  ", ""),
        ("123", "123"),
        ("Test & Report", "test_report"),
    ])
    def test_slugification(self, value, expected):
        assert _slugify(value) == expected


class TestBuildSlugMap:
    """Test document type to slug mapping."""

    def test_builds_mapping(self):
        types = [
            {"name": "Lab Report", "key": "lab"},
            {"name": "Imaging Report", "key": "imaging"},
        ]
        result = _build_slug_map(types)

        assert "lab_report" in result
        assert "imaging_report" in result
        assert result["lab_report"]["key"] == "lab"

    def test_skips_duplicates(self):
        types = [
            {"name": "Lab Report", "key": "lab1"},
            {"name": "Lab Report", "key": "lab2"},
        ]
        result = _build_slug_map(types)

        assert len(result) == 1
        assert result["lab_report"]["key"] == "lab1"

    def test_skips_missing_names(self):
        types = [
            {"name": "Lab Report", "key": "lab"},
            {"key": "no_name"},
            {"name": None, "key": "null_name"},
        ]
        result = _build_slug_map(types)

        assert len(result) == 1
        assert "lab_report" in result

    def test_empty_list(self):
        result = _build_slug_map([])
        assert result == {}


class TestExtractMinConfidence:
    """Test OCR confidence extraction."""

    def test_returns_minimum(self):
        metadata = {
            "field1": {"ocrConfidence": 0.95},
            "field2": {"ocrConfidence": 0.85},
            "field3": {"ocrConfidence": 0.90},
        }
        assert _extract_min_confidence(metadata) == 0.85

    def test_single_field(self):
        metadata = {"field1": {"ocrConfidence": 0.95}}
        assert _extract_min_confidence(metadata) == 0.95

    def test_none_when_empty(self):
        assert _extract_min_confidence({}) is None

    def test_none_when_none(self):
        assert _extract_min_confidence(None) is None

    def test_skips_non_dict_values(self):
        metadata = {
            "field1": {"ocrConfidence": 0.95},
            "field2": "not a dict",
            "field3": None,
        }
        assert _extract_min_confidence(metadata) == 0.95

    def test_skips_missing_confidence(self):
        metadata = {
            "field1": {"ocrConfidence": 0.95},
            "field2": {"other": "data"},
        }
        assert _extract_min_confidence(metadata) == 0.95

    def test_handles_int_confidence(self):
        metadata = {"field1": {"ocrConfidence": 1}}
        assert _extract_min_confidence(metadata) == 1.0

    def test_none_when_no_valid_scores(self):
        metadata = {
            "field1": {"other": "data"},
            "field2": "string",
        }
        assert _extract_min_confidence(metadata) is None


class TestParseExtraction:
    """Test extraction data parsing."""

    def test_valid_data(self):
        raw = {
            "document_type": "lab_report",
            "loinc_codes": "11580-8",
            "patient_id": "MRN123",
        }
        result = _parse_extraction(raw)

        assert isinstance(result, DocumentExtraction)
        assert result.document_type == "lab_report"
        assert result.loinc_codes == "11580-8"
        assert result.patient_id == "MRN123"

    def test_extra_fields_preserved(self):
        raw = {
            "document_type": "lab_report",
            "custom_field": "custom_value",
        }
        result = _parse_extraction(raw)

        assert result.document_type == "lab_report"
        assert result.model_extra.get("custom_field") == "custom_value"

    def test_empty_data(self):
        result = _parse_extraction({})

        assert isinstance(result, DocumentExtraction)
        assert result.document_type is None

    def test_handles_invalid_types_gracefully(self):
        raw = {
            "document_type": 123,  # Should be string
            "loinc_codes": {"nested": "object"},
        }
        result = _parse_extraction(raw)

        assert isinstance(result, DocumentExtraction)
