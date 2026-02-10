"""Canvas SDK effect builders for document processing."""

from pydantic import ValidationError

from canvas_sdk.effects import Effect
from canvas_sdk.effects.data_integration import (
    AnnotationItem,
    AssignDocumentReviewer,
    CategorizeDocument,
    LinkDocumentToPatient,
    Priority,
    ReviewMode,
)
from logger import log

from extend_ai_document_processor.constants import AnnotationColor


SOURCE_PROTOCOL = "extend_ai_document_processor"


def categorize_effect(
    doc_id: str,
    doc_type: dict,
    confidence: float | None,
    patient_error: str | None = None,
) -> Effect | None:
    """Build CategorizeDocument effect."""
    try:
        return CategorizeDocument(
            document_id=str(doc_id),
            document_type={
                "key": doc_type["key"],
                "name": doc_type["name"],
                "report_type": doc_type["report_type"],
                "template_type": doc_type.get("template_type"),
            },
            annotations=_build_annotations(confidence, patient_error),
            source_protocol=SOURCE_PROTOCOL,
        ).apply()
    except (ValidationError, KeyError) as e:
        log.error("[EFFECTS] Categorize error: %s", e)
        return None


def link_patient_effect(
    doc_id: str,
    patient,
    confidence: float | None,
) -> Effect | None:
    """Build LinkDocumentToPatient effect."""
    try:
        return LinkDocumentToPatient(
            document_id=str(doc_id),
            patient_key=str(patient.id),
            annotations=_build_annotations(confidence),
            source_protocol=SOURCE_PROTOCOL,
        ).apply()
    except ValidationError as e:
        log.error("[EFFECTS] Link error: %s", e)
        return None


def assign_reviewer_effect(
    doc_id: str,
    reviewer,
    auto_assigned: bool,
    confidence: float | None,
    patient_error: str | None = None,
) -> Effect | None:
    """Build AssignDocumentReviewer effect."""
    if auto_assigned:
        annotations = [{"text": "Auto-assigned", "color": AnnotationColor.AUTO_ASSIGNED}]
    else:
        raw = _build_annotations(confidence, patient_error)
        annotations = [{"text": a["text"], "color": a["color"]} for a in raw]

    try:
        return AssignDocumentReviewer(
            document_id=str(doc_id),
            reviewer_id=str(reviewer.id),
            priority=Priority.HIGH,
            review_mode=ReviewMode.REVIEW_NOT_REQUIRED,
            annotations=annotations,
            source_protocol=SOURCE_PROTOCOL,
        ).apply()
    except ValidationError as e:
        log.error("[EFFECTS] Assign error: %s", e)
        return None


def _build_annotations(confidence: float | None, error: str | None = None) -> list[dict]:
    """Build annotation list for confidence or error display."""
    if confidence is not None and 0 <= confidence <= 1:
        return [{"text": f"AI {round(confidence * 100)}%", "color": AnnotationColor.CONFIDENCE}]
    if error:
        return [{"text": error, "color": AnnotationColor.ERROR}]
    return []
