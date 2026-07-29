// Mirrors the backend Pydantic contract in backend/app/schemas/job.py.
// Kept in sync by hand for now; a generated client is a post-MVP nicety.

export type JobStatus = "processing" | "done" | "low_quality" | "failed";

export interface JobResult {
  filename: string;
  page_count: number;
  word_count: number;
  mean_confidence: number;
  text: string;
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
