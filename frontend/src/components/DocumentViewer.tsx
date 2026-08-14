"use client";

import { useEffect, useRef, useState } from "react";

import { bboxToStyle } from "@/lib/bbox";
import { getDocumentPageUrl } from "@/services/api";
import type { LetterExtraction, SourceSpan } from "@/types/job";

export interface SourceSpanBearer {
  source_span: SourceSpan | null;
}

interface DocumentViewerProps {
  jobId: string;
  pageCount: number;
  extraction?: LetterExtraction | null;
  // M19: the field currently selected in ExtractionSummary. null/undefined
  // means nothing is selected -- no scroll, no highlight, no prompt.
  selectedField?: SourceSpanBearer | null;
}

// M18: "see the original scan of my letter." Renders one <img> per page,
// backed by the real, un-preprocessed rasterization the backend serves (see
// api.py::get_document_page's docstring) -- not the OCR-preprocessed image,
// so what's shown is recognizably the file the user actually uploaded.
//
// Every field with a resolved source_span (M10) gets a faint, permanent
// box (bbox.ts's pure percentage conversion -- correct at any render size,
// zero pixel measurement) proving the coordinate math is right. M19 adds
// the actual interaction on top: the currently *selected* field (tapped in
// ExtractionSummary) gets a brighter, animated highlight, and the viewer
// auto-scrolls to whichever page it's on. A selected field with no
// source_span at all shows a verify prompt instead of a highlight --
// there's nothing to point at, and pretending otherwise would be exactly
// the kind of false confidence CLAUDE.md's null-not-guess principle exists
// to prevent.
export function DocumentViewer({
  jobId,
  pageCount,
  extraction,
  selectedField = null,
}: DocumentViewerProps) {
  const [failedPages, setFailedPages] = useState<ReadonlySet<number>>(new Set());
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const selectedSpan = selectedField?.source_span ?? null;
  const showUnverifiedPrompt = selectedField !== null && selectedSpan === null;

  useEffect(() => {
    if (!selectedSpan) return;
    pageRefs.current
      .get(selectedSpan.page)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [selectedSpan]);

  if (pageCount === 0) return null;

  const fields: SourceSpanBearer[] = extraction
    ? (Object.values(extraction) as SourceSpanBearer[])
    : [];

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">Original scan</h2>
      {showUnverifiedPrompt && (
        <p
          role="status"
          className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300"
        >
          This value could not be matched back to a specific spot in the scan — please verify it
          manually against the original.
        </p>
      )}
      <div className="flex flex-col gap-3">
        {Array.from({ length: pageCount }, (_, page) => {
          if (failedPages.has(page)) return null;
          const pageBoxes = fields.flatMap((field) =>
            field.source_span && field.source_span.page === page ? field.source_span.bboxes : [],
          );
          const isSelectedPage = selectedSpan?.page === page;
          return (
            <div
              key={page}
              ref={(el) => {
                if (el) pageRefs.current.set(page, el);
                else pageRefs.current.delete(page);
              }}
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
              {isSelectedPage &&
                selectedSpan.bboxes.map((bbox, index) => (
                  <div
                    key={`selected-${index}`}
                    className="pointer-events-none absolute animate-pulse rounded border-4 border-blue-500 bg-blue-400/25 shadow-lg"
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
