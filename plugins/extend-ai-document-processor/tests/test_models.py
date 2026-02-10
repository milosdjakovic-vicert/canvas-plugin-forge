"""Tests for data models."""

import pytest
from unittest.mock import MagicMock

from extend_ai_document_processor.models import (
    DocumentExtraction,
    CategorizationResult,
    PatientMatch,
    ReviewerMatch,
)


class TestDocumentExtraction:
    """Test DocumentExtraction model."""

    def test_default_values(self):
        e = DocumentExtraction()
        assert e.document_type is None
        assert e.loinc_codes is None
        assert e.patient_id is None

    def test_with_values(self):
        e = DocumentExtraction(
            document_type="lab_report",
            loinc_codes="11580-8",
            patient_id="MRN123",
        )
        assert e.document_type == "lab_report"
        assert e.loinc_codes == "11580-8"
        assert e.patient_id == "MRN123"

    def test_extra_fields_allowed(self):
        e = DocumentExtraction(custom_field="value")
        assert e.model_extra.get("custom_field") == "value"

    def test_codes_as_list(self):
        e = DocumentExtraction(loinc_codes=["11580-8", "3016-3"])
        assert e.loinc_codes == ["11580-8", "3016-3"]


class TestCategorizationResult:
    """Test CategorizationResult."""

    def test_ok_without_error(self):
        r = CategorizationResult()
        assert r.ok is True

    def test_not_ok_with_error(self):
        r = CategorizationResult(error="Something failed")
        assert r.ok is False

    def test_with_document_type(self):
        r = CategorizationResult(
            document_type={"key": "lab", "name": "Lab Report"},
            extraction=DocumentExtraction(document_type="lab_report"),
        )
        assert r.document_type["name"] == "Lab Report"
        assert r.extraction.document_type == "lab_report"

    def test_with_confidence(self):
        r = CategorizationResult(confidence=0.95)
        assert r.confidence == 0.95
        assert r.ok is True

    def test_with_metadata(self):
        metadata = {"field": {"ocrConfidence": 0.9}}
        r = CategorizationResult(metadata=metadata)
        assert r.metadata == metadata


class TestPatientMatch:
    """Test PatientMatch."""

    def test_found_with_patient(self):
        mock_patient = MagicMock()
        mock_patient.id = "patient-123"
        r = PatientMatch(patient=mock_patient)
        assert r.found is True
        assert r.patient.id == "patient-123"

    def test_not_found_without_patient(self):
        r = PatientMatch()
        assert r.found is False
        assert r.patient is None

    def test_not_found_with_error(self):
        r = PatientMatch(error="Multiple patients found")
        assert r.found is False
        assert r.error == "Multiple patients found"

    def test_found_with_patient_and_no_error(self):
        mock_patient = MagicMock()
        r = PatientMatch(patient=mock_patient)
        assert r.found is True
        assert r.error is None


class TestReviewerMatch:
    """Test ReviewerMatch."""

    def test_found_with_reviewer(self):
        mock_reviewer = MagicMock()
        mock_reviewer.id = "staff-123"
        r = ReviewerMatch(reviewer=mock_reviewer)
        assert r.found is True
        assert r.reviewer.id == "staff-123"

    def test_not_found_without_reviewer(self):
        r = ReviewerMatch()
        assert r.found is False
        assert r.reviewer is None

    def test_auto_assigned_default(self):
        r = ReviewerMatch()
        assert r.auto_assigned is False

    def test_auto_assigned_true(self):
        mock_reviewer = MagicMock()
        r = ReviewerMatch(reviewer=mock_reviewer, auto_assigned=True)
        assert r.found is True
        assert r.auto_assigned is True

    def test_found_and_not_auto_assigned(self):
        mock_reviewer = MagicMock()
        r = ReviewerMatch(reviewer=mock_reviewer, auto_assigned=False)
        assert r.found is True
        assert r.auto_assigned is False
