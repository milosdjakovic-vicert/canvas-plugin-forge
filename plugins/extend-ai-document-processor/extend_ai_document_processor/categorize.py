"""Document categorization using Extend.ai API."""

import re
import time

from pydantic import ValidationError

from canvas_sdk.utils import Http
from logger import log

from extend_ai_document_processor.constants import API_URL, API_VERSION, MAX_RETRIES
from extend_ai_document_processor.models import CategorizationResult, DocumentExtraction


def categorize_document(
    file_url: str,
    available_types: list[dict],
    api_key: str,
    processor_id: str,
) -> CategorizationResult:
    """Categorize a document and extract structured data.

    Calls Extend.ai to:
    1. Classify the document type from available_types
    2. Extract patient/practitioner info and medical codes

    Returns CategorizationResult with matched document type and extraction data.
    """
    if not file_url:
        return CategorizationResult(error="Missing file URL")

    slug_to_type = _build_slug_map(available_types)
    schema = _build_extraction_schema(list(slug_to_type.keys()))

    response, request_id = _call_api(api_key, processor_id, file_url, schema)
    if response is None:
        return CategorizationResult(error="API request failed after retries")
    if not response.ok:
        return CategorizationResult(error=_format_error(response, request_id))

    data = response.json()
    output = data.get("processorRun", {}).get("output", {})
    extraction_raw = output.get("value", {})
    metadata = output.get("metadata")

    extraction = _parse_extraction(extraction_raw)
    doc_slug = extraction.document_type or extraction_raw.get("document_type")
    matched_type = slug_to_type.get(doc_slug)

    confidence = _extract_min_confidence(metadata)

    log.info(
        "[CATEGORIZE] type=%s confidence=%s",
        matched_type.get("name") if matched_type else None,
        round(confidence, 2) if confidence else None,
    )

    return CategorizationResult(
        document_type=matched_type,
        extraction=extraction,
        metadata=metadata,
        confidence=confidence,
    )


def extract_with_schema(
    file_url: str,
    schema: dict,
    api_key: str,
    processor_id: str,
) -> tuple[dict | None, dict | None, str | None]:
    """Extract data using a custom schema. Returns (extraction, metadata, error)."""
    if not file_url:
        return None, None, "Missing file URL"

    response, request_id = _call_api(api_key, processor_id, file_url, schema)
    if response is None:
        return None, None, "API request failed after retries"
    if not response.ok:
        return None, None, _format_error(response, request_id)

    data = response.json()
    output = data.get("processorRun", {}).get("output", {})
    return output.get("value", {}), output.get("metadata"), None


def _call_api(
    api_key: str,
    processor_id: str,
    file_url: str,
    schema: dict,
) -> tuple:
    """Call Extend.ai API with retries. Returns (response, request_id)."""
    http = Http()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "x-extend-api-version": API_VERSION,
    }
    payload = {
        "processorId": processor_id,
        "file": {"fileUrl": file_url},
        "sync": True,
        "config": schema,
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = http.post(API_URL, headers=headers, json=payload)
            request_id = None
            try:
                request_id = response.json().get("requestId")
            except Exception:
                pass

            if response.ok or 400 <= response.status_code < 500:
                return response, request_id

            if attempt < MAX_RETRIES:
                log.warning("[CATEGORIZE] Retry %d after status %d", attempt + 1, response.status_code)
                time.sleep(attempt + 1)

        except Exception as e:
            log.warning("[CATEGORIZE] Request error: %s", e)
            if attempt >= MAX_RETRIES:
                return None, None
            time.sleep(attempt + 1)

    return None, None


def _build_slug_map(available_types: list[dict]) -> dict[str, dict]:
    """Build mapping from slugified names to document types."""
    result = {}
    for doc_type in available_types:
        name = doc_type.get("name")
        if name:
            slug = _slugify(name)
            if slug not in result:
                result[slug] = doc_type
    return result


def _slugify(value: str) -> str:
    """Convert name to slug: 'Lab Report' -> 'lab_report'."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _build_extraction_schema(slugs: list[str]) -> dict:
    """Build Extend.ai extraction schema."""
    doc_type_schema = {"type": "string", "description": "Document type"}
    if slugs:
        doc_type_schema["enum"] = slugs

    return {
        "type": "EXTRACT",
        "baseProcessor": "extraction_performance",
        "baseVersion": "4.6.0",
        "schema": {
            "type": "object",
            "properties": {
                "document_type": doc_type_schema,
                "loinc_codes": {"type": ["string", "null"], "description": "LOINC codes"},
                "snomed_codes": {"type": ["string", "null"], "description": "SNOMED codes"},
                "test_names": {"type": ["string", "null"], "description": "Test names"},
                "study_names": {"type": ["string", "null"], "description": "Study names"},
                "modality": {"type": ["string", "null"]},
                "body_part": {"type": ["string", "null"]},
                "patient_id": {"type": ["string", "null"]},
                "patient_first_name": {"type": ["string", "null"]},
                "patient_last_name": {"type": ["string", "null"]},
                "patient_name": {"type": ["string", "null"]},
                "date_of_birth": {"type": ["string", "null"], "extend:type": "date"},
                "practitioner_npi": {"type": ["string", "null"]},
                "practitioner_first_name": {"type": ["string", "null"]},
                "practitioner_last_name": {"type": ["string", "null"]},
                "practitioner_name": {"type": ["string", "null"]},
            },
            "required": ["document_type"],
        },
        "advancedOptions": {"citationsEnabled": True},
    }


def _parse_extraction(raw: dict) -> DocumentExtraction:
    """Parse extraction data, handling validation errors gracefully."""
    try:
        return DocumentExtraction.model_validate(raw)
    except ValidationError:
        return DocumentExtraction.model_construct(**raw)


def _extract_min_confidence(metadata: dict | None) -> float | None:
    """Extract minimum OCR confidence from metadata."""
    if not metadata:
        return None
    scores = []
    for field_meta in metadata.values():
        if isinstance(field_meta, dict):
            conf = field_meta.get("ocrConfidence")
            if isinstance(conf, (int, float)):
                scores.append(float(conf))
    return min(scores) if scores else None


def _format_error(response, request_id: str | None) -> str:
    """Format API error message."""
    status = response.status_code
    try:
        data = response.json()
        parts = [f"status={status}"]
        if code := data.get("code"):
            parts.append(f"code={code}")
        if msg := data.get("message"):
            parts.append(msg)
        if rid := (request_id or data.get("requestId")):
            parts.append(f"requestId={rid}")
        return "Extend.ai: " + " | ".join(parts)
    except Exception:
        return f"Extend.ai: status={status}"
