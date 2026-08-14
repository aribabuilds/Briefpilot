"""Pure tests for services/retention.py (M22) -- no FastAPI, no clock, just
an injected `now` against injected job created_at timestamps."""

from datetime import UTC, datetime, timedelta

from app.repositories.document_store import InMemoryDocumentStore
from app.repositories.job_repository import InMemoryJobRepository
from app.schemas.job import Job, JobStatus
from app.services.retention import purge_expired

NOW = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
MAX_AGE = timedelta(hours=24)


def _job(job_id: str, *, age: timedelta) -> Job:
    return Job(id=job_id, status=JobStatus.DONE, filename="letter.pdf", created_at=NOW - age)


def test_jobs_older_than_max_age_are_deleted() -> None:
    repo = InMemoryJobRepository()
    repo.add(_job("old", age=timedelta(hours=25)))

    purged = purge_expired(repo, None, now=NOW, max_age=MAX_AGE)

    assert purged == ["old"]
    assert repo.get("old") is None


def test_jobs_within_max_age_are_kept() -> None:
    repo = InMemoryJobRepository()
    repo.add(_job("fresh", age=timedelta(hours=1)))

    purged = purge_expired(repo, None, now=NOW, max_age=MAX_AGE)

    assert purged == []
    assert repo.get("fresh") is not None


def test_a_job_exactly_at_the_boundary_is_treated_as_expired() -> None:
    repo = InMemoryJobRepository()
    repo.add(_job("boundary", age=timedelta(hours=24)))

    purged = purge_expired(repo, None, now=NOW, max_age=MAX_AGE)

    assert purged == ["boundary"]


def test_only_expired_jobs_are_purged_others_are_left_alone() -> None:
    repo = InMemoryJobRepository()
    repo.add(_job("old", age=timedelta(hours=48)))
    repo.add(_job("fresh", age=timedelta(hours=2)))

    purged = purge_expired(repo, None, now=NOW, max_age=MAX_AGE)

    assert purged == ["old"]
    assert repo.get("old") is None
    assert repo.get("fresh") is not None


def test_document_store_is_purged_alongside_the_job() -> None:
    repo = InMemoryJobRepository()
    store = InMemoryDocumentStore()
    repo.add(_job("old", age=timedelta(hours=25)))
    store.put("old", content=b"raw bytes", content_type="image/png")

    purge_expired(repo, store, now=NOW, max_age=MAX_AGE)

    assert store.get("old") is None


def test_works_without_a_document_store() -> None:
    repo = InMemoryJobRepository()
    repo.add(_job("old", age=timedelta(hours=25)))

    purged = purge_expired(repo, None, now=NOW, max_age=MAX_AGE)

    assert purged == ["old"]


def test_empty_repository_purges_nothing() -> None:
    repo = InMemoryJobRepository()
    assert purge_expired(repo, None, now=NOW, max_age=MAX_AGE) == []
