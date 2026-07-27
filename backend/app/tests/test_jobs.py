from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings, get_settings
from app.main import app
from app.repositories.job_repository import InMemoryJobRepository
from app.schemas.job import JobStatus
from app.services.job_service import JobService, get_job_service

PDF = ("letter.pdf", b"%PDF-1.4 fake", "application/pdf")


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


# --- HTTP layer: upload -> poll -> result ---------------------------------


def test_upload_returns_201_with_processing_status(client: TestClient) -> None:
    # A large delay keeps the job in "processing" so the state is observable.
    _override_service(JobService(InMemoryJobRepository(), processing_delay_seconds=3600))
    response = client.post("/api/v1/jobs", files={"file": PDF})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == JobStatus.PROCESSING.value
    assert body["id"]


def test_poll_before_delay_still_processing(client: TestClient) -> None:
    _override_service(JobService(InMemoryJobRepository(), processing_delay_seconds=3600))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == JobStatus.PROCESSING.value
    assert body["result"] is None


def test_poll_after_delay_returns_done_with_result(client: TestClient) -> None:
    # Zero delay: the job completes by the first poll, exercising the transition.
    _override_service(JobService(InMemoryJobRepository(), processing_delay_seconds=0))
    job_id = client.post("/api/v1/jobs", files={"file": PDF}).json()["id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == JobStatus.DONE.value
    assert body["result"]["filename"] == "letter.pdf"
    assert body["result"]["message"]


def test_unknown_job_returns_404(client: TestClient) -> None:
    _override_service(JobService(InMemoryJobRepository(), processing_delay_seconds=0))
    assert client.get("/api/v1/jobs/does-not-exist").status_code == 404


# --- HTTP layer: rejection paths ------------------------------------------


def test_unsupported_content_type_returns_415(client: TestClient) -> None:
    _override_service(JobService(InMemoryJobRepository(), processing_delay_seconds=0))
    response = client.post(
        "/api/v1/jobs",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_empty_file_returns_400(client: TestClient) -> None:
    _override_service(JobService(InMemoryJobRepository(), processing_delay_seconds=0))
    response = client.post(
        "/api/v1/jobs",
        files={"file": ("letter.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400


def test_oversize_file_returns_413(client: TestClient) -> None:
    _override_service(JobService(InMemoryJobRepository(), processing_delay_seconds=0))
    _override_settings(max_upload_bytes=8)
    response = client.post(
        "/api/v1/jobs",
        files={"file": ("letter.pdf", b"%PDF-1.4 too big", "application/pdf")},
    )
    assert response.status_code == 413


# --- service layer: state machine driven by an injected clock -------------


def test_service_transitions_processing_to_done_on_clock_advance() -> None:
    now = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)
    clock = lambda: now  # noqa: E731 - trivial fixed clock for the test
    service = JobService(InMemoryJobRepository(), processing_delay_seconds=2, clock=clock)

    job = service.create_job(filename="x.pdf")
    assert service.get_job(job.id) is not None
    assert job.status is JobStatus.PROCESSING

    fetched = service.get_job(job.id)
    assert fetched is not None and fetched.status is JobStatus.PROCESSING

    now = now + timedelta(seconds=2)
    completed = service.get_job(job.id)
    assert completed is not None
    assert completed.status is JobStatus.DONE
    assert completed.result is not None
    assert completed.result.filename == "x.pdf"
