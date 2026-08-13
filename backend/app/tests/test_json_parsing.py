from app.services.ai.json_parsing import extract_json_value


def test_extracts_clean_json_object() -> None:
    assert extract_json_value('{"a": 1}') == {"a": 1}


def test_strips_markdown_code_fences() -> None:
    assert extract_json_value('```json\n{"a": 1}\n```') == {"a": 1}


def test_tolerates_trailing_prose_after_a_valid_json_object() -> None:
    # Confirmed live against gemini-3.5-flash (2026-08-13): the model appended
    # an explanatory sentence after an otherwise perfect JSON object despite
    # response_mime_type="application/json" -- plain json.loads rejects this
    # outright, which used to silently degrade a correct extraction to null.
    raw = '{"a": 1}\nNote: the above is valid JSON per your request.'
    assert extract_json_value(raw) == {"a": 1}


def test_tolerates_trailing_prose_after_a_json_list() -> None:
    raw = '["x", "y"]\nHope that helps!'
    assert extract_json_value(raw) == ["x", "y"]


def test_tolerates_leading_prose_before_a_valid_json_object() -> None:
    # Confirmed live: a second real gemini-3.5-flash call wrapped the JSON
    # with prose BEFORE it instead of after -- still a 200 OK, still
    # response_mime_type="application/json", still not pure JSON.
    raw = 'Sure, here is the JSON: {"a": 1}'
    assert extract_json_value(raw) == {"a": 1}


def test_tolerates_prose_on_both_sides_of_the_json_value() -> None:
    raw = 'Here you go:\n{"a": 1}\nLet me know if you need anything else.'
    assert extract_json_value(raw) == {"a": 1}


def test_returns_none_for_completely_invalid_input() -> None:
    assert extract_json_value("not json at all") is None


def test_returns_none_for_empty_string() -> None:
    assert extract_json_value("") is None


def test_returns_none_for_a_truncated_json_object() -> None:
    assert extract_json_value('{"a": 1,') is None
