// Mirrors the backend Pydantic contract in backend/app/schemas/job.py.
// Kept in sync by hand for now; a generated client is a post-MVP nicety.

export type JobStatus = "processing" | "done" | "low_quality" | "failed";

// Mirrors DocumentType in backend/app/schemas/classification.py.
export type DocumentType =
  | "finanzamt"
  | "auslaenderbehoerde"
  | "krankenkasse"
  | "bussgeld"
  | "rundfunkbeitrag"
  | "jobcenter"
  | "rental_utility"
  | "other";

// Mirrors backend/app/schemas/ocr.py::BBox (frozen, ADR-0002) — page fractions.
export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

// Mirrors backend/app/schemas/extraction.py::SourceSpan.
export interface SourceSpan {
  page: number;
  bboxes: BBox[];
}

// Mirrors backend/app/schemas/extraction.py::ExtractedField[T] (frozen, ADR-0004).
// `T` is `string | null` here for every field, NOT a parsed number/Date:
// Pydantic serializes `date` as an ISO string and `Decimal` (amount) as a
// string to preserve precision (verified in test_extraction_schemas.py) — do
// not `parseFloat`/`new Date()` these without knowing that's what you want.
// M11/ADR-0005: machine-readable codes from backend/app/services/validators.py,
// e.g. "deadline_before_letter_date" -- empty means no deterministic check
// failed. Additive to the frozen ADR-0004 contract, never removed.
export interface ExtractedField<T> {
  value: T | null;
  confidence: number;
  source_span: SourceSpan | null;
  validation_issues: string[];
}

// Mirrors backend/app/schemas/extraction.py::LetterExtraction (frozen, ADR-0004).
export interface LetterExtraction {
  sender: ExtractedField<string>;
  letter_date: ExtractedField<string>; // ISO date string, e.g. "2026-03-01"
  deadline: ExtractedField<string>;
  amount: ExtractedField<string>; // decimal string, e.g. "250.00"
  legal_references: ExtractedField<string[]>;
  required_actions: ExtractedField<string[]>;
}

// Mirrors backend/app/schemas/explanation.py::ExplanationResult (M15).
export interface ExplanationResult {
  text: string;
  word_count: number;
  flesch_reading_ease: number;
  exceeds_word_limit: boolean;
  below_readability_target: boolean;
  // Machine-readable codes from backend/app/services/advice_linter.py, e.g.
  // "you_should" -- empty means the linter found nothing. CLAUDE.md §5.4:
  // BriefPilot explains, it never gives legal advice.
  advice_phrases_found: string[];
}

export interface JobResult {
  filename: string;
  page_count: number;
  word_count: number;
  mean_confidence: number;
  text: string;
  // Null whenever classification hasn't run or failed (no API key yet, a
  // network error) — never a guessed type. See JobService's null-not-guess
  // handling in backend/app/services/job_service.py.
  doc_type: DocumentType | null;
  doc_type_confidence: number | null;
  // Independent of classification — either can succeed or fail on its own.
  extraction: LetterExtraction | null;
  // Independent of both — grounded on document text + whatever extraction
  // produced, but does not require extraction to have succeeded.
  explanation: ExplanationResult | null;
}

export interface Job {
  id: string;
  status: JobStatus;
  filename: string;
  created_at: string;
  result: JobResult | null;
  error: string | null;
}

export interface JobCreatedResponse {
  id: string;
  status: JobStatus;
}
