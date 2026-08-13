from pydantic import BaseModel

from app.schemas.extraction import LetterExtraction


class DocumentExtractionRequest(BaseModel):
    content: str


class DocumentExplanationRequest(BaseModel):
    content: str
    # The already-extracted (and, by the time JobService calls this, already
    # validated/source-linked) fields -- CLAUDE.md §1.2 grounds the
    # explanation in "the document text + extracted fields", not text alone.
    # May be all-null fields if extraction itself failed; still valid input.
    extraction: LetterExtraction


class DocumentExplanationResult(BaseModel):
    # Raw model output. Word count, readability, and advice-phrase checks are
    # computed afterward by services/readability.py and
    # services/advice_linter.py -- the same split M10/M11 established between
    # "what the model claims" and "what we can verify about that claim".
    explanation: str
