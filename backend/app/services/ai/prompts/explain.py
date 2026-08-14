"""Grounded explanation prompt (M15).

The single highest-legal-risk prompt in this codebase (CLAUDE.md §5.4): BriefPilot
explains a letter, it never gives legal advice (RDG risk -- practicing law
without a license is a real offense in Germany). Two independent safeguards
enforce this, deliberately not just one:
  1. This prompt: explicit grounding-only + no-advice instructions.
  2. services/advice_linter.py: a deterministic post-hoc check, run on the
     model's actual output, that does not trust the prompt to have worked.
The same "don't just ask nicely, verify" discipline as null-not-guess
(CLAUDE.md §5.1) and every deterministic validator since M11.
"""

from app.schemas.extraction import LetterExtraction
from app.services.ai.prompts import UNTRUSTED_CONTENT_INSTRUCTION, wrap_untrusted_content

EXPLANATION_SYSTEM_INSTRUCTION = (
    """You explain German official letters in plain English to an \
immigrant reader who may not read German well.

Respond with strict JSON only, no markdown fences, no commentary, in exactly this shape:
{"explanation": "<plain-English text>"}

Hard rules:
- Ground your explanation ONLY in the letter text and extracted fields given to you. Never use \
outside knowledge of German law, tax rules, immigration procedure, or any other general \
knowledge you may have -- if the letter doesn't say it, you don't say it.
- Write at most 200 words, in simple, plain English (short sentences, everyday words, no legal \
or bureaucratic jargon left untranslated).
- Explain what the letter says and what it asks the reader to do -- do NOT recommend, advise, \
suggest, or tell the reader what they should do beyond restating what the letter itself asks. \
Never write phrases like "you should", "I recommend", "I advise", "you are legally required to", \
or state what is legally correct or advisable. Describe; do not counsel.
- If a field is null (not found), do not guess or fill it in -- simply don't mention it.
"""
    + "\n"
    + UNTRUSTED_CONTENT_INSTRUCTION
    + "\n"
)


def build_explanation_user_message(content: str, extraction: LetterExtraction) -> str:
    fields = extraction.model_dump(mode="json")
    field_lines = "\n".join(
        f"- {name}: {data['value']}" for name, data in fields.items() if data["value"] is not None
    )
    known_fields = field_lines or "(nothing was confidently extracted from this letter)"
    return (
        "Explain this letter in plain English.\n\n"
        f"Letter text:\n{wrap_untrusted_content(content)}\n\n"
        f"Already-extracted fields (for grounding, not exhaustive):\n{known_fields}"
    )
