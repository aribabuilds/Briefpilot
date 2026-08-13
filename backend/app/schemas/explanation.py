"""JobResult-level explanation contract (M15). Wraps the raw AI adapter
output (app.schemas.ai.DocumentExplanationResult) with the deterministic
checks computed afterward -- same split as extraction's ExtractedField vs.
the raw LLM response (M9/M10/M11): what the model claims, plus what we can
verify about that claim, kept as separate fields rather than silently
folded into (or hidden behind) the text itself.
"""

from pydantic import BaseModel


class ExplanationResult(BaseModel):
    text: str
    word_count: int
    flesch_reading_ease: float
    # True when word_count > readability.MAX_WORD_COUNT or
    # flesch_reading_ease < readability.MIN_FLESCH_READING_EASE. Flagged, not
    # corrected -- truncating or rewriting prose risks producing something
    # worse than an honest "this ran long" signal (same non-negotiable as
    # every deterministic check since M11).
    exceeds_word_limit: bool
    below_readability_target: bool
    # Machine-readable codes from services/advice_linter.py, e.g. "you_should".
    # Empty means the linter found nothing. CLAUDE.md §5.4: BriefPilot
    # explains, it never gives legal advice -- a non-empty list here is the
    # single most important field on this whole object.
    advice_phrases_found: list[str]
