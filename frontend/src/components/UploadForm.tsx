"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, uploadDocument } from "@/services/api";

const ACCEPT = "application/pdf,image/jpeg,image/png";

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;

    setSubmitting(true);
    setError(null);
    try {
      const { id } = await uploadDocument(file);
      router.push(`/result/${id}`);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?";
      setError(message);
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-md flex-col gap-4">
      <label
        htmlFor="document"
        className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-neutral-300 px-6 py-10 text-center transition hover:border-neutral-400 dark:border-neutral-700 dark:hover:border-neutral-600"
      >
        <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
          {file ? file.name : "Choose a PDF or photo of your letter"}
        </span>
        <span className="text-xs text-neutral-500 dark:text-neutral-500">PDF, JPEG, or PNG</span>
        <input
          id="document"
          name="document"
          type="file"
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setError(null);
          }}
        />
      </label>

      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!file || submitting}
        className="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-300"
      >
        {submitting ? "Uploading…" : "Analyze letter"}
      </button>
    </form>
  );
}
