import threading
from abc import ABC, abstractmethod

from app.schemas.job import Job


class JobRepository(ABC):
    """Persistence boundary for jobs.

    The rest of the app depends on this interface, never on a concrete store —
    the same dependency-inversion seam as the AI layer. The in-memory
    implementation below is the M2 stub; a Postgres-backed one drops in behind
    this interface once there is a schema worth persisting (no earlier than the
    real extraction contract at M9), with no change to the service or routers.
    """

    @abstractmethod
    def add(self, job: Job) -> None: ...

    @abstractmethod
    def get(self, job_id: str) -> Job | None: ...

    @abstractmethod
    def update(self, job: Job) -> None: ...

    @abstractmethod
    def delete(self, job_id: str) -> bool:
        """Returns whether a job existed to delete (M22: the DELETE endpoint
        needs this to answer 204 vs. 404 without a separate get() round-trip)."""
        ...

    @abstractmethod
    def list_all(self) -> list[Job]:
        """Only consumer today is the M22 retention sweep, which has to look at
        every job's created_at. A real datastore would push this down to a
        WHERE created_at < ... query instead of materializing everything."""
        ...


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        # A background worker writes the completed job while request threads read
        # it, so guard the dict. (A real datastore makes this the DB's problem.)
        self._lock = threading.Lock()

    def add(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def delete(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs.pop(job_id, None) is not None

    def list_all(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())
