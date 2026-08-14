"""API-level test proving M24's rate limiter is actually wired into the
upload/delete endpoints, not just correct in isolation (test_rate_limiter.py
already covers RateLimiter's own logic). Overrides get_upload_rate_limiter
with a tiny, dedicated instance so this is deterministic without needing to
fire 20+ requests to hit the real default limit.
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.document_store import InMemoryDocumentStore
from app.repositories.job_repository import InMemoryJobRepository
from app.schemas.ocr import BBox, OcrDocument, OcrPage, OcrWord
from app.services.job_service import Executor, JobService, get_job_service
from app.services.rate_limiter import RateLimiter, get_upload_rate_limiter

PDF = ("letter.pdf", b"%PDF-1.4 fake", "application/pdf")


class _SyncExecutor:
    def submit(self, fn: Callable[..., object], /, *args: object) -> object:
        fn(*args)
        return None


def _document() -> OcrDocument:
    words = [
        OcrWord(text="x", page=0, bbox=BBox(x=0.1, y=0.1, width=0.1, height=0.1), confidence=0.9)
    ]
    return OcrDocument(pages=[OcrPage(page=0, width=100, height=100, words=words)])


def _service(executor: Executor | None = None) -> JobService:
    return JobService(
        InMemoryJobRepository(),
        lambda content, ct: _document(),
        executor or _SyncExecutor(),
        min_mean_confidence=0.5,
        min_word_count=1,
        document_store=InMemoryDocumentStore(),
    )


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    # Construct both the service and the limiter once and close over those
    # same instances -- assigning the factory call itself (lambda:
    # RateLimiter(...)) would build a fresh, empty-history limiter on every
    # single request, so no request would ever see a prior one's hits and
    # the 429 path could never trigger. Exactly the bug class
    # LEARNING.md's M10 post-merge fix documents, just for a limiter instead
    # of a repository.
    service = _service()
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    app.dependency_overrides[get_job_service] = lambda: service
    app.dependency_overrides[get_upload_rate_limiter] = lambda: limiter
    return TestClient(app)


def test_the_second_upload_within_the_window_is_rejected_with_429(client: TestClient) -> None:
    first = client.post("/api/v1/jobs", files={"file": PDF})
    assert first.status_code == 201

    second = client.post("/api/v1/jobs", files={"file": PDF})
    assert second.status_code == 429
    assert "Retry-After" in second.headers


def test_a_rejected_upload_never_reaches_job_creation(client: TestClient) -> None:
    client.post("/api/v1/jobs", files={"file": PDF})  # consumes the 1-request budget
    before = client.get("/api/v1/jobs/does-not-exist").status_code  # sanity: unrelated to the limit
    assert before == 404

    rejected = client.post("/api/v1/jobs", files={"file": PDF})
    assert rejected.status_code == 429
    # No job was created for the rejected request -- the guard runs before the handler.
    assert rejected.json()["detail"] == "Too many requests. Please wait a moment and try again."


def test_delete_is_rate_limited_too(client: TestClient) -> None:
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]
    # The upload itself already spent the shared 1-request budget for this IP.
    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 429
