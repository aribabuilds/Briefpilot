"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ActionChecklist } from "@/components/ActionChecklist";
import { Disclaimer } from "@/components/Disclaimer";
import { DocumentViewer } from "@/components/DocumentViewer";
import { ExplanationCard } from "@/components/ExplanationCard";
import { ExtractionSummary } from "@/components/ExtractionSummary";
import { RetakePrompt } from "@/components/RetakePrompt";
import { SummaryCard } from "@/components/SummaryCard";
import { buildChecklist } from "@/lib/checklist";
import { formatDocumentType } from "@/lib/documentType";
import { getJob } from "@/services/api";
import type { Job, LetterExtraction } from "@/types/job";

const POLL_INTERVAL_MS = 1200;

type ViewState =
  | { kind: "loading" }
  | { kind: "processing"; job: Job }
  | { kind: "done"; job: Job }
  | { kind: "low_quality"; job: Job }
  | { kind: "failed"; job: Job }
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
          return; // terminal
        }
        if (job.status === "low_quality") {
          setState({ kind: "low_quality", job });
          return; // terminal — OCR ran, but the output isn't reliable enough to show
        }
        if (job.status === "failed") {
          setState({ kind: "failed", job });
          return; // terminal
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
      <div className="w-full max-w-2xl">{renderState(state)}</div>
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
            Reading your letter…
          </p>
          <p className="text-xs text-neutral-500 dark:text-neutral-500">
            This usually takes a few seconds.
          </p>
        </div>
      );
    case "done":
      return <DoneView job={state.job} />;
    case "low_quality":
      // Deliberately does not render state.job.result.text: the quality gate
      // exists precisely to withhold OCR output that's too unreliable to show.
      return (
        <RetakePrompt
          meanConfidence={state.job.result?.mean_confidence ?? 0}
          wordCount={state.job.result?.word_count ?? 0}
        />
      );
    case "failed":
      return (
        <div role="alert" className="flex flex-col gap-2 text-center">
          <p className="text-sm font-medium text-red-600 dark:text-red-400">
            We couldn&apos;t read this document.
          </p>
          <p className="text-xs text-neutral-500 dark:text-neutral-500">
            {state.job.error ?? "Processing failed. Please try a different file."}
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

// M19: selection state (which field is tapped) lives here, not in
// ExtractionSummary or DocumentViewer -- they're siblings that both need to
// react to the same selection, so it has to live in their nearest common
// parent. Split out of renderState's inline "done" case specifically so
// this component can hold that useState: renderState itself is a plain
// helper function, not a component React tracks across renders, so a hook
// inside it would violate the rules of hooks.
function DoneView({ job }: { job: Job }) {
  const [selectedKey, setSelectedKey] = useState<keyof LetterExtraction | null>(null);
  const { result } = job;
  const selectedField = selectedKey && result?.extraction ? result.extraction[selectedKey] : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
            Your letter
          </h1>
          {result?.doc_type && (
            <span className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
              {formatDocumentType(result.doc_type)}
              {result.doc_type_confidence !== null &&
                ` · ${Math.round(result.doc_type_confidence * 100)}%`}
            </span>
          )}
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-500">
          {result?.filename} · {result?.page_count} page
          {result?.page_count === 1 ? "" : "s"} · {result?.word_count} words · avg confidence{" "}
          {result ? Math.round(result.mean_confidence * 100) : 0}%
        </p>
      </div>
      {result?.extraction && <SummaryCard extraction={result.extraction} />}
      <Disclaimer />
      {result?.explanation && <ExplanationCard explanation={result.explanation} />}
      {result?.extraction && <ActionChecklist items={buildChecklist(result.extraction)} />}
      {result?.extraction && (
        <ExtractionSummary
          extraction={result.extraction}
          selectedKey={selectedKey}
          onSelect={setSelectedKey}
        />
      )}
      {result && (
        <DocumentViewer
          jobId={job.id}
          pageCount={result.page_count}
          extraction={result.extraction}
          selectedField={selectedField}
        />
      )}
      <pre className="max-h-[50vh] overflow-auto whitespace-pre-wrap rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-800 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-200">
        {result?.text || "(no text found)"}
      </pre>
      <p className="text-xs text-neutral-400 dark:text-neutral-600">
        This is the raw OCR text behind the explanation and fields above.
      </p>
    </div>
  );
}
