"""Shared fixtures for extend-ai-document-processor tests."""

import sys
from unittest.mock import MagicMock

import pytest


# Mock canvas_sdk modules that may not exist in test environment
mock_data_integration = MagicMock()
mock_data_integration.PrefillDocumentFields = MagicMock()
sys.modules["canvas_sdk.effects.data_integration"] = mock_data_integration

# Patch canvas_sdk.v1.data with missing report template types
from canvas_sdk.v1 import data as sdk_data

if not hasattr(sdk_data, "ImagingReportTemplate"):
    sdk_data.ImagingReportTemplate = MagicMock()
if not hasattr(sdk_data, "ImagingReportTemplateField"):
    sdk_data.ImagingReportTemplateField = MagicMock()
if not hasattr(sdk_data, "LabReportTemplate"):
    sdk_data.LabReportTemplate = MagicMock()
if not hasattr(sdk_data, "LabReportTemplateField"):
    sdk_data.LabReportTemplateField = MagicMock()
if not hasattr(sdk_data, "SpecialtyReportTemplate"):
    sdk_data.SpecialtyReportTemplate = MagicMock()
if not hasattr(sdk_data, "SpecialtyReportTemplateField"):
    sdk_data.SpecialtyReportTemplateField = MagicMock()


@pytest.fixture
def sample_extraction_data():
    """Sample extraction data from Extend.ai."""
    return {
        "document_type": "lab_report",
        "loinc_codes": "11580-8, 3016-3",
        "snomed_codes": None,
        "test_names": "TSH, T4 Free",
        "patient_id": "MRN123",
        "patient_first_name": "John",
        "patient_last_name": "Doe",
        "date_of_birth": "1990-01-15",
        "practitioner_npi": "1234567890",
        "practitioner_first_name": "Jane",
        "practitioner_last_name": "Smith",
    }


@pytest.fixture
def sample_metadata():
    """Sample metadata with OCR confidence scores."""
    return {
        "document_type": {"ocrConfidence": 0.95},
        "loinc_codes": {"ocrConfidence": 0.88},
        "patient_id": {"ocrConfidence": 0.92},
        "patient_first_name": {"ocrConfidence": 0.85},
    }


@pytest.fixture
def sample_available_types():
    """Sample available document types."""
    return [
        {
            "key": "lab_report",
            "name": "Lab Report",
            "report_type": "LAB",
            "template_type": "LabReportTemplate",
        },
        {
            "key": "imaging_report",
            "name": "Imaging Report",
            "report_type": "IMAGING",
            "template_type": "ImagingReportTemplate",
        },
        {
            "key": "specialty_report",
            "name": "Specialty Report",
            "report_type": "SPECIALTY",
            "template_type": "SpecialtyReportTemplate",
        },
    ]
