from typing import Any

from pydantic import BaseModel


class DocumentExtractionRequest(BaseModel):
    content: str
    instructions: str | None = None


class DocumentExtractionResult(BaseModel):
    extracted_data: dict[str, Any]
    raw_response: str | None = None


class SummarizationRequest(BaseModel):
    content: str
    max_length: int | None = None


class SummarizationResult(BaseModel):
    summary: str
