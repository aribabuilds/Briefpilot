"""JobService-level tests for M22's delete_job/purge_expired wrappers.
purge_expired has no HTTP endpoint (it's only ever called by main.py's
background sweep task), so it needs a direct test against the service --
unlike delete_job, which test_jobs.py already covers through the API.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.repositories.document_store import InMemoryDocumentStore
from app.repositories.job_repository import InMemoryJobRepository
from app.schemas.ocr import BBox, OcrDocument, OcrPage, OcrWord
from app.services.job_service import JobService


class _SyncExecutor:
    def submit(self, fn: Callable[..., object], /, *args: object) -> object:
        fn(*args)
        return None


def _document() -> OcrDocument:
    words = [
        OcrWord(text="x", page=0, bbox=BBox(x=0.1, y=0.1, width=0.1, height=0.1), confidence=0.9)
    ]
    return OcrDocument(pages=[OcrPage(page=0, width=100, height=100, words=words)])


def _service() -> JobService:
    return JobService(
        InMemoryJobRepository(),
        lambda content, ct: _document(),
        _SyncExecutor(),
        min_mean_confidence=0.5,
        min_word_count=1,
        document_store=InMemoryDocumentStore(),
    )


def test_delete_job_reports_false_for_an_unknown_job() -> None:
    service = _service()
    assert service.delete_job("nope") is False


def test_delete_job_reports_true_and_clears_state_for_a_known_job() -> None:
    service = _service()
    job = service.create_job(filename="letter.pdf", content=b"bytes", content_type="image/png")

    assert service.delete_job(job.id) is True
    assert service.get_job(job.id) is None
    assert service.get_document(job.id) is None


def test_purge_expired_removes_only_jobs_past_the_retention_window() -> None:
    service = _service()
    job = service.create_job(filename="letter.pdf", content=b"bytes", content_type="image/png")

    # The job was just created, so "now" 25h later puts it past a 24h max_age.
    future = job.created_at + timedelta(hours=25)
    purged = service.purge_expired(now=future, max_age=timedelta(hours=24))

    assert purged == [job.id]
    assert service.get_job(job.id) is None
    assert service.get_document(job.id) is None


def test_purge_expired_leaves_fresh_jobs_alone() -> None:
    service = _service()
    job = service.create_job(filename="letter.pdf", content=b"bytes", content_type="image/png")

    purged = service.purge_expired(now=datetime.now(UTC), max_age=timedelta(hours=24))

    assert purged == []
    assert service.get_job(job.id) is not None
