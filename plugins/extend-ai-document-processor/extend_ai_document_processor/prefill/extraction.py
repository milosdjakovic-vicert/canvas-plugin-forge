"""Template field extraction and prefill building."""

from logger import log

from extend_ai_document_processor.categorize import extract_with_schema
from extend_ai_document_processor.constants import (
    SCORE_THRESHOLD,
    GAP_FILL_THRESHOLD,
    MAX_FIELDS,
    AnnotationColor,
)
from extend_ai_document_processor.prefill.scoring import is_valid_code


def extract_fields_for_templates(
    candidates: list[dict],
    extracted_codes: set[str],
    field_model,
    file_url: str,
    confidence: float | None,
    api_key: str,
    processor_id: str,
) -> list[dict]:
    """Extract document data for each matched template until all codes covered."""
    matched_codes: set[str] = set()
    templates = []

    for candidate in candidates:
        is_gap_fill = len(templates) > 0
        threshold = GAP_FILL_THRESHOLD if is_gap_fill else SCORE_THRESHOLD

        if candidate["score"] < threshold:
            if not is_gap_fill:
                break
            continue

        new_codes = set(candidate["codes"]) - matched_codes
        if not new_codes:
            continue

        fields = list(field_model.objects.filter(
            report_template_id=candidate["id"]
        ).order_by("sequence"))

        if not fields:
            continue

        schema, key_map = _build_schema(fields, extracted_codes)
        if not schema["schema"]["properties"]:
            continue

        extraction, metadata, error = extract_with_schema(
            file_url, schema, api_key, processor_id
        )
        if error:
            log.warning("[PREFILL] Extraction error for %s: %s", candidate["name"], error)
            continue

        prefill_fields = _build_prefill_fields(extraction, metadata, key_map, confidence)
        if not prefill_fields:
            continue

        templates.append({
            "template_id": candidate["id"],
            "template_name": candidate["name"],
            "fields": prefill_fields,
        })
        matched_codes.update(candidate["codes"])

        log.info("[PREFILL] Added %s (%d/%d codes)", candidate["name"], len(matched_codes), len(extracted_codes))

        if matched_codes >= extracted_codes:
            break

    return templates


def _build_schema(fields: list, preferred_codes: set[str]) -> tuple[dict, dict]:
    """Build extraction schema from template fields."""
    sorted_fields = sorted(
        fields,
        key=lambda f: (getattr(f, "code", None) not in preferred_codes, getattr(f, "sequence", 0)),
    )

    properties = {}
    key_map = {}

    for f in sorted_fields[:MAX_FIELDS]:
        key = _field_key(f)
        if not key or key in properties:
            continue

        label = getattr(f, "label", "") or key
        desc_parts = []
        if code := getattr(f, "code", ""):
            desc_parts.append(f"code={code}")
        if units := getattr(f, "units", None):
            desc_parts.append(f"units={units}")
        desc = f"{label} ({'; '.join(desc_parts)})" if desc_parts else label

        properties[key] = {"type": ["string", "null"], "description": desc}
        key_map[key] = f

    return {
        "type": "EXTRACT",
        "baseProcessor": "extraction_performance",
        "baseVersion": "4.6.0",
        "schema": {"type": "object", "properties": properties},
        "advancedOptions": {"citationsEnabled": True},
    }, key_map


def _build_prefill_fields(
    extraction: dict | None,
    metadata: dict | None,
    key_map: dict,
    fallback_confidence: float | None,
) -> dict:
    """Convert extraction to prefill format."""
    if not extraction:
        return {}

    result = {}
    for key, raw in extraction.items():
        value = _normalize_value(raw)
        if not value:
            continue

        field = key_map.get(key)
        payload = {"value": value}

        if field and (units := getattr(field, "units", None)):
            payload["unit"] = units

        conf = None
        if isinstance(metadata, dict) and isinstance(metadata.get(key), dict):
            conf = metadata[key].get("ocrConfidence")
        conf = conf or fallback_confidence
        if conf is not None and 0 <= conf <= 1:
            payload["annotations"] = [{"text": f"AI {round(conf * 100)}%", "color": AnnotationColor.CONFIDENCE}]

        result[key] = payload

    return result


def _field_key(field) -> str | None:
    """Get unique key for field."""
    code = getattr(field, "code", None)
    if isinstance(code, str) and is_valid_code(code):
        return code.strip()
    label = getattr(field, "label", None)
    if isinstance(label, str) and label.strip():
        return label.strip()
    return None


def _normalize_value(value) -> str | None:
    """Normalize field value to string."""
    if value is None:
        return None
    if isinstance(value, list):
        parts = [_normalize_value(v) for v in value]
        parts = [p for p in parts if p]
        return ", ".join(parts) if parts else None
    if isinstance(value, dict) and "value" in value:
        return _normalize_value(value["value"])
    text = str(value).strip()
    return text if text else None
