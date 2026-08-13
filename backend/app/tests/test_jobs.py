from collections.abc import Callable, Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings, get_settings
from app.main import app
from app.repositories.job_repository import InMemoryJobRepository
from app.schemas.classification import ClassificationResult, DocumentType
from app.schemas.extraction import ExtractedField, LetterExtraction
from app.schemas.job import JobStatus
from app.schemas.ocr import BBox, OcrDocument, OcrPage, OcrWord
from app.services.job_service import ClassifierRunner, ExtractorRunner, JobService, get_job_service

PDF = ("letter.pdf", b"%PDF-1.4 fake", "application/pdf")


class _SyncExecutor:
    """Runs the submitted work inline, so job completion is deterministic in tests."""

    def submit(self, fn: Callable[..., object], /, *args: object) -> object:
        fn(*args)
        return None


def _document(text: str, *, words: int = 10, confidence: float = 0.8) -> OcrDocument:
    page_words = [
        OcrWord(
            text=text, page=0, bbox=BBox(x=0.1, y=0.1, width=0.2, height=0.1), confidence=confidence
        )
        for _ in range(words)
    ]
    return OcrDocument(pages=[OcrPage(page=0, width=1000, height=500, words=page_words)])


def _service_with(
    runner: Callable[[bytes, str], OcrDocument],
    *,
    classifier: ClassifierRunner | None = None,
    extractor: ExtractorRunner | None = None,
) -> JobService:
    return JobService(
        InMemoryJobRepository(),
        runner,
        _SyncExecutor(),
        min_mean_confidence=0.5,
        min_word_count=5,
        classifier=classifier,
        extractor=extractor,
    )


def _empty_extraction() -> LetterExtraction:
    return LetterExtraction(
        sender=ExtractedField(value=None, confidence=0.0),
        letter_date=ExtractedField(value=None, confidence=0.0),
        deadline=ExtractedField(value=None, confidence=0.0),
        amount=ExtractedField(value=None, confidence=0.0),
        legal_references=ExtractedField(value=None, confidence=0.0),
        required_actions=ExtractedField(value=None, confidence=0.0),
    )


def _override_service(service: JobService) -> None:
    app.dependency_overrides[get_job_service] = lambda: service


def _override_settings(**kwargs: object) -> None:
    settings = Settings(**kwargs)  # type: ignore[arg-type]
    app.dependency_overrides[get_settings] = lambda: settings


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# --- upload -> poll -> result (synchronous executor, faked pipeline) -------


def test_upload_returns_201_processing(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("Finanzamt")))
    response = client.post("/api/v1/jobs", files={"file": PDF})
    assert response.status_code == 201
    assert response.json()["status"] == JobStatus.PROCESSING.value


def test_completed_job_carries_extracted_text_and_summary(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("Finanzamt", words=10)))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.DONE.value
    assert "Finanzamt" in body["result"]["text"]
    assert body["result"]["word_count"] == 10
    assert body["result"]["page_count"] == 1
    assert body["result"]["mean_confidence"] == pytest.approx(0.8)
    assert body["error"] is None


# --- classification wiring (M8) -------------------------------------------


def test_successful_classification_populates_doc_type(client: TestClient) -> None:
    def classify(text: str) -> ClassificationResult:
        return ClassificationResult(doc_type=DocumentType.FINANZAMT, confidence=0.87)

    _override_service(
        _service_with(lambda content, ct: _document("Finanzamt"), classifier=classify)
    )
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["doc_type"] == DocumentType.FINANZAMT.value
    assert body["result"]["doc_type_confidence"] == pytest.approx(0.87)


def test_classifier_failure_leaves_doc_type_null_but_job_still_done(client: TestClient) -> None:
    def boom(text: str) -> ClassificationResult:
        raise RuntimeError("GEMINI_API_KEY must be set when AI_PROVIDER=gemini.")

    _override_service(_service_with(lambda content, ct: _document("Finanzamt"), classifier=boom))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    # Null-not-guess: no LLM key configured degrades the field, not the job.
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["doc_type"] is None
    assert body["result"]["doc_type_confidence"] is None
    assert body["result"]["text"]  # OCR output is unaffected


def test_no_classifier_configured_leaves_doc_type_null(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("Finanzamt"), classifier=None))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["doc_type"] is None


def test_classification_is_skipped_for_low_quality_documents(client: TestClient) -> None:
    calls: list[str] = []

    def classify(text: str) -> ClassificationResult:
        calls.append(text)
        return ClassificationResult(doc_type=DocumentType.FINANZAMT, confidence=0.9)

    _override_service(
        _service_with(
            lambda content, ct: _document("blur", words=10, confidence=0.2),
            classifier=classify,
        )
    )
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.LOW_QUALITY.value
    assert calls == []  # garbled OCR text is never sent to the classifier


# --- extraction wiring (M10) -----------------------------------------------


def test_successful_extraction_populates_result(client: TestClient) -> None:
    def extract(text: str) -> LetterExtraction:
        extraction = _empty_extraction()
        return extraction.model_copy(
            update={"sender": ExtractedField(value="Finanzamt Muenchen", confidence=0.9)}
        )

    _override_service(_service_with(lambda content, ct: _document("Finanzamt"), extractor=extract))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["extraction"]["sender"]["value"] == "Finanzamt Muenchen"


def test_extraction_links_source_spans_against_the_real_ocr_document(client: TestClient) -> None:
    # The OCR document's words literally contain "Finanzamt" -- JobService
    # must call link_source_spans with that same document, not just store the
    # AI adapter's raw (always source_span=None) result untouched.
    def extract(text: str) -> LetterExtraction:
        extraction = _empty_extraction()
        return extraction.model_copy(
            update={"sender": ExtractedField(value="Finanzamt", confidence=0.9)}
        )

    _override_service(
        _service_with(lambda content, ct: _document("Finanzamt", words=5), extractor=extract)
    )
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    sender = body["result"]["extraction"]["sender"]
    assert sender["source_span"] is not None
    assert sender["confidence"] == pytest.approx(0.9)  # verified, not capped


def test_extractor_failure_leaves_extraction_null_but_job_still_done(client: TestClient) -> None:
    def boom(text: str) -> LetterExtraction:
        raise RuntimeError("GEMINI_API_KEY must be set when AI_PROVIDER=gemini.")

    _override_service(_service_with(lambda content, ct: _document("Finanzamt"), extractor=boom))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["extraction"] is None
    assert body["result"]["text"]  # OCR output is unaffected


def test_no_extractor_configured_leaves_extraction_null(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("Finanzamt"), extractor=None))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["extraction"] is None


def test_extraction_is_skipped_for_low_quality_documents(client: TestClient) -> None:
    calls: list[str] = []

    def extract(text: str) -> LetterExtraction:
        calls.append(text)
        return _empty_extraction()

    _override_service(
        _service_with(
            lambda content, ct: _document("blur", words=10, confidence=0.2),
            extractor=extract,
        )
    )
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.LOW_QUALITY.value
    assert calls == []  # garbled OCR text is never sent to extraction either


def test_classification_and_extraction_are_independent(client: TestClient) -> None:
    # Classification fails, extraction succeeds -- neither should affect the other.
    def boom_classify(text: str) -> ClassificationResult:
        raise RuntimeError("classifier down")

    def extract(text: str) -> LetterExtraction:
        extraction = _empty_extraction()
        return extraction.model_copy(
            update={"sender": ExtractedField(value="Finanzamt", confidence=0.9)}
        )

    _override_service(
        _service_with(
            lambda content, ct: _document("Finanzamt"),
            classifier=boom_classify,
            extractor=extract,
        )
    )
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["doc_type"] is None  # classification failed
    assert body["result"]["extraction"]["sender"]["value"] == "Finanzamt"  # extraction still ran


# --- deterministic validation wiring (M11) ----------------------------------


def test_validation_flags_deadline_before_letter_date_through_the_full_pipeline(
    client: TestClient,
) -> None:
    def extract(text: str) -> LetterExtraction:
        extraction = _empty_extraction()
        return extraction.model_copy(
            update={
                "letter_date": ExtractedField(value=date(2026, 3, 10), confidence=0.9),
                "deadline": ExtractedField(value=date(2026, 3, 1), confidence=0.9),
            }
        )

    _override_service(_service_with(lambda content, ct: _document("Finanzamt"), extractor=extract))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    deadline = body["result"]["extraction"]["deadline"]
    assert deadline["value"] == "2026-03-01"  # value preserved, not corrected
    assert deadline["confidence"] == pytest.approx(0.2)
    assert "deadline_before_letter_date" in deadline["validation_issues"]


def test_validation_leaves_consistent_values_unflagged_through_the_full_pipeline(
    client: TestClient,
) -> None:
    def extract(text: str) -> LetterExtraction:
        extraction = _empty_extraction()
        return extraction.model_copy(
            update={
                "letter_date": ExtractedField(value=date(2026, 3, 1), confidence=0.9),
                "deadline": ExtractedField(value=date(2026, 3, 31), confidence=0.9),
            }
        )

    _override_service(_service_with(lambda content, ct: _document("Finanzamt"), extractor=extract))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    deadline = body["result"]["extraction"]["deadline"]
    # Semantically consistent, so no *validation* flag -- but the OCR fixture's
    # text ("Finanzamt") never contains this date, so M10's source-span
    # linking still caps it as unverified. The two mechanisms are independent:
    # this proves validation doesn't re-flag (or further downgrade) a value
    # that already failed a different, earlier check for a different reason.
    assert deadline["validation_issues"] == []
    assert deadline["confidence"] == pytest.approx(0.4)


def test_low_confidence_document_is_marked_low_quality(client: TestClient) -> None:
    _override_service(
        _service_with(lambda content, ct: _document("blur", words=10, confidence=0.2))
    )
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    # OCR ran, so it's not FAILED — but the output is too weak to show.
    assert body["status"] == JobStatus.LOW_QUALITY.value
    assert body["result"]["mean_confidence"] == pytest.approx(0.2)


def test_too_few_words_is_marked_low_quality(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("hi", words=2, confidence=0.9)))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.LOW_QUALITY.value


def test_pipeline_failure_marks_job_failed(client: TestClient) -> None:
    def boom(content: bytes, content_type: str) -> OcrDocument:
        raise RuntimeError("pipeline exploded")

    _override_service(_service_with(boom))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.FAILED.value
    assert body["result"] is None
    assert "pipeline exploded" in body["error"]


def test_unknown_job_returns_404(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("x")))
    assert client.get("/api/v1/jobs/nope").status_code == 404


# --- rejection paths at the API boundary ----------------------------------


def test_unsupported_content_type_returns_415(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("x")))
    response = client.post("/api/v1/jobs", files={"file": ("n.txt", b"hi", "text/plain")})
    assert response.status_code == 415


def test_empty_file_returns_400(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("x")))
    response = client.post("/api/v1/jobs", files={"file": ("letter.pdf", b"", "application/pdf")})
    assert response.status_code == 400


def test_oversize_file_returns_413(client: TestClient) -> None:
    _override_service(_service_with(lambda content, ct: _document("x")))
    _override_settings(max_upload_bytes=8)
    response = client.post(
        "/api/v1/jobs",
        files={"file": ("letter.pdf", b"%PDF-1.4 too big", "application/pdf")},
    )
    assert response.status_code == 413
