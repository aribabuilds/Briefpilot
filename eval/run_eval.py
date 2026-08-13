"""CLI: runs the real pipeline (OCR -> classification -> extraction ->
source-span linking -> validation) against every document registered in
eval/golden/manifest.json, scores each one against its hand-labeled ground
truth (scoring.py), and writes eval/scorecard.md.

With 0 golden letters (the state today -- see eval/golden/README.md), this
still runs end to end and writes an honest "0 documents" scorecard rather
than skipping silently: the harness itself is worth proving works, even
before there is real data to run it on.

Needs the real Tesseract binary and, for non-null classification/extraction,
a configured GEMINI_API_KEY -- without one, this still runs (classification
and extraction degrade to null per JobService's own best-effort discipline),
and the scorecard will honestly show those fields as MISSED, never silently
fabricated or skipped.

Classification/extraction are injected as callables (ClassifierRunner /
ExtractorRunner, reused from app.services.job_service) rather than called
inline via get_ai_service() -- the same dependency-inversion seam JobService
itself uses, and for the same reason: it lets eval/tests exercise the real
OCR + scoring wiring against a real rendered document without a live LLM
call, exactly as test_extraction_e2e.py already does for JobService.

Usage (from the repo root, using the backend's own venv):
    backend/.venv/Scripts/python.exe eval/run_eval.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

EVAL_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = EVAL_ROOT.parent / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config.settings import Settings, get_settings  # noqa: E402
from app.schemas.ai import DocumentExtractionRequest  # noqa: E402
from app.schemas.classification import ClassificationRequest, ClassificationResult  # noqa: E402
from app.schemas.extraction import LetterExtraction  # noqa: E402
from app.services.ai import get_ai_service  # noqa: E402
from app.services.document_pipeline import build_document  # noqa: E402
from app.services.job_service import ClassifierRunner, ExtractorRunner  # noqa: E402
from app.services.ocr import OcrService, TesseractOcrService  # noqa: E402
from app.services.source_span_linking import link_source_spans  # noqa: E402
from app.services.validators import validate_extraction  # noqa: E402

from scoring import (  # noqa: E402
    FieldOutcome,
    aggregate,
    generate_scorecard_markdown,
    score_document,
)

_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

GOLDEN_ROOT = EVAL_ROOT / "golden"
SCORECARD_PATH = EVAL_ROOT / "scorecard.md"


def _load_manifest(golden_root: Path = GOLDEN_ROOT) -> list[dict[str, Any]]:
    manifest_path = golden_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = manifest["documents"]
    if not isinstance(documents, list):  # pragma: no cover - malformed manifest is a hard error
        raise ValueError(f"{manifest_path} must have a top-level 'documents' list")
    return documents


def _find_source(document_id: str, golden_root: Path = GOLDEN_ROOT) -> Path:
    doc_dir = golden_root / "documents" / document_id
    for ext in _CONTENT_TYPES:
        candidate = doc_dir / f"source{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No source.* file for golden document {document_id!r} in {doc_dir}")


def _extraction_to_comparable(extraction: LetterExtraction) -> dict[str, Any]:
    return {
        "sender": extraction.sender.value,
        "letter_date": (
            extraction.letter_date.value.isoformat() if extraction.letter_date.value else None
        ),
        "deadline": extraction.deadline.value.isoformat() if extraction.deadline.value else None,
        "amount": float(extraction.amount.value) if extraction.amount.value is not None else None,
        "legal_references": extraction.legal_references.value,
        "required_actions": extraction.required_actions.value,
    }


def _classify(text: str) -> ClassificationResult:
    # Lazy get_ai_service() call, same as JobService's own _classify -- a
    # missing/misconfigured provider surfaces as an exception at call time,
    # not at import time.
    ai_service = get_ai_service()
    return asyncio.run(ai_service.classify_document(ClassificationRequest(content=text)))


def _extract(text: str) -> LetterExtraction:
    ai_service = get_ai_service()
    return asyncio.run(ai_service.extract_document(DocumentExtractionRequest(content=text)))


def score_one_document(
    document_id: str,
    ocr: OcrService,
    settings: Settings,
    *,
    golden_root: Path = GOLDEN_ROOT,
    classifier: ClassifierRunner | None,
    extractor: ExtractorRunner | None,
) -> dict[str, FieldOutcome]:
    label_path = golden_root / "documents" / document_id / "label.json"
    label = json.loads(label_path.read_text(encoding="utf-8"))

    source_path = _find_source(document_id, golden_root)
    content_type = _CONTENT_TYPES[source_path.suffix.lower()]
    ocr_document = build_document(
        source_path.read_bytes(),
        content_type,
        ocr=ocr,
        max_pages=settings.max_document_pages,
        render_scale=settings.ocr_render_scale,
        preprocess_enabled=settings.preprocess_enabled,
        deskew_max_angle=settings.deskew_max_angle,
        max_dimension=settings.preprocess_max_dimension,
    )

    # Best-effort, mirroring JobService: a missing API key or a provider
    # outage degrades this one document's AI-derived fields to null (scored
    # as MISSED against a non-null label), not a crash of the whole eval run.
    extracted: dict[str, Any] = {"doc_type": None}
    if classifier is not None:
        try:
            classification = classifier(ocr_document.text)
            extracted["doc_type"] = classification.doc_type
        except Exception:  # noqa: BLE001 - best-effort, matches JobService
            pass

    if extractor is not None:
        try:
            extraction = extractor(ocr_document.text)
            extraction = validate_extraction(link_source_spans(extraction, ocr_document))
            extracted.update(_extraction_to_comparable(extraction))
        except Exception:  # noqa: BLE001 - best-effort, matches JobService
            pass

    return score_document(label, extracted)


def main() -> int:
    documents = _load_manifest()

    if not documents:
        scorecard = generate_scorecard_markdown({}, document_count=0)
        SCORECARD_PATH.write_text(scorecard, encoding="utf-8")
        print(scorecard)
        return 0

    settings = get_settings()
    ocr = TesseractOcrService(language=settings.ocr_language, timeout=settings.ocr_timeout_seconds)

    document_scores = []
    for doc in documents:
        print(f"Scoring {doc['id']}...", file=sys.stderr)
        document_scores.append(
            score_one_document(doc["id"], ocr, settings, classifier=_classify, extractor=_extract)
        )

    tallies = aggregate(document_scores)
    scorecard = generate_scorecard_markdown(tallies, document_count=len(documents))
    SCORECARD_PATH.write_text(scorecard, encoding="utf-8")
    print(scorecard)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
