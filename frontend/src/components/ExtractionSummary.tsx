import { confidenceTier, confidenceTierLabel } from "@/lib/confidence";
import type { ExtractedField, LetterExtraction } from "@/types/job";

interface ExtractionSummaryProps {
  extraction: LetterExtraction;
  // M19: which field is currently highlighted in DocumentViewer, and the
  // callback to change it. Optional so ExtractionSummary still works
  // standalone (e.g. in a future context with no viewer to link to).
  selectedKey?: keyof LetterExtraction | null;
  onSelect?: (key: keyof LetterExtraction) => void;
}

const FIELD_LABELS: Record<keyof LetterExtraction, string> = {
  sender: "Sender",
  letter_date: "Letter date",
  deadline: "Deadline",
  amount: "Amount",
  legal_references: "Legal references",
  required_actions: "Required actions",
};

function hasValue(field: ExtractedField<unknown>): boolean {
  if (field.value === null) return false;
  return !Array.isArray(field.value) || field.value.length > 0;
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

// Mirrors the codes appended by backend/app/services/validators.py.
const VALIDATION_ISSUE_LABELS: Record<string, string> = {
  deadline_before_letter_date: "Deadline falls before the letter's own date",
  negative_amount: "Amount is negative",
  unrecognized_legal_reference: "Legal reference not in the known list",
};

function describeIssues(issues: string[]): string {
  return issues.map((issue) => VALIDATION_ISSUE_LABELS[issue] ?? issue).join("; ");
}

export function ExtractionSummary({ extraction, selectedKey, onSelect }: ExtractionSummaryProps) {
  const entries = (Object.keys(FIELD_LABELS) as (keyof LetterExtraction)[])
    .map((key) => ({ key, field: extraction[key] }))
    .filter(({ field }) => hasValue(field));

  if (entries.length === 0) {
    return (
      <p className="text-xs text-neutral-500 dark:text-neutral-500">
        No structured fields were confidently extracted from this letter yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        Extracted fields
      </h2>
      <dl className="flex flex-col divide-y divide-neutral-100 dark:divide-neutral-800">
        {entries.map(({ key, field }) => {
          // Verified means source-span linking found this value in the
          // actual OCR text (M10). Tapping any field (M19) scrolls
          // DocumentViewer to it and highlights it when verified, or shows a
          // "couldn't verify" prompt when it isn't -- the honesty signal
          // either way: an unverified value was capped in confidence for
          // exactly this reason.
          const verified = field.source_span !== null;
          const flagged = field.validation_issues.length > 0;
          const tier = confidenceTier(field.confidence);
          const isSelected = selectedKey === key;
          return (
            <button
              key={key}
              type="button"
              disabled={!onSelect}
              onClick={() => onSelect?.(key)}
              aria-pressed={isSelected}
              className={`flex items-baseline justify-between gap-4 py-1.5 text-left ${
                onSelect ? "cursor-pointer" : ""
              } ${isSelected ? "-mx-2 rounded-lg bg-blue-50 px-2 dark:bg-blue-950" : ""}`}
            >
              <dt className="text-xs text-neutral-500 dark:text-neutral-500">
                {FIELD_LABELS[key]}
              </dt>
              <dd className="flex items-baseline gap-2 text-right text-sm text-neutral-800 dark:text-neutral-200">
                <span>{formatValue(field.value)}</span>
                <span
                  className={
                    tier === "high"
                      ? "text-xs text-emerald-600 dark:text-emerald-400"
                      : tier === "medium"
                        ? "text-xs text-amber-600 dark:text-amber-400"
                        : "text-xs text-orange-600 dark:text-orange-400"
                  }
                  title={`${confidenceTierLabel(tier)} — ${
                    verified
                      ? "found in the original letter text"
                      : "could not be matched back to the original letter text"
                  }`}
                >
                  {Math.round(field.confidence * 100)}% {verified ? "✓" : "unverified"}
                </span>
                {flagged && (
                  <span
                    className="text-xs text-red-600 dark:text-red-400"
                    title={describeIssues(field.validation_issues)}
                  >
                    ⚠ flagged
                  </span>
                )}
              </dd>
            </button>
          );
        })}
      </dl>
    </div>
  );
}
