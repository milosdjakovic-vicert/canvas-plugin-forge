"""Document field prefilling orchestration."""

from pydantic import ValidationError

from canvas_sdk.effects import Effect
from canvas_sdk.effects.data_integration import PrefillDocumentFields
from canvas_sdk.v1.data import (
    ImagingReportTemplate,
    ImagingReportTemplateField,
    LabReportTemplate,
    LabReportTemplateField,
    SpecialtyReportTemplate,
    SpecialtyReportTemplateField,
)
from logger import log

from extend_ai_document_processor.models import DocumentExtraction
from extend_ai_document_processor.prefill.scoring import score_templates, extract_codes, extract_keywords
from extend_ai_document_processor.prefill.extraction import extract_fields_for_templates


def prefill_document_fields(
    document_id: str,
    file_url: str,
    template_type: str,
    extraction: DocumentExtraction,
    confidence: float | None,
    api_key: str,
    processor_id: str,
) -> Effect | None:
    """Match report templates and prefill document fields with extracted data.

    Returns PrefillDocumentFields effect or None if no templates match.
    """
    field_model, template_model = _get_models(template_type)
    if not field_model:
        return None

    codes = extract_codes(template_type, extraction)
    keywords = extract_keywords(extraction)

    if not codes:
        log.info("[PREFILL] No codes to match")
        return None

    candidates = score_templates(field_model, template_model, codes, keywords, template_type)
    if not candidates:
        log.info("[PREFILL] No matching templates")
        return None

    log.info(
        "[PREFILL] Found %d candidates, top: %s (%.2f)",
        len(candidates),
        candidates[0]["name"],
        candidates[0]["score"],
    )

    templates = extract_fields_for_templates(
        candidates, codes, field_model,
        file_url, confidence, api_key, processor_id,
    )

    if not templates:
        return None

    try:
        return PrefillDocumentFields(
            document_id=str(document_id),
            templates=templates,
            annotations=[],
        ).apply()
    except ValidationError as e:
        log.error("[PREFILL] Effect error: %s", e)
        return None


def _get_models(template_type: str) -> tuple:
    """Get field and template models for template type."""
    return {
        "LabReportTemplate": (LabReportTemplateField, LabReportTemplate),
        "ImagingReportTemplate": (ImagingReportTemplateField, ImagingReportTemplate),
        "SpecialtyReportTemplate": (SpecialtyReportTemplateField, SpecialtyReportTemplate),
    }.get(template_type, (None, None))
