"""Tests for Canvas SDK effect builders."""

import pytest
from unittest.mock import MagicMock, patch

from extend_ai_document_processor.effects import (
    categorize_effect,
    link_patient_effect,
    assign_reviewer_effect,
    _build_annotations,
    SOURCE_PROTOCOL,
)
from extend_ai_document_processor.constants import AnnotationColor


class TestBuildAnnotations:
    """Test annotation building helper."""

    def test_confidence_annotation(self):
        result = _build_annotations(0.95)
        assert len(result) == 1
        assert result[0]["text"] == "AI 95%"
        assert result[0]["color"] == AnnotationColor.CONFIDENCE

    def test_confidence_rounds(self):
        result = _build_annotations(0.876)
        assert result[0]["text"] == "AI 88%"

    def test_confidence_zero(self):
        result = _build_annotations(0.0)
        assert len(result) == 1
        assert result[0]["text"] == "AI 0%"

    def test_confidence_one(self):
        result = _build_annotations(1.0)
        assert len(result) == 1
        assert result[0]["text"] == "AI 100%"

    def test_confidence_out_of_range_high(self):
        result = _build_annotations(1.5)
        assert result == []

    def test_confidence_out_of_range_negative(self):
        result = _build_annotations(-0.1)
        assert result == []

    def test_error_annotation(self):
        result = _build_annotations(None, "Patient not found")
        assert len(result) == 1
        assert result[0]["text"] == "Patient not found"
        assert result[0]["color"] == AnnotationColor.ERROR

    def test_confidence_takes_precedence_over_error(self):
        result = _build_annotations(0.95, "Some error")
        assert result[0]["text"] == "AI 95%"

    def test_none_confidence_and_none_error(self):
        result = _build_annotations(None, None)
        assert result == []


class TestCategorizeEffect:
    """Test categorize effect builder."""

    @patch("extend_ai_document_processor.effects.CategorizeDocument")
    def test_success(self, mock_categorize):
        mock_effect = MagicMock()
        mock_categorize.return_value.apply.return_value = mock_effect

        doc_type = {
            "key": "lab_report",
            "name": "Lab Report",
            "report_type": "LAB",
            "template_type": "LabReportTemplate",
        }
        result = categorize_effect("doc-123", doc_type, 0.95)

        assert result == mock_effect
        mock_categorize.assert_called_once()
        call_kwargs = mock_categorize.call_args.kwargs
        assert call_kwargs["document_id"] == "doc-123"
        assert call_kwargs["document_type"]["key"] == "lab_report"
        assert call_kwargs["source_protocol"] == SOURCE_PROTOCOL

    @patch("extend_ai_document_processor.effects.CategorizeDocument")
    def test_with_patient_error(self, mock_categorize):
        mock_categorize.return_value.apply.return_value = MagicMock()

        doc_type = {
            "key": "lab_report",
            "name": "Lab Report",
            "report_type": "LAB",
        }
        categorize_effect("doc-123", doc_type, None, patient_error="Multiple patients")

        call_kwargs = mock_categorize.call_args.kwargs
        assert any(
            "Multiple patients" in str(a.get("text", ""))
            for a in call_kwargs["annotations"]
        )

    def test_missing_required_keys_returns_none(self):
        doc_type = {"key": "lab"}  # Missing name and report_type
        result = categorize_effect("doc-123", doc_type, 0.95)
        assert result is None

    def test_empty_doc_type_returns_none(self):
        result = categorize_effect("doc-123", {}, 0.95)
        assert result is None


class TestLinkPatientEffect:
    """Test link patient effect builder."""

    @patch("extend_ai_document_processor.effects.LinkDocumentToPatient")
    def test_success(self, mock_link):
        mock_effect = MagicMock()
        mock_link.return_value.apply.return_value = mock_effect

        mock_patient = MagicMock()
        mock_patient.id = "patient-123"

        result = link_patient_effect("doc-123", mock_patient, 0.92)

        assert result == mock_effect
        mock_link.assert_called_once()
        call_kwargs = mock_link.call_args.kwargs
        assert call_kwargs["document_id"] == "doc-123"
        assert call_kwargs["patient_key"] == "patient-123"
        assert call_kwargs["source_protocol"] == SOURCE_PROTOCOL

    @patch("extend_ai_document_processor.effects.LinkDocumentToPatient")
    def test_with_confidence_annotation(self, mock_link):
        mock_link.return_value.apply.return_value = MagicMock()

        mock_patient = MagicMock(id="patient-123")
        link_patient_effect("doc-123", mock_patient, 0.88)

        call_kwargs = mock_link.call_args.kwargs
        assert len(call_kwargs["annotations"]) == 1
        assert "AI 88%" in call_kwargs["annotations"][0]["text"]


class TestAssignReviewerEffect:
    """Test assign reviewer effect builder."""

    @patch("extend_ai_document_processor.effects.AssignDocumentReviewer")
    def test_success(self, mock_assign):
        mock_effect = MagicMock()
        mock_assign.return_value.apply.return_value = mock_effect

        mock_reviewer = MagicMock()
        mock_reviewer.id = "staff-123"

        result = assign_reviewer_effect(
            "doc-123", mock_reviewer, auto_assigned=False, confidence=0.95
        )

        assert result == mock_effect
        mock_assign.assert_called_once()
        call_kwargs = mock_assign.call_args.kwargs
        assert call_kwargs["document_id"] == "doc-123"
        assert call_kwargs["reviewer_id"] == "staff-123"
        assert call_kwargs["source_protocol"] == SOURCE_PROTOCOL

    @patch("extend_ai_document_processor.effects.AssignDocumentReviewer")
    def test_auto_assigned_annotation(self, mock_assign):
        mock_assign.return_value.apply.return_value = MagicMock()

        mock_reviewer = MagicMock(id="staff-123")
        assign_reviewer_effect(
            "doc-123", mock_reviewer, auto_assigned=True, confidence=0.95
        )

        call_kwargs = mock_assign.call_args.kwargs
        assert any(
            "Auto-assigned" in str(a.get("text", ""))
            for a in call_kwargs["annotations"]
        )

    @patch("extend_ai_document_processor.effects.AssignDocumentReviewer")
    def test_not_auto_assigned_uses_confidence(self, mock_assign):
        mock_assign.return_value.apply.return_value = MagicMock()

        mock_reviewer = MagicMock(id="staff-123")
        assign_reviewer_effect(
            "doc-123", mock_reviewer, auto_assigned=False, confidence=0.85
        )

        call_kwargs = mock_assign.call_args.kwargs
        assert any(
            "AI 85%" in str(a.get("text", ""))
            for a in call_kwargs["annotations"]
        )

    @patch("extend_ai_document_processor.effects.AssignDocumentReviewer")
    def test_with_patient_error_annotation(self, mock_assign):
        mock_assign.return_value.apply.return_value = MagicMock()

        mock_reviewer = MagicMock(id="staff-123")
        assign_reviewer_effect(
            "doc-123",
            mock_reviewer,
            auto_assigned=False,
            confidence=None,
            patient_error="Multiple patients found",
        )

        call_kwargs = mock_assign.call_args.kwargs
        assert any(
            "Multiple patients found" in str(a.get("text", ""))
            for a in call_kwargs["annotations"]
        )
