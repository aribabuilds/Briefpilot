import type { HealthStatus } from "@/types/health";
import type { Job, JobCreatedResponse } from "@/types/job";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const JOBS_URL = `${API_BASE}/api/v1/jobs`;
const HEALTH_URL = `${API_BASE}/health`;

/** Thrown for any non-2xx response, carrying the backend's detail when present. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function detail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? fallback;
  } catch {
    return fallback;
  }
}

export async function uploadDocument(file: File): Promise<JobCreatedResponse> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(JOBS_URL, { method: "POST", body });
  if (!response.ok) {
    throw new ApiError(await detail(response, "Upload failed."), response.status);
  }
  return (await response.json()) as JobCreatedResponse;
}

export async function getJob(id: string): Promise<Job> {
  const response = await fetch(`${JOBS_URL}/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new ApiError(await detail(response, "Could not load job."), response.status);
  }
  return (await response.json()) as Job;
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(HEALTH_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new ApiError(await detail(response, "Health check failed."), response.status);
  }
  return (await response.json()) as HealthStatus;
}
