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
