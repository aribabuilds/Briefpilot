// Mirrors the backend Pydantic contract in backend/app/schemas/job.py.
// Kept in sync by hand for now; a generated client is a post-MVP nicety.

export type JobStatus = "processing" | "done";

export interface JobResult {
  message: string;
  filename: string;
}

export interface Job {
  id: string;
  status: JobStatus;
  filename: string;
  created_at: string;
  result: JobResult | null;
}

export interface JobCreatedResponse {
  id: string;
  status: JobStatus;
}
