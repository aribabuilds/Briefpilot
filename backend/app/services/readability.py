"""Deterministic readability checks for a generated explanation (M15,
CLAUDE.md §1.2: "≤200 words, B1 readability"). A post-hoc CHECK on the
model's actual output, not a rewriter -- same discipline as validators.py
(M11): a violation is flagged, never silently truncated or "fixed", because
truncating prose can cut it off mid-sentence and produce something worse
than an honest flag.

Flesch Reading Ease is the standard deterministic English readability
metric; CEFR's B1 has no single agreed numeric equivalent, so
MIN_FLESCH_READING_EASE is a placeholder aimed at the "Standard" band
(60-70) of the classic Flesch scale, pending real user testing (M21: "2
non-native testers on real phones") -- the same posture as every other
threshold in this codebase (M6, M10, M11).
"""

import re
from dataclasses import dataclass

MAX_WORD_COUNT = 200
MIN_FLESCH_READING_EASE = 60.0

_WORD_RE = re.compile(r"[A-Za-z']+")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _sentence_count(text: str) -> int:
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return max(len(sentences), 1)


def _count_syllables(word: str) -> int:
    # Standard heuristic: count vowel groups, drop one for a silent trailing
    # "e", floor at 1 -- not linguistically exact, but exact enough for a
    # readability *estimate*, the same tolerance the Flesch formula itself
    # assumes.
    lowered = word.lower()
    count = len(_VOWEL_GROUP_RE.findall(lowered))
    if lowered.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_reading_ease(text: str) -> float:
    words = _WORD_RE.findall(text)
    if not words:
        return 0.0
    sentences = _sentence_count(text)
    syllables = sum(_count_syllables(w) for w in words)
    total_words = len(words)
    score = 206.835 - 1.015 * (total_words / sentences) - 84.6 * (syllables / total_words)
    return round(score, 1)


@dataclass(frozen=True)
class ReadabilityAssessment:
    word_count: int
    flesch_reading_ease: float
    exceeds_word_limit: bool
    below_readability_target: bool


def assess_readability(text: str) -> ReadabilityAssessment:
    words = word_count(text)
    score = flesch_reading_ease(text)
    return ReadabilityAssessment(
        word_count=words,
        flesch_reading_ease=score,
        exceeds_word_limit=words > MAX_WORD_COUNT,
        below_readability_target=score < MIN_FLESCH_READING_EASE,
    )
