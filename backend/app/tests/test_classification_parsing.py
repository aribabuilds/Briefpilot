from app.schemas.classification import DocumentType
from app.services.ai.classification_parsing import parse_classification_response


def test_parses_clean_json() -> None:
    result = parse_classification_response('{"doc_type": "finanzamt", "confidence": 0.92}')
    assert result.doc_type == DocumentType.FINANZAMT
    assert result.confidence == 0.92


def test_strips_markdown_code_fences() -> None:
    raw = '```json\n{"doc_type": "krankenkasse", "confidence": 0.8}\n```'
    result = parse_classification_response(raw)
    assert result.doc_type == DocumentType.KRANKENKASSE
    assert result.confidence == 0.8


def test_normalizes_doc_type_case_and_whitespace() -> None:
    result = parse_classification_response('{"doc_type": "  Bussgeld ", "confidence": 0.5}')
    assert result.doc_type == DocumentType.BUSSGELD


def test_clamps_confidence_above_one() -> None:
    result = parse_classification_response('{"doc_type": "other", "confidence": 1.7}')
    assert result.confidence == 1.0


def test_clamps_confidence_below_zero() -> None:
    result = parse_classification_response('{"doc_type": "other", "confidence": -0.3}')
    assert result.confidence == 0.0


def test_invalid_json_falls_back_to_other_zero_confidence() -> None:
    result = parse_classification_response("not json at all")
    assert result.doc_type == DocumentType.OTHER
    assert result.confidence == 0.0


def test_unrecognized_doc_type_falls_back_to_other() -> None:
    result = parse_classification_response('{"doc_type": "something_made_up", "confidence": 0.9}')
    assert result.doc_type == DocumentType.OTHER
    assert result.confidence == 0.0


def test_missing_confidence_field_falls_back_to_other() -> None:
    result = parse_classification_response('{"doc_type": "finanzamt"}')
    assert result.doc_type == DocumentType.OTHER
    assert result.confidence == 0.0


def test_non_numeric_confidence_falls_back_to_other() -> None:
    result = parse_classification_response('{"doc_type": "finanzamt", "confidence": "high"}')
    assert result.doc_type == DocumentType.OTHER
    assert result.confidence == 0.0


def test_empty_string_falls_back_to_other() -> None:
    result = parse_classification_response("")
    assert result.doc_type == DocumentType.OTHER
    assert result.confidence == 0.0


def test_tolerates_trailing_prose_after_the_json_object() -> None:
    # Confirmed live against gemini-3.5-flash (2026-08-13): the model can
    # append explanatory text after an otherwise valid JSON object even with
    # response_mime_type="application/json" set.
    raw = '{"doc_type": "finanzamt", "confidence": 0.92}\nNote: pure JSON as requested.'
    result = parse_classification_response(raw)
    assert result.doc_type == DocumentType.FINANZAMT
    assert result.confidence == 0.92
