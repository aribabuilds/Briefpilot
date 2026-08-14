"""Persistence boundary for the raw uploaded document bytes (M18).

Separate from JobRepository (job.py's JSON-serializable Job/JobResult
records) deliberately: raw file bytes are a different concern with a
different lifecycle (needed to re-render the original scan; never sent as
part of the Job JSON response, which would bloat every poll response with a
base64 blob). Same dependency-inversion seam as JobRepository -- an
in-memory implementation now, swappable for real storage (e.g. a local
volume, per CLAUDE.md §3) behind this interface with no caller changes,
once M22's retention/deletion story needs it.
"""

import threading
from abc import ABC, abstractmethod


class DocumentStore(ABC):
    @abstractmethod
    def put(self, job_id: str, *, content: bytes, content_type: str) -> None: ...

    @abstractmethod
    def get(self, job_id: str) -> tuple[bytes, str] | None: ...


class InMemoryDocumentStore(DocumentStore):
    def __init__(self) -> None:
        self._documents: dict[str, tuple[bytes, str]] = {}
        self._lock = threading.Lock()

    def put(self, job_id: str, *, content: bytes, content_type: str) -> None:
        with self._lock:
            self._documents[job_id] = (content, content_type)

    def get(self, job_id: str) -> tuple[bytes, str] | None:
        with self._lock:
            return self._documents.get(job_id)
