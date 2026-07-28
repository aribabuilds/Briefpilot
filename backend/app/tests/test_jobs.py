from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings, get_settings
from app.main import app
from app.repositories.job_repository import InMemoryJobRepository
from app.schemas.job import JobStatus
from app.schemas.ocr import BBox, OcrDocument, OcrPage, OcrWord
from app.services.job_service import JobService, get_job_service

PDF = ("letter.pdf", b"%PDF-1.4 fake", "application/pdf")


class _SyncExecutor:
    """Runs the submitted work inline, so job completion is deterministic in tests."""

    def submit(self, fn: Callable[..., object], /, *args: object) -> object:
        fn(*args)
        return None


def _document(text: str) -> OcrDocument:
    word = OcrWord(
        text=text, page=0, bbox=BBox(x=0.1, y=0.1, width=0.2, height=0.1), confidence=0.8
    )
    return OcrDocument(pages=[OcrPage(page=0, width=1000, height=500, words=[word])])


def _service_with(runner: Callable[[bytes, str], OcrDocument]) -> JobService:
    return JobService(InMemoryJobRepository(), runner, _SyncExecutor())


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
    _override_service(_service_with(lambda content, ct: _document("Finanzamt")))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["text"] == "Finanzamt"
    assert body["result"]["word_count"] == 1
    assert body["result"]["page_count"] == 1
    assert body["result"]["mean_confidence"] == pytest.approx(0.8)
    assert body["error"] is None


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
