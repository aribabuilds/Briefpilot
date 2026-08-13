"""End-to-end: real Tesseract OCR feeds run_eval's scoring wiring against a
real rendered document -- not a live LLM call (same discipline as
backend/app/tests/test_extraction_e2e.py: classification/extraction are
injected fakes, deterministic and free, so this test proves the harness's
plumbing, not model accuracy). Needs the Tesseract binary; skipped where
absent but required (never silently skipped) in CI.
"""

import io
import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytesseract
import pytest
from app.config.settings import get_settings
from app.schemas.classification import ClassificationResult, DocumentType
from app.schemas.extraction import ExtractedField, LetterExtraction
from app.services.ocr import TesseractOcrService
from PIL import Image, ImageDraw, ImageFont

import run_eval
from scoring import FieldOutcome


def _tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # pragma: no cover - environment-dependent
        return False


_IN_CI = os.getenv("CI") == "true"

pytestmark = pytest.mark.skipif(
    not _tesseract_available() and not _IN_CI,
    reason="Tesseract binary not installed (runs, and is required, in CI)",
)


def _letter_pdf() -> bytes:
    image = Image.new("RGB", (1200, 420), "white")
    font = ImageFont.load_default(size=56)
    draw = ImageDraw.Draw(image)
    lines = [
        "Finanzamt Muenchen",
        "Steuerbescheid vom 01.03.2026",
        "Betrag 250,00 EUR faellig 31.03.2026",
    ]
    for i, line in enumerate(lines):
        draw.text((40, 20 + i * 120), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PDF")
    return buffer.getvalue()


def _fake_classifier(text: str) -> ClassificationResult:
    return ClassificationResult(doc_type=DocumentType.FINANZAMT, confidence=0.9)


def _fake_extractor(text: str) -> LetterExtraction:
    # Deliberately matches _letter_pdf()'s rendered text -- same pattern as
    # test_extraction_e2e.py -- and deliberately gets `deadline` WRONG
    # relative to the label below, so this test also proves score_document
    # is really being called on real (fake-extractor, real-OCR) output, not
    # a hand-wired always-correct stub.
    return LetterExtraction(
        sender=ExtractedField(value="Finanzamt Muenchen", confidence=0.9),
        letter_date=ExtractedField(value=date(2026, 3, 1), confidence=0.9),
        deadline=ExtractedField(value=date(2026, 4, 1), confidence=0.9),  # wrong on purpose
        amount=ExtractedField(value=Decimal("250.00"), confidence=0.9),
        legal_references=ExtractedField(value=[], confidence=0.5),
        required_actions=ExtractedField(value=[], confidence=0.5),
    )


def _write_golden_document(golden_root: Path) -> None:
    doc_dir = golden_root / "documents" / "test-finanzamt-001"
    doc_dir.mkdir(parents=True)
    (doc_dir / "source.pdf").write_bytes(_letter_pdf())
    label = {
        "sender": "Finanzamt Muenchen",
        "doc_type": "finanzamt",
        "letter_date": "2026-03-01",
        "deadline": "2026-03-31",  # deliberately differs from the fake extractor's value
        "amount": 250.00,
        "legal_references": [],
        "required_actions": [],
    }
    (doc_dir / "label.json").write_text(json.dumps(label), encoding="utf-8")

    manifest = {"documents": [{"id": "test-finanzamt-001", "doc_type": "finanzamt", "notes": ""}]}
    (golden_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_score_one_document_runs_real_ocr_and_scores_against_the_label(tmp_path: Path) -> None:
    golden_root = tmp_path / "golden"
    _write_golden_document(golden_root)

    settings = get_settings()
    ocr = TesseractOcrService(language=settings.ocr_language, timeout=settings.ocr_timeout_seconds)

    result = run_eval.score_one_document(
        "test-finanzamt-001",
        ocr,
        settings,
        golden_root=golden_root,
        classifier=_fake_classifier,
        extractor=_fake_extractor,
    )

    assert result["sender"] == FieldOutcome.CORRECT
    assert result["doc_type"] == FieldOutcome.CORRECT
    assert result["letter_date"] == FieldOutcome.CORRECT
    assert result["amount"] == FieldOutcome.CORRECT
    assert result["legal_references"] == FieldOutcome.CORRECT_NULL
    # The one field this fixture deliberately gets wrong -- proves real
    # scoring logic ran on real (OCR + fake-AI) output, not a stub that
    # always reports success.
    assert result["deadline"] == FieldOutcome.WRONG


def test_score_one_document_degrades_gracefully_with_no_classifier_or_extractor(
    tmp_path: Path,
) -> None:
    golden_root = tmp_path / "golden"
    _write_golden_document(golden_root)

    settings = get_settings()
    ocr = TesseractOcrService(language=settings.ocr_language, timeout=settings.ocr_timeout_seconds)

    result = run_eval.score_one_document(
        "test-finanzamt-001",
        ocr,
        settings,
        golden_root=golden_root,
        classifier=None,
        extractor=None,
    )

    # Every labeled field is non-null/non-empty in this fixture, so with no
    # AI call at all, every one of them is a genuine MISSED -- OCR ran for
    # real, but nothing was extracted from it.
    assert result["sender"] == FieldOutcome.MISSED
    assert result["doc_type"] == FieldOutcome.MISSED
    assert result["amount"] == FieldOutcome.MISSED
    assert result["legal_references"] == FieldOutcome.CORRECT_NULL
