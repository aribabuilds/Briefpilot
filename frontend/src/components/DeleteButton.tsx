"use client";

import { useState } from "react";

import { ApiError, deleteJob, getJob } from "@/services/api";

// M22: "one-click delete... and know it's really gone." Two-stage rather
// than a single unconfirmed click -- a data-deleting action still deserves
// a guard against a stray tap, but confirming is itself one click, not a
// modal or a typed confirmation. After the DELETE call succeeds, this
// re-fetches the job and requires a 404 before claiming success: the
// privacy promise (CLAUDE.md §5.6) is that deletion actually happened, not
// that the request didn't error.
type Stage = "idle" | "confirming" | "deleting" | "deleted" | "error";

export function DeleteButton({ jobId }: { jobId: string }) {
  const [stage, setStage] = useState<Stage>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleConfirm() {
    setStage("deleting");
    try {
      await deleteJob(jobId);
    } catch {
      setStage("error");
      setErrorMessage("Could not delete. Please try again.");
      return;
    }

    try {
      await getJob(jobId);
      // Still reachable after a "successful" delete -- don't claim it's gone.
      setStage("error");
      setErrorMessage("Delete did not take effect. Please try again.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setStage("deleted");
        return;
      }
      setStage("error");
      setErrorMessage("Could not confirm deletion. Please try again.");
    }
  }

  if (stage === "deleted") {
    return (
      <p
        role="status"
        className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-center text-xs text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300"
      >
        Deleted. This document and everything extracted from it are gone from our servers.
      </p>
    );
  }

  if (stage === "confirming") {
    return (
      <div className="flex flex-wrap items-center justify-center gap-2 text-xs">
        <span className="text-neutral-500 dark:text-neutral-400">Delete this document?</span>
        <button
          type="button"
          onClick={handleConfirm}
          className="font-medium text-red-600 underline-offset-4 hover:underline dark:text-red-400"
        >
          Yes, delete it
        </button>
        <button
          type="button"
          onClick={() => setStage("idle")}
          className="text-neutral-500 underline-offset-4 hover:underline dark:text-neutral-400"
        >
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        type="button"
        onClick={() => setStage("confirming")}
        disabled={stage === "deleting"}
        className="text-xs text-neutral-500 underline-offset-4 hover:underline disabled:opacity-50 dark:text-neutral-400"
      >
        {stage === "deleting" ? "Deleting…" : "Delete my document"}
      </button>
      {stage === "error" && errorMessage && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
          {errorMessage}
        </p>
      )}
    </div>
  );
}
