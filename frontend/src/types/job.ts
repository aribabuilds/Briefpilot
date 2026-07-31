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
