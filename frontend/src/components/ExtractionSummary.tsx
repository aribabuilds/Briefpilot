import type { ExtractedField, LetterExtraction } from "@/types/job";

interface ExtractionSummaryProps {
  extraction: LetterExtraction;
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

export function ExtractionSummary({ extraction }: ExtractionSummaryProps) {
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
          // actual OCR text (M10) — not yet clickable/highlightable, that's
          // the M18/M19 overlay. This is the honesty signal in the meantime:
          // an unverified value was capped in confidence for exactly this reason.
          const verified = field.source_span !== null;
          return (
            <div key={key} className="flex items-baseline justify-between gap-4 py-1.5">
              <dt className="text-xs text-neutral-500 dark:text-neutral-500">
                {FIELD_LABELS[key]}
              </dt>
              <dd className="flex items-baseline gap-2 text-right text-sm text-neutral-800 dark:text-neutral-200">
                <span>{formatValue(field.value)}</span>
                <span
                  className={
                    verified
                      ? "text-xs text-emerald-600 dark:text-emerald-400"
                      : "text-xs text-amber-600 dark:text-amber-400"
                  }
                  title={
                    verified
                      ? "Found in the original letter text"
                      : "Could not be matched back to the original letter text"
                  }
                >
                  {Math.round(field.confidence * 100)}% {verified ? "✓" : "unverified"}
                </span>
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
