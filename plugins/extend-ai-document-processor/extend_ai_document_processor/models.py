"""Data models for document processing."""

from dataclasses import dataclass, field

from pydantic import BaseModel


class DocumentExtraction(BaseModel):
    """Data extracted from document by Extend.ai."""

    model_config = {"extra": "allow"}

    document_type: str | None = None
    loinc_codes: list[str] | str | None = None
    snomed_codes: list[str] | str | None = None
    test_names: list[str] | str | None = None
    study_names: list[str] | str | None = None
    modality: str | None = None
    body_part: str | None = None

    patient_id: str | None = None
    patient_first_name: str | None = None
    patient_last_name: str | None = None
    patient_name: str | None = None
    date_of_birth: str | None = None

    practitioner_npi: str | None = None
    practitioner_first_name: str | None = None
    practitioner_last_name: str | None = None
    practitioner_name: str | None = None


@dataclass
class CategorizationResult:
    """Result of document categorization."""

    document_type: dict | None = None
    extraction: DocumentExtraction = field(default_factory=DocumentExtraction)
    metadata: dict | None = None
    confidence: float | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class PatientMatch:
    """Result of patient matching."""

    patient: "Patient | None" = None
    error: str | None = None

    @property
    def found(self) -> bool:
        return self.patient is not None


@dataclass
class ReviewerMatch:
    """Result of reviewer matching."""

    reviewer: "Staff | None" = None
    auto_assigned: bool = False

    @property
    def found(self) -> bool:
        return self.reviewer is not None
