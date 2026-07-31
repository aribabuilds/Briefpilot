from enum import StrEnum

from pydantic import BaseModel


# The 8 in-scope letter types from CLAUDE.md §1. Frozen alongside the OCR
# schema in spirit: extraction (M9+) and the eval scorecard (M12) both key off
# these exact values.
class DocumentType(StrEnum):
    FINANZAMT = "finanzamt"
    AUSLAENDERBEHOERDE = "auslaenderbehoerde"
    KRANKENKASSE = "krankenkasse"
    BUSSGELD = "bussgeld"
    RUNDFUNKBEITRAG = "rundfunkbeitrag"
    JOBCENTER = "jobcenter"
    RENTAL_UTILITY = "rental_utility"
    OTHER = "other"


class ClassificationRequest(BaseModel):
    content: str


class ClassificationResult(BaseModel):
    doc_type: DocumentType
    confidence: float  # [0, 1]
