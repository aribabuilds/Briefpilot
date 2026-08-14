import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.config.settings import Settings, get_settings
from app.schemas.job import Job, JobCreatedResponse
from app.services.ingestion import IngestionError, rasterize
from app.services.job_service import JobService, get_job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Content types the walking skeleton accepts. OCR (M5) only makes sense for
# scanned images and PDFs; anything else is rejected at the boundary.
ALLOWED_CONTENT_TYPES = frozenset(
    {"application/pdf", "image/jpeg", "image/png"},
)

# Annotated dependencies (FastAPI's current idiom) — keeps the calls out of
# argument defaults, which is both a linter rule (B008) and clearer at the
# call site: the parameter's type and how it's provided are stated together.
UploadedFile = Annotated[UploadFile, File()]
ServiceDep = Annotated[JobService, Depends(get_job_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", response_model=JobCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadedFile,
    service: ServiceDep,
    settings: SettingsDep,
) -> JobCreatedResponse:
    content_type = file.content_type
    if content_type is None or content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Upload a PDF, JPEG, or PNG.",
        )

    # Read once to measure size. Streaming size guards belong to hardening (M24);
    # for the skeleton, bounding the in-memory read is enough to reject abuse.
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes} byte limit.",
        )

    job = service.create_job(
        filename=file.filename or "upload",
        content=contents,
        content_type=content_type,
    )
    return JobCreatedResponse(id=job.id, status=job.status)


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    service: ServiceDep,
) -> Job:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return job


@router.get(
    "/{job_id}/pages/{page_number}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
async def get_document_page(
    job_id: str,
    page_number: int,
    service: ServiceDep,
    settings: SettingsDep,
) -> Response:
    """Renders the RAW (un-deskewed, un-preprocessed) rasterized page — the
    original scan the user actually uploaded (M18's story: "see the original
    scan of my letter"). Deliberately not the OCR-preprocessed image
    (grayscale/deskewed/contrast-enhanced, services/preprocess.py) that OCR's
    bounding boxes are actually relative to -- reconciling that alignment
    question, if it turns out to matter, is M19's job, not this one's.
    """
    stored = service.get_document(job_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job or document not found.",
        )
    content, content_type = stored

    try:
        pages = rasterize(
            content,
            content_type,
            max_pages=settings.max_document_pages,
            render_scale=settings.ocr_render_scale,
        )
    except IngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    if page_number < 0 or page_number >= len(pages):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} does not exist ({len(pages)} page(s)).",
        )

    buffer = io.BytesIO()
    pages[page_number].save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")
