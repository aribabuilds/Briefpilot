"""Parses an LLM's raw JSON text response into a DocumentExplanationResult.

Shares extract_json_value with classification_parsing.py and
extraction_parsing.py (same reasoning as D19/M9's parser split) -- including
its tolerance for the leading/trailing prose a provider sometimes wraps
around an otherwise-valid JSON object even with response_mime_type=
"application/json" set (confirmed live, see LEARNING.md's M14 post-merge fix).

Never raises: malformed JSON or a missing/wrong-typed "explanation" key
degrades to an empty string rather than crashing the caller -- the same
null-not-guess instinct as the other two parsers. An empty explanation is a
real, representable "could not generate one" state, not a guess.
"""

from app.schemas.ai import DocumentExplanationResult
from app.services.ai.json_parsing import extract_json_value


def parse_explanation_response(raw_text: str) -> DocumentExplanationResult:
    data = extract_json_value(raw_text)
    if not isinstance(data, dict):
        return DocumentExplanationResult(explanation="")
    explanation = data.get("explanation")
    if not isinstance(explanation, str):
        return DocumentExplanationResult(explanation="")
    return DocumentExplanationResult(explanation=explanation.strip())
