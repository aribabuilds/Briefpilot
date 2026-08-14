"""API-level tests for GET /jobs/{id}/pages/{n} (M18): the endpoint that
serves the original scan back to the frontend for the document viewer.
Uses a synchronous, OCR-free JobService (a fast stub runner) since this
endpoint's own correctness has nothing to do with OCR succeeding -- the raw
bytes are stored at create_job time regardless of pipeline outcome.
"""

import io
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.repositories.document_store import InMemoryDocumentStore
from app.repositories.job_repository import InMemoryJobRepository
from app.schemas.ocr import BBox, OcrDocument, OcrPage, OcrWord
from app.services.job_service import Executor, JobService, get_job_service


class _SyncExecutor:
    def submit(self, fn: Callable[..., object], /, *args: object) -> object:
        fn(*args)
        return None


def _stub_document() -> OcrDocument:
    words = [
        OcrWord(text="x", page=0, bbox=BBox(x=0.1, y=0.1, width=0.1, height=0.1), confidence=0.9)
    ]
    return OcrDocument(pages=[OcrPage(page=0, width=100, height=100, words=words)])


def _png_bytes(color: str = "white") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (200, 100), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf_bytes(page_count: int) -> bytes:
    pages = [Image.new("RGB", (200, 100), "white") for _ in range(page_count)]
    buffer = io.BytesIO()
    pages[0].save(buffer, format="PDF", save_all=True, append_images=pages[1:])
    return buffer.getvalue()


def _service(executor: Executor | None = None) -> JobService:
    return JobService(
        InMemoryJobRepository(),
        lambda content, ct: _stub_document(),
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
    # Construct once and close over that same instance -- assigning the
    # factory call itself (lambda: _service()) would build a fresh
    # InMemoryJobRepository on every request, so a POST and the GET right
    # after it would never see the same job (exactly the bug LEARNING.md's
    # M10 post-merge fix documents).
    service = _service()
    app.dependency_overrides[get_job_service] = lambda: service
    return TestClient(app)


def test_returns_a_png_for_an_image_upload(client: TestClient) -> None:
    created = client.post("/api/v1/jobs", files={"file": ("letter.png", _png_bytes(), "image/png")})
    job_id = created.json()["id"]

    response = client.get(f"/api/v1/jobs/{job_id}/pages/0")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    Image.open(io.BytesIO(response.content)).verify()  # valid PNG bytes


def test_returns_every_page_of_a_multipage_pdf(client: TestClient) -> None:
    created = client.post(
        "/api/v1/jobs", files={"file": ("letter.pdf", _pdf_bytes(3), "application/pdf")}
    )
    job_id = created.json()["id"]

    for page in range(3):
        response = client.get(f"/api/v1/jobs/{job_id}/pages/{page}")
        assert response.status_code == 200, page


def test_404s_for_a_page_number_past_the_last_page(client: TestClient) -> None:
    created = client.post("/api/v1/jobs", files={"file": ("letter.png", _png_bytes(), "image/png")})
    job_id = created.json()["id"]

    response = client.get(f"/api/v1/jobs/{job_id}/pages/5")
    assert response.status_code == 404


def test_404s_for_a_negative_page_number(client: TestClient) -> None:
    created = client.post("/api/v1/jobs", files={"file": ("letter.png", _png_bytes(), "image/png")})
    job_id = created.json()["id"]

    response = client.get(f"/api/v1/jobs/{job_id}/pages/-1")
    assert response.status_code == 404


def test_404s_for_an_unknown_job_id(client: TestClient) -> None:
    response = client.get("/api/v1/jobs/does-not-exist/pages/0")
    assert response.status_code == 404


def test_available_even_before_the_pipeline_finishes() -> None:
    # A stand-in executor that never actually runs the submitted work -- the
    # job stays "processing" forever. The original scan must still be
    # viewable: the bytes are stored at create_job time, independent of
    # whether OCR/classification/extraction ever complete.
    class _NeverRuns:
        def submit(self, fn: Callable[..., object], /, *args: object) -> object:
            return None

    service = _service(executor=_NeverRuns())
    app.dependency_overrides[get_job_service] = lambda: service
    client = TestClient(app)

    created = client.post("/api/v1/jobs", files={"file": ("letter.png", _png_bytes(), "image/png")})
    job_id = created.json()["id"]
    assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "processing"

    response = client.get(f"/api/v1/jobs/{job_id}/pages/0")
    assert response.status_code == 200
