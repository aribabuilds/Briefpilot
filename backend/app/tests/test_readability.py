from app.services.readability import (
    MAX_WORD_COUNT,
    MIN_FLESCH_READING_EASE,
    assess_readability,
    flesch_reading_ease,
    word_count,
)

_SIMPLE_TEXT = "This is a simple letter. It asks you to pay a fee. The fee is due soon."
_COMPLEX_TEXT = (
    "The aforementioned correspondence necessitates immediate remittance of the "
    "outstanding pecuniary obligation, notwithstanding any procedural objections "
    "the addressee may otherwise be inclined to raise regarding jurisdictional propriety."
)


def test_word_count_counts_words_not_punctuation() -> None:
    assert word_count("Hello, world! This is a test.") == 6


def test_word_count_is_zero_for_empty_string() -> None:
    assert word_count("") == 0


def test_flesch_reading_ease_scores_simple_text_higher_than_complex_text() -> None:
    simple_score = flesch_reading_ease(_SIMPLE_TEXT)
    complex_score = flesch_reading_ease(_COMPLEX_TEXT)
    assert simple_score > complex_score


def test_flesch_reading_ease_is_zero_for_empty_string() -> None:
    assert flesch_reading_ease("") == 0.0


def test_assess_readability_passes_simple_text() -> None:
    assessment = assess_readability(_SIMPLE_TEXT)
    assert assessment.word_count == word_count(_SIMPLE_TEXT)
    assert not assessment.exceeds_word_limit
    assert not assessment.below_readability_target


def test_assess_readability_flags_text_over_the_word_limit() -> None:
    long_text = " ".join(["word"] * (MAX_WORD_COUNT + 1)) + "."
    assessment = assess_readability(long_text)
    assert assessment.word_count == MAX_WORD_COUNT + 1
    assert assessment.exceeds_word_limit


def test_assess_readability_does_not_flag_text_at_exactly_the_word_limit() -> None:
    text = " ".join(["word"] * MAX_WORD_COUNT) + "."
    assessment = assess_readability(text)
    assert not assessment.exceeds_word_limit


def test_assess_readability_flags_low_readability_text() -> None:
    assessment = assess_readability(_COMPLEX_TEXT)
    assert assessment.flesch_reading_ease < MIN_FLESCH_READING_EASE
    assert assessment.below_readability_target
