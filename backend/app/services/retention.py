"""24h auto-purge (M22): a pure, unit-tested sweep over JobRepository and
DocumentStore. Deliberately knows nothing about *when* or *how often* it
runs -- that scheduling concern belongs to main.py's background task, not
here. Same split as validators.py (pure check) vs. job_service.py (wiring):
correctness of "what counts as expired" is trivial to test in isolation this
way, without spinning up a real clock or an event loop.
"""

from datetime import datetime, timedelta

from app.repositories.document_store import DocumentStore
from app.repositories.job_repository import JobRepository


def purge_expired(
    repository: JobRepository,
    document_store: DocumentStore | None,
    *,
    now: datetime,
    max_age: timedelta,
) -> list[str]:
    expired_ids = [job.id for job in repository.list_all() if now - job.created_at >= max_age]
    for job_id in expired_ids:
        repository.delete(job_id)
        if document_store is not None:
            document_store.delete(job_id)
    return expired_ids
