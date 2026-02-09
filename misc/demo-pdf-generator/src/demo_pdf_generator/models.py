"""Pydantic models for PDF generation configuration."""

from pydantic import BaseModel


class PatientConfig(BaseModel):
    """Patient information for the report."""

    first_name: str
    last_name: str
    date_of_birth: str
    mrn: str = ""


class ReviewerConfig(BaseModel):
    """Reviewer/Practitioner information for the report."""

    first_name: str
    last_name: str
    npi: str = ""


class ReportConfig(BaseModel):
    """Report metadata."""

    type: str  # lab_report | imaging_report | specialty_report
    date: str
    facility: str = "Canvas Medical Lab"


class PdfConfig(BaseModel):
    """Complete PDF generation configuration."""

    patient: PatientConfig
    reviewer: ReviewerConfig
    report: ReportConfig
    pages: int = 1
