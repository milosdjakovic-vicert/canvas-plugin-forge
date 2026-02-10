"""Integration tests for patient and reviewer matching with mocked ORM."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from extend_ai_document_processor.models import DocumentExtraction
from extend_ai_document_processor.match import find_patient, find_reviewer


def make_queryset_mock(items):
    """Create a mock that behaves like a Django QuerySet."""
    mock = MagicMock()
    mock.__iter__ = lambda self: iter(items)
    mock.__len__ = lambda self: len(items)
    mock.first.return_value = items[0] if items else None
    return mock


class TestFindPatient:
    """Test patient matching with mocked ORM."""

    @patch("extend_ai_document_processor.match.Patient")
    def test_match_by_mrn_single(self, mock_patient_cls):
        mock_patient = MagicMock(id="123")
        mock_patient_cls.objects.filter.return_value = [mock_patient]

        extraction = DocumentExtraction(patient_id="MRN001")
        result = find_patient(extraction)

        assert result.found is True
        assert result.error is None
        mock_patient_cls.objects.filter.assert_called_with(mrn="MRN001")

    @patch("extend_ai_document_processor.match.Patient")
    def test_match_by_mrn_multiple_returns_error(self, mock_patient_cls):
        mock_patient_cls.objects.filter.return_value = [MagicMock(), MagicMock()]

        extraction = DocumentExtraction(patient_id="MRN001")
        result = find_patient(extraction)

        assert result.found is False
        assert "Multiple" in result.error

    @patch("extend_ai_document_processor.match.Patient")
    def test_match_by_mrn_none_found_fallback_to_name(self, mock_patient_cls):
        mock_patient = MagicMock(id="456")
        mock_patient_cls.objects.filter.side_effect = [
            [],  # MRN lookup
            [mock_patient],  # name+DOB lookup
        ]

        extraction = DocumentExtraction(
            patient_id="MRN001",
            patient_first_name="John",
            patient_last_name="Doe",
            date_of_birth="1990-01-15",
        )
        result = find_patient(extraction)

        assert result.found is True

    @patch("extend_ai_document_processor.match.Patient")
    def test_match_by_name_and_dob(self, mock_patient_cls):
        mock_patient = MagicMock(id="456")
        mock_patient_cls.objects.filter.return_value = [mock_patient]

        extraction = DocumentExtraction(
            patient_first_name="John",
            patient_last_name="Doe",
            date_of_birth="1990-01-15",
        )
        result = find_patient(extraction)

        assert result.found is True
        assert result.patient.id == "456"

    @patch("extend_ai_document_processor.match.Patient")
    def test_match_by_name_only(self, mock_patient_cls):
        mock_patient = MagicMock(id="789")
        mock_patient_cls.objects.filter.return_value = [mock_patient]

        extraction = DocumentExtraction(
            patient_first_name="John",
            patient_last_name="Doe",
        )
        result = find_patient(extraction)

        assert result.found is True

    @patch("extend_ai_document_processor.match.Patient")
    def test_match_by_full_name(self, mock_patient_cls):
        mock_patient = MagicMock(id="999")
        mock_patient_cls.objects.filter.return_value = [mock_patient]

        extraction = DocumentExtraction(patient_name="John Doe")
        result = find_patient(extraction)

        assert result.found is True

    @patch("extend_ai_document_processor.match.Patient")
    def test_no_match_by_name_dob_then_name_only(self, mock_patient_cls):
        mock_patient = MagicMock(id="789")
        mock_patient_cls.objects.filter.side_effect = [
            [],  # name+DOB lookup fails
            [mock_patient],  # name-only succeeds
        ]

        extraction = DocumentExtraction(
            patient_first_name="John",
            patient_last_name="Doe",
            date_of_birth="1990-01-15",
        )
        result = find_patient(extraction)

        assert result.found is True

    @patch("extend_ai_document_processor.match.Patient")
    def test_no_match_with_multiple_by_name(self, mock_patient_cls):
        mock_patient_cls.objects.filter.return_value = [MagicMock(), MagicMock()]

        extraction = DocumentExtraction(
            patient_first_name="John",
            patient_last_name="Doe",
        )
        result = find_patient(extraction)

        assert result.found is False
        assert "Multiple" in result.error

    @patch("extend_ai_document_processor.match.Patient")
    def test_no_extraction_data(self, mock_patient_cls):
        extraction = DocumentExtraction()
        result = find_patient(extraction)

        assert result.found is False
        assert result.error is None

    @patch("extend_ai_document_processor.match.Patient")
    def test_only_first_name_no_match(self, mock_patient_cls):
        extraction = DocumentExtraction(patient_first_name="John")
        result = find_patient(extraction)

        assert result.found is False


class TestFindReviewer:
    """Test reviewer matching with mocked ORM."""

    @patch("extend_ai_document_processor.match.Staff")
    def test_match_by_npi(self, mock_staff_cls):
        mock_reviewer = MagicMock(id="staff-123")
        mock_staff_cls.objects.filter.return_value = [mock_reviewer]

        extraction = DocumentExtraction(practitioner_npi="1234567890")
        result = find_reviewer(extraction)

        assert result.found is True
        assert result.reviewer.id == "staff-123"
        assert result.auto_assigned is False

    @patch("extend_ai_document_processor.match.Staff")
    def test_match_by_name(self, mock_staff_cls):
        mock_reviewer = MagicMock(id="staff-456")
        # For staff name lookup (not NPI first since no NPI in extraction)
        mock_staff_cls.objects.filter.return_value = [mock_reviewer]

        extraction = DocumentExtraction(
            practitioner_first_name="Jane",
            practitioner_last_name="Smith",
        )
        result = find_reviewer(extraction)

        assert result.found is True
        assert result.auto_assigned is False

    @patch("extend_ai_document_processor.match.Staff")
    def test_match_by_full_name(self, mock_staff_cls):
        mock_reviewer = MagicMock(id="staff-789")
        mock_staff_cls.objects.filter.return_value = [mock_reviewer]

        extraction = DocumentExtraction(practitioner_name="Jane Smith")
        result = find_reviewer(extraction)

        assert result.found is True

    @patch("extend_ai_document_processor.match.Staff")
    def test_auto_assign_canvas_bot(self, mock_staff_cls):
        mock_bot = MagicMock(id="canvas-bot")
        # No name in extraction, goes straight to auto-assign
        filter_mock = make_queryset_mock([mock_bot])
        mock_staff_cls.objects.filter.return_value = filter_mock

        extraction = DocumentExtraction()
        result = find_reviewer(extraction)

        assert result.found is True
        assert result.auto_assigned is True

    @patch("extend_ai_document_processor.match.Staff")
    def test_auto_assign_fallback_to_first_staff(self, mock_staff_cls):
        mock_first = MagicMock(id="first-staff")
        # Canvas Bot lookup returns empty
        filter_mock = make_queryset_mock([])
        mock_staff_cls.objects.filter.return_value = filter_mock
        mock_staff_cls.objects.first.return_value = mock_first

        extraction = DocumentExtraction()
        result = find_reviewer(extraction)

        assert result.found is True
        assert result.auto_assigned is True

    @patch("extend_ai_document_processor.match.Staff")
    def test_no_staff_available(self, mock_staff_cls):
        filter_mock = make_queryset_mock([])
        mock_staff_cls.objects.filter.return_value = filter_mock
        mock_staff_cls.objects.first.return_value = None

        extraction = DocumentExtraction()
        result = find_reviewer(extraction)

        assert result.found is False
        assert result.auto_assigned is False

    @patch("extend_ai_document_processor.match.Staff")
    def test_npi_not_found_fallback_to_name(self, mock_staff_cls):
        mock_reviewer = MagicMock(id="staff-by-name")
        mock_staff_cls.objects.filter.side_effect = [
            [],  # NPI lookup fails
            [mock_reviewer],  # Name lookup succeeds
        ]

        extraction = DocumentExtraction(
            practitioner_npi="0000000000",
            practitioner_first_name="Jane",
            practitioner_last_name="Smith",
        )
        result = find_reviewer(extraction)

        assert result.found is True
        assert result.auto_assigned is False
