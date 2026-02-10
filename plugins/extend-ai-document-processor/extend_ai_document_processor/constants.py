"""Constants for extend-ai-document-processor."""


class AnnotationColor:
    """Colors for document annotations."""

    CONFIDENCE = "#00AA00"
    ERROR = "#F44336"
    AUTO_ASSIGNED = "#9C27B0"


# Extend.ai API
API_URL = "https://api.extend.ai/processor_runs"
API_VERSION = "2025-04-21"
MAX_RETRIES = 2

# Template matching
SCORE_THRESHOLD = 0.3
GAP_FILL_THRESHOLD = 0.05
MAX_FIELDS = 120
KEYWORD_BONUS = 0.05
