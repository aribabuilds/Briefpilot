from app.services.ai.explanation_parsing import parse_explanation_response


def test_parses_clean_json() -> None:
    result = parse_explanation_response('{"explanation": "This is a tax bill."}')
    assert result.explanation == "This is a tax bill."


def test_strips_markdown_code_fences() -> None:
    raw = '```json\n{"explanation": "This is a tax bill."}\n```'
    result = parse_explanation_response(raw)
    assert result.explanation == "This is a tax bill."


def test_tolerates_trailing_prose_after_the_json_object() -> None:
    raw = '{"explanation": "This is a tax bill."}\nLet me know if you need more detail.'
    result = parse_explanation_response(raw)
    assert result.explanation == "This is a tax bill."


def test_strips_surrounding_whitespace() -> None:
    result = parse_explanation_response('{"explanation": "  This is a tax bill.  "}')
    assert result.explanation == "This is a tax bill."


def test_invalid_json_falls_back_to_empty_string() -> None:
    result = parse_explanation_response("not json at all")
    assert result.explanation == ""


def test_missing_explanation_key_falls_back_to_empty_string() -> None:
    result = parse_explanation_response("{}")
    assert result.explanation == ""


def test_non_string_explanation_falls_back_to_empty_string() -> None:
    result = parse_explanation_response('{"explanation": 42}')
    assert result.explanation == ""


def test_empty_string_input_falls_back_to_empty_string() -> None:
    result = parse_explanation_response("")
    assert result.explanation == ""
