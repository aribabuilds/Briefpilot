from pydantic import BaseModel


class DocumentExtractionRequest(BaseModel):
    content: str


class SummarizationRequest(BaseModel):
    content: str
    max_length: int | None = None


class SummarizationResult(BaseModel):
    summary: str
