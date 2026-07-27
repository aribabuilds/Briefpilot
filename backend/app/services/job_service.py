from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from uuid import uuid4

from app.config.settings import get_settings
from app.repositories.job_repository import InMemoryJobRepository, JobRepository
from app.schemas.job import Job, JobResult, JobStatus


def _utc_now() -> datetime:
    return datetime.now(UTC)


class JobService:
    """Owns the job lifecycle: create on upload, complete when the work is done.

    For the walking skeleton there is no work, so "done" is driven by elapsed
    time rather than a real pipeline. Completion is evaluated lazily on read —
    no threads, no background tasks, no wall-clock coupling in tests (the clock
    is injectable). When the real pipeline lands, the elapsed-time check is
    replaced by "is the pipeline finished"; the poll-until-done contract the
    frontend depends on does not change.
    """

    def __init__(
        self,
        repository: JobRepository,
        processing_delay_seconds: float,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._repository = repository
        self._delay = timedelta(seconds=processing_delay_seconds)
        self._clock = clock

    def create_job(self, filename: str) -> Job:
        job = Job(
            id=uuid4().hex,
            status=JobStatus.PROCESSING,
            filename=filename,
            created_at=self._clock(),
            result=None,
        )
        self._repository.add(job)
        return job

    def get_job(self, job_id: str) -> Job | None:
        job = self._repository.get(job_id)
        if job is None:
            return None
        if job.status is JobStatus.PROCESSING and self._clock() - job.created_at >= self._delay:
            job = job.model_copy(
                update={"status": JobStatus.DONE, "result": self._build_stub_result(job)}
            )
            self._repository.update(job)
        return job

    def _build_stub_result(self, job: Job) -> JobResult:
        return JobResult(
            message=(
                "Your document was received and a placeholder result was produced. "
                "Real extraction, explanation, and source highlighting arrive in later milestones."
            ),
            filename=job.filename,
        )


@lru_cache
def get_job_service() -> JobService:
    # Cached so the in-memory repository is a process-wide singleton; a fresh
    # service per request would drop every job the instant it was created.
    settings = get_settings()
    return JobService(
        repository=InMemoryJobRepository(),
        processing_delay_seconds=settings.stub_processing_delay_seconds,
    )
