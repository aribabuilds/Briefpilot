"use client";

import { useState } from "react";

import { bboxToStyle } from "@/lib/bbox";
import { getDocumentPageUrl } from "@/services/api";
import type { LetterExtraction, SourceSpan } from "@/types/job";

interface DocumentViewerProps {
  jobId: string;
  pageCount: number;
  extraction?: LetterExtraction | null;
}

interface SourceSpanBearer {
  source_span: SourceSpan | null;
}

// M18: "see the original scan of my letter." Renders one <img> per page,
// backed by the real, un-preprocessed rasterization the backend serves (see
// api.py::get_document_page's docstring) -- not the OCR-preprocessed image,
// so what's shown is recognizably the file the user actually uploaded.
//
// Also demonstrates the M18 deliverable "bbox rendering at any scale": every
// field with a resolved source_span (M10) gets a faint, permanent,
// non-interactive box drawn from real extraction data already on the
// frontend, using bbox.ts's pure percentage conversion -- proof the
// coordinate math is correct at whatever size the browser renders the image,
// with zero pixel measurement. Tap-to-highlight on a *specific* field is
// deliberately not built here; that interaction is M19's job.
export function DocumentViewer({ jobId, pageCount, extraction }: DocumentViewerProps) {
  const [failedPages, setFailedPages] = useState<ReadonlySet<number>>(new Set());

  if (pageCount === 0) return null;

  const fields: SourceSpanBearer[] = extraction
    ? (Object.values(extraction) as SourceSpanBearer[])
    : [];

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">Original scan</h2>
      <div className="flex flex-col gap-3">
        {Array.from({ length: pageCount }, (_, page) => {
          if (failedPages.has(page)) return null;
          const pageBoxes = fields.flatMap((field) =>
            field.source_span && field.source_span.page === page ? field.source_span.bboxes : [],
          );
          return (
            <div
              key={page}
              className="relative overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- a
                  backend-rendered page image, not a Next-optimizable static asset */}
              <img
                src={getDocumentPageUrl(jobId, page)}
                alt={`Page ${page + 1} of your letter`}
                className="block w-full"
                onError={() => setFailedPages((prev) => new Set(prev).add(page))}
              />
              {pageBoxes.map((bbox, index) => (
                <div
                  key={index}
                  className="pointer-events-none absolute border-2 border-emerald-500/70 bg-emerald-400/10"
                  style={bboxToStyle(bbox)}
                />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
