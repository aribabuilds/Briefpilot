"""Extraction prompt (M9 scaffolding).

The example below is a hand-written, obviously-synthetic illustration of the
expected input/output shape — the same role the few-shot snippets play in
prompts/classify.py (see that module's docstring): prompt engineering, not
eval data. `eval/golden/` governs measured accuracy once real letters exist.

Source-span linking (pointing each value back to the OCR words it came from)
is not requested here — the model only sees flattened text, not word
positions, so it cannot honestly claim a bounding box. That link is computed
separately once the pipeline has the OcrDocument to match against (M10).
"""

EXTRACTION_SYSTEM_INSTRUCTION = """You extract structured fields from a German official letter.

Respond with strict JSON only, no markdown fences, no commentary, in exactly this shape:
{
  "sender": {"value": "<string or null>", "confidence": <0.0-1.0>},
  "letter_date": {"value": "<YYYY-MM-DD or null>", "confidence": <0.0-1.0>},
  "deadline": {"value": "<YYYY-MM-DD or null>", "confidence": <0.0-1.0>},
  "amount": {"value": "<decimal string like 184.50, or null>", "confidence": <0.0-1.0>},
  "legal_references": {"value": ["<string>", ...] or [], "confidence": <0.0-1.0>},
  "required_actions": {"value": ["<string>", ...] or [], "confidence": <0.0-1.0>}
}

If a field is not present in the letter, or you are not confident, set its
"value" to null (or [] for the two list fields) rather than guessing. Never
fabricate a date, an amount, or a legal reference that is not actually in the
text — an honest null is always better than a plausible-looking wrong answer.

Example (illustrative only, not a real letter):
Input: "Finanzamt Musterstadt. Steuerbescheid vom 01.03.2026. Bitte zahlen Sie
250,00 EUR bis 31.03.2026. Rechtsgrundlage: Paragraph 152 AO."
Output:
{
  "sender": {"value": "Finanzamt Musterstadt", "confidence": 0.95},
  "letter_date": {"value": "2026-03-01", "confidence": 0.9},
  "deadline": {"value": "2026-03-31", "confidence": 0.92},
  "amount": {"value": "250.00", "confidence": 0.9},
  "legal_references": {"value": ["Paragraph 152 AO"], "confidence": 0.85},
  "required_actions": {"value": ["Pay the amount by the deadline"], "confidence": 0.8}
}
"""


def build_extraction_user_message(content: str) -> str:
    return f"Extract structured fields from this letter:\n\n{content}"
