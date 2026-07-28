from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class JobStatus(StrEnum):
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class JobResult(BaseModel):
    # The real OCR outcome (M5). Full word-level geometry lives in the server-side
    # OcrDocument and surfaces to the client when the overlay needs it (M18); for
    # now the result carries the extracted text and a summary the user can see.
    filename: str
    page_count: int
    word_count: int
    mean_confidence: float
    text: str


class Job(BaseModel):
    id: str
    status: JobStatus
    filename: str
    created_at: datetime
    result: JobResult | None = None
    error: str | None = None  # set when status is FAILED


class JobCreatedResponse(BaseModel):
    id: str
    status: JobStatus
