"""Classification prompt.

The few-shot snippets below are hand-written prompt-engineering examples, not
eval data — they exist to show the model the shape of each letter type, the
same role a few lines of an interface's docstring play for a human reader.
They are NOT a substitute for the golden-letter set: `eval/golden/` (M6)
governs measured accuracy, and fabricating "realistic" eval fixtures would
defeat the entire point of that suite (see its README). Real accuracy
measurement is deferred to M12/M13 once real letters exist.
"""

from app.schemas.classification import DocumentType
from app.services.ai.prompts import UNTRUSTED_CONTENT_INSTRUCTION, wrap_untrusted_content

_DOC_TYPES = ", ".join(t.value for t in DocumentType)

CLASSIFICATION_SYSTEM_INSTRUCTION = f"""You classify German official letters by sender type.

Respond with strict JSON only, no markdown fences, no commentary:
{{"doc_type": "<one of: {_DOC_TYPES}>", "confidence": <number 0.0-1.0>}}

If the letter does not clearly match one of the specific types, or you are
unsure, respond with "other" and a low confidence rather than guessing.

{UNTRUSTED_CONTENT_INSTRUCTION}

Examples (illustrative only, not real letters):
- A letter from a "Finanzamt" about "Steuerbescheid", "Einkommensteuer", or a
  tax ID ("Steuernummer") -> finanzamt
- A letter from an "Ausländerbehörde" about a residence permit
  ("Aufenthaltstitel") or visa status -> auslaenderbehoerde
- A letter from a health insurer ("Krankenkasse") about
  "Versichertennummer" or "Beitragsbescheid" -> krankenkasse
- A letter about a fine ("Bußgeldbescheid", a traffic violation) -> bussgeld
- A letter from "ARD ZDF Deutschlandradio Beitragsservice" about the
  broadcasting fee ("Rundfunkbeitrag") -> rundfunkbeitrag
- A letter from a "Jobcenter" about unemployment benefits
  ("Arbeitslosengeld", "Bürgergeld") -> jobcenter
- A letter from a landlord or utility provider about rent ("Miete") or a
  utility bill ("Nebenkostenabrechnung") -> rental_utility
- Anything else, or a letter too unclear to tell -> other
"""


def build_classification_user_message(content: str) -> str:
    return f"Classify this letter:\n\n{wrap_untrusted_content(content)}"
