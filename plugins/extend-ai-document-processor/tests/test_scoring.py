"""Tests for template scoring functions."""

import pytest

from extend_ai_document_processor.models import DocumentExtraction
from extend_ai_document_processor.prefill.scoring import (
    is_valid_code,
    extract_codes,
    extract_keywords,
    _to_list,
    _keyword_bonus,
)


class TestIsValidCode:
    """Test code validation."""

    @pytest.mark.parametrize("code,expected", [
        ("11580-8", True),
        ("SNOMED-123", True),
        ("abc123", True),
        ("", False),
        (None, False),
        ("N/A", False),
        ("NA", False),
        ("NONE", False),
        ("  ", False),
        ("n/a", False),
        ("na", False),
        ("none", False),
        ("  N/A  ", False),
    ])
    def test_validation(self, code, expected):
        # Use bool() since function returns truthy/falsy values, not strict booleans
        assert bool(is_valid_code(code)) == expected


class TestToList:
    """Test value to list conversion."""

    @pytest.mark.parametrize("value,expected", [
        (None, []),
        ("single", ["single"]),
        ("a, b, c", ["a", "b", "c"]),
        ("a; b; c", ["a", "b", "c"]),
        ("a\nb\nc", ["a", "b", "c"]),
        (["a", "b"], ["a", "b"]),
        (["a, b", "c"], ["a", "b", "c"]),
        ("  spaced  ", ["spaced"]),
        ("", []),
        (123, ["123"]),
    ])
    def test_conversion(self, value, expected):
        assert _to_list(value) == expected


class TestExtractCodes:
    """Test code extraction by template type."""

    def test_lab_extracts_loinc_codes(self):
        extraction = DocumentExtraction(loinc_codes="11580-8, 3016-3")
        codes = extract_codes("LabReportTemplate", extraction)
        assert codes == {"11580-8", "3016-3"}

    def test_imaging_extracts_snomed_codes(self):
        extraction = DocumentExtraction(snomed_codes="12345, 67890")
        codes = extract_codes("ImagingReportTemplate", extraction)
        assert codes == {"12345", "67890"}

    def test_filters_invalid_codes(self):
        extraction = DocumentExtraction(loinc_codes="11580-8, N/A, , NONE")
        codes = extract_codes("LabReportTemplate", extraction)
        assert codes == {"11580-8"}

    def test_handles_list_codes(self):
        extraction = DocumentExtraction(loinc_codes=["11580-8", "3016-3"])
        codes = extract_codes("LabReportTemplate", extraction)
        assert codes == {"11580-8", "3016-3"}

    def test_handles_none(self):
        extraction = DocumentExtraction()
        codes = extract_codes("LabReportTemplate", extraction)
        assert codes == set()


class TestExtractKeywords:
    """Test keyword extraction from document extraction."""

    def test_extracts_all_fields(self):
        extraction = DocumentExtraction(
            test_names="CBC",
            study_names="MRI",
            modality="CT",
            body_part="Head",
        )
        keywords = extract_keywords(extraction)
        assert set(keywords) == {"CBC", "MRI", "CT", "Head"}

    def test_handles_partial_fields(self):
        extraction = DocumentExtraction(test_names="CBC", modality="CT")
        keywords = extract_keywords(extraction)
        assert set(keywords) == {"CBC", "CT"}

    def test_handles_none_values(self):
        extraction = DocumentExtraction()
        keywords = extract_keywords(extraction)
        assert keywords == []

    def test_handles_list_values(self):
        extraction = DocumentExtraction(test_names=["CBC", "BMP"])
        keywords = extract_keywords(extraction)
        assert set(keywords) == {"CBC", "BMP"}

    def test_strips_whitespace(self):
        extraction = DocumentExtraction(test_names="  CBC  , BMP  ")
        keywords = extract_keywords(extraction)
        assert keywords == ["CBC", "BMP"]


class TestKeywordBonus:
    """Test keyword bonus calculation."""

    def test_no_keywords(self):
        class MockTemplate:
            name = "Lab Report"
            search_keywords = ""

        assert _keyword_bonus(MockTemplate(), []) == 0.0

    def test_single_match(self):
        class MockTemplate:
            name = "CBC Lab Report"
            search_keywords = ""

        bonus = _keyword_bonus(MockTemplate(), ["CBC"])
        assert bonus > 0

    def test_multiple_matches(self):
        class MockTemplate:
            name = "CBC Lab Report"
            search_keywords = "blood count"

        single = _keyword_bonus(MockTemplate(), ["CBC"])
        double = _keyword_bonus(MockTemplate(), ["CBC", "blood"])
        assert double > single

    def test_case_insensitive(self):
        class MockTemplate:
            name = "CBC Lab Report"
            search_keywords = ""

        upper = _keyword_bonus(MockTemplate(), ["CBC"])
        lower = _keyword_bonus(MockTemplate(), ["cbc"])
        assert upper == lower

    def test_matches_in_search_keywords(self):
        class MockTemplate:
            name = "Lab Report"
            search_keywords = "complete blood count"

        bonus = _keyword_bonus(MockTemplate(), ["blood"])
        assert bonus > 0
