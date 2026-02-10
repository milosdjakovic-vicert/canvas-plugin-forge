"""Document processor protocol - orchestrates categorization, matching, and prefilling."""

from canvas_sdk.effects import Effect
from canvas_sdk.events import EventType
from canvas_sdk.protocols import BaseProtocol
from logger import log

from extend_ai_document_processor.categorize import categorize_document
from extend_ai_document_processor.effects import assign_reviewer_effect, categorize_effect, link_patient_effect
from extend_ai_document_processor.match import find_patient, find_reviewer
from extend_ai_document_processor.prefill import prefill_document_fields


class DocumentProcessor(BaseProtocol):
    """Process documents using Extend.ai for extraction and categorization."""

    RESPONDS_TO = [EventType.Name(EventType.DOCUMENT_RECEIVED)]

    def compute(self) -> list[Effect]:
        log.info("[PROCESSOR] compute() called")
        log.info("[PROCESSOR] event type: %s", self.event.type)
        log.info("[PROCESSOR] context keys: %s", list(self.event.context.keys()) if self.event.context else None)

        doc = self.event.context.get("document", {})
        doc_id, url = doc.get("id"), doc.get("content_url")
        if not doc_id or not url:
            log.warning("[PROCESSOR] Missing document id or url")
            return []

        api_key = self.secrets.get("EXTEND_AI_API_KEY")
        processor_id = self.secrets.get("EXTEND_AI_PROCESSOR_ID")
        if not api_key or not processor_id:
            log.error("[PROCESSOR] Missing Extend.ai credentials")
            return []

        available_types = self.event.context.get("available_document_types", [])

        result = categorize_document(url, available_types, api_key, processor_id)
        if result.error:
            log.error("[PROCESSOR] %s", result.error)
            return []

        patient_match = find_patient(result.extraction)
        reviewer_match = find_reviewer(result.extraction)

        if patient_match.error:
            log.warning("[PROCESSOR] %s", patient_match.error)

        effects: list[Effect] = []

        if result.document_type:
            effects.append(categorize_effect(doc_id, result.document_type, result.confidence, patient_match.error))

            if template_type := result.document_type.get("template_type"):
                effects.append(prefill_document_fields(
                    doc_id, url, template_type, result.extraction,
                    result.confidence, api_key, processor_id,
                ))

        if patient_match.found:
            effects.append(link_patient_effect(doc_id, patient_match.patient, result.confidence))

        if reviewer_match.found:
            effects.append(assign_reviewer_effect(
                doc_id, reviewer_match.reviewer, reviewer_match.auto_assigned,
                result.confidence, patient_match.error,
            ))

        effects = [e for e in effects if e]
        log.info("[PROCESSOR] Created %d effects", len(effects))
        return effects
