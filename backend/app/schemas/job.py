from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class JobStatus(StrEnum):
    PROCESSING = "processing"
    DONE = "done"


class JobResult(BaseModel):
    # Stub result for the walking skeleton (M2). This is intentionally trivial:
    # its only job is to prove the upload -> poll -> render wire end to end.
    # It is replaced at M9 by the real extraction contract — per-type Pydantic
    # schemas where every field carries {value, confidence, source_span}.
    message: str
    filename: str


class Job(BaseModel):
    id: str
    status: JobStatus
    filename: str
    created_at: datetime
    result: JobResult | None = None


class JobCreatedResponse(BaseModel):
    id: str
    status: JobStatus
