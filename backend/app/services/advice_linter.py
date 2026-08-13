"""Flags phrases that read as legal advice rather than a grounded explanation
of a letter's own content -- CLAUDE.md §5.4's core compliance requirement:
"BriefPilot explains; it never gives legal advice (RDG risk)." Giving legal
advice without a license is a real offense in Germany (Rechtsdienst-
leistungsgesetz), not a style preference.

A deterministic post-hoc check on the model's actual output, deliberately
independent of the explanation prompt's own no-advice instructions
(prompts/explain.py) -- the same "don't just ask nicely, verify" discipline
every deterministic validator in this codebase follows since M11. Curated,
not exhaustive: a phrase-pattern linter can only catch surface patterns, not
every way a model could phrase advice, and is not a substitute for a human
legal review before this product handles real user-facing legal risk at
scale -- it is a floor, not a guarantee.
"""

import re

# Machine-readable code -> pattern. Deliberately phrased to catch the model
# directly counseling the reader ("you should...", "I recommend...") without
# flagging the model merely restating what the letter itself demands (e.g.
# "the letter states you must respond by March 31" is not advice; it is a
# faithful restatement of the letter's own content).
_ADVICE_PATTERNS: dict[str, re.Pattern[str]] = {
    "you_should": re.compile(r"\byou should\b", re.IGNORECASE),
    "you_need_to": re.compile(r"\byou need to\b", re.IGNORECASE),
    "i_recommend": re.compile(r"\bi recommend\b", re.IGNORECASE),
    "i_advise": re.compile(r"\bi advise\b", re.IGNORECASE),
    "my_advice": re.compile(r"\bmy advice\b", re.IGNORECASE),
    "in_my_opinion": re.compile(r"\bin my opinion\b", re.IGNORECASE),
    "it_is_advisable": re.compile(r"\bit is advisable\b", re.IGNORECASE),
    "you_are_legally_required": re.compile(r"\byou are legally required\b", re.IGNORECASE),
    "you_have_no_choice": re.compile(r"\byou have no choice\b", re.IGNORECASE),
    "your_best_option": re.compile(r"\byour best option\b", re.IGNORECASE),
}


def find_advice_phrases(text: str) -> list[str]:
    return [code for code, pattern in _ADVICE_PATTERNS.items() if pattern.search(text)]
