from app.services.advice_linter import find_advice_phrases


def test_finds_you_should() -> None:
    assert "you_should" in find_advice_phrases("You should pay this immediately.")


def test_finds_i_recommend() -> None:
    assert "i_recommend" in find_advice_phrases("I recommend contesting this fine.")


def test_finds_i_advise() -> None:
    assert "i_advise" in find_advice_phrases("I advise you to ignore this letter.")


def test_finds_in_my_opinion() -> None:
    assert "in_my_opinion" in find_advice_phrases("In my opinion, this fine is unfair.")


def test_finds_legally_required_phrasing() -> None:
    text = "You are legally required to pay within 14 days."
    assert "you_are_legally_required" in find_advice_phrases(text)


def test_finds_no_choice_phrasing() -> None:
    assert "you_have_no_choice" in find_advice_phrases("You have no choice but to comply.")


def test_finds_your_best_option_phrasing() -> None:
    assert "your_best_option" in find_advice_phrases("Paying now is your best option.")


def test_is_case_insensitive() -> None:
    assert "you_should" in find_advice_phrases("YOU SHOULD pay this now.")


def test_clean_explanation_has_no_advice_phrases() -> None:
    text = (
        "This letter is from the Finanzamt. It states you owe 250 EUR in taxes. "
        "The letter asks for payment by March 31, 2026."
    )
    assert find_advice_phrases(text) == []


def test_restating_the_letters_own_deadline_is_not_flagged() -> None:
    # Describing what the letter demands is not the same as advising the
    # reader what to do -- this phrasing avoids every curated pattern.
    text = "The letter states that payment is due by March 31, 2026."
    assert find_advice_phrases(text) == []


def test_finds_multiple_distinct_phrases_in_one_text() -> None:
    text = "I recommend you pay now. In my opinion, this is your best option."
    found = find_advice_phrases(text)
    assert "i_recommend" in found
    assert "in_my_opinion" in found
    assert "your_best_option" in found
