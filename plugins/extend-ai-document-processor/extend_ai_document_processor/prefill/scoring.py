"""Template scoring using IDF-weighted code matching."""

import re

from logger import log

from extend_ai_document_processor.constants import KEYWORD_BONUS
from extend_ai_document_processor.models import DocumentExtraction


def score_templates(
    field_model,
    template_model,
    codes: set[str],
    keywords: list[str],
    template_type: str,
) -> list[dict]:
    """Score templates using IDF-weighted code matching."""
    code_filter = "snomed" if template_type == "ImagingReportTemplate" else None

    queryset = field_model.objects.filter(code__in=codes)
    if code_filter:
        queryset = queryset.filter(code_system__icontains=code_filter)
    fields = list(queryset.select_related("report_template"))

    if not fields:
        return _keyword_fallback(template_model, keywords)

    code_templates = _build_code_template_map(fields)
    if not code_templates:
        return []

    weights = {code: 1.0 / len(tids) for code, tids in code_templates.items()}
    total_weight = sum(weights.values())

    return _score_candidates(fields, weights, total_weight, keywords)


def extract_codes(template_type: str, extraction: DocumentExtraction) -> set[str]:
    """Extract matching codes (LOINC or SNOMED) based on template type."""
    if template_type == "LabReportTemplate":
        raw = extraction.loinc_codes
    else:
        raw = extraction.snomed_codes
    return {c.strip() for c in _to_list(raw) if is_valid_code(c)}


def extract_keywords(extraction: DocumentExtraction) -> list[str]:
    """Extract keywords from document extraction for template matching."""
    keywords = []
    for val in [extraction.test_names, extraction.study_names, extraction.modality, extraction.body_part]:
        keywords.extend(_to_list(val))
    return [k.strip() for k in keywords if k and k.strip()]


def is_valid_code(code: str) -> bool:
    """Check if code is valid (not N/A, empty, etc)."""
    if not code:
        return False
    stripped = code.strip().upper()
    return stripped and stripped not in {"N/A", "NA", "NONE"}


def _keyword_fallback(template_model, keywords: list[str]) -> list[dict]:
    """Fallback to keyword search when no code matches."""
    if not keywords:
        return []
    results = template_model.objects.active().search(" ".join(keywords)).values_list("id", "name")[:3]
    return [{"id": tid, "name": name, "score": 0.1, "codes": []} for tid, name in results]


def _build_code_template_map(fields: list) -> dict[str, set[int]]:
    """Build mapping from codes to template IDs."""
    code_templates: dict[str, set[int]] = {}
    for f in fields:
        if f.code and is_valid_code(f.code):
            code_templates.setdefault(f.code, set()).add(f.report_template_id)
    return code_templates


def _score_candidates(
    fields: list,
    weights: dict[str, float],
    total_weight: float,
    keywords: list[str],
) -> list[dict]:
    """Score template candidates by weighted code matches."""
    scores: dict[int, float] = {}
    template_codes: dict[int, set[str]] = {}
    template_refs: dict[int, any] = {}

    for f in fields:
        if f.code not in weights:
            continue
        tid = f.report_template_id
        scores[tid] = scores.get(tid, 0) + weights[f.code]
        template_codes.setdefault(tid, set()).add(f.code)
        template_refs.setdefault(tid, f.report_template)

    results = []
    for tid, score in scores.items():
        template = template_refs.get(tid)
        if not template:
            continue

        bonus = _keyword_bonus(template, keywords)
        final_score = min(1.0, (score / total_weight) + bonus)

        results.append({
            "id": tid,
            "name": template.name,
            "score": final_score,
            "codes": sorted(template_codes.get(tid, set())),
        })

    results.sort(key=lambda x: (x["score"], len(x["codes"])), reverse=True)
    return results


def _keyword_bonus(template, keywords: list[str]) -> float:
    """Calculate keyword match bonus."""
    if not keywords:
        return 0.0
    haystack = f"{template.name} {getattr(template, 'search_keywords', '')}".lower()
    hits = sum(1 for kw in keywords if kw.lower() in haystack)
    return KEYWORD_BONUS * hits


def _to_list(value) -> list[str]:
    """Convert value to list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_to_list(item))
        return result
    if isinstance(value, str):
        return [p.strip() for p in re.split(r"[,;\n]+", value) if p.strip()]
    return [str(value)]
