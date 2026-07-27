"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getJob } from "@/services/api";
import type { Job } from "@/types/job";

const POLL_INTERVAL_MS = 1200;

type ViewState =
  | { kind: "loading" }
  | { kind: "processing"; job: Job }
  | { kind: "done"; job: Job }
  | { kind: "error"; message: string };

export default function ResultPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [state, setState] = useState<ViewState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const job = await getJob(id);
        if (cancelled) return;

        if (job.status === "done") {
          setState({ kind: "done", job });
          return; // stop polling
        }
        setState({ kind: "processing", job });
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        setState({
          kind: "error",
          message: err instanceof Error ? err.message : "Something went wrong.",
        });
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-white px-6 py-16 dark:bg-neutral-950">
      <div className="w-full max-w-md">{renderState(state)}</div>
      <Link
        href="/"
        className="text-sm text-neutral-500 underline-offset-4 hover:underline dark:text-neutral-400"
      >
        ← Upload another letter
      </Link>
    </main>
  );
}

function renderState(state: ViewState) {
  switch (state.kind) {
    case "loading":
    case "processing":
      return (
        <div className="flex flex-col items-center gap-3 text-center" role="status">
          <div
            className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900 dark:border-neutral-700 dark:border-t-neutral-100"
            aria-hidden
          />
          <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Analyzing your letter…
          </p>
          <p className="text-xs text-neutral-500 dark:text-neutral-500">
            This usually takes a few seconds.
          </p>
        </div>
      );
    case "done":
      return (
        <div className="flex flex-col gap-4 rounded-xl border border-neutral-200 p-6 dark:border-neutral-800">
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">Result</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            {state.job.result?.message}
          </p>
          <p className="text-xs text-neutral-500 dark:text-neutral-500">
            File: {state.job.result?.filename}
          </p>
        </div>
      );
    case "error":
      return (
        <div role="alert" className="flex flex-col gap-2 text-center">
          <p className="text-sm font-medium text-red-600 dark:text-red-400">{state.message}</p>
          <p className="text-xs text-neutral-500 dark:text-neutral-500">
            The job may have expired, or the backend may be unavailable.
          </p>
        </div>
      );
  }
}
