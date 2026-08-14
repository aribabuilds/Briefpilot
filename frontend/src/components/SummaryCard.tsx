import { confidenceTier, type ConfidenceTier } from "@/lib/confidence";
import type { LetterExtraction } from "@/types/job";

interface SummaryCardProps {
  extraction: LetterExtraction;
}

const TIER_COLOR: Record<ConfidenceTier, string> = {
  high: "text-emerald-600 dark:text-emerald-400",
  medium: "text-amber-600 dark:text-amber-400",
  low: "text-orange-600 dark:text-orange-400",
};

// M17: "one clear results page" — the at-a-glance summary a user should see
// before reading anything else. Reuses M14's confidence tiers rather than
// inventing a second color scale, so the same value looks the same color
// whether it's read here or in ExtractionSummary below.
interface SummaryRow {
  label: string;
  value: string | null;
  confidence: number;
}

export function SummaryCard({ extraction }: SummaryCardProps) {
  const allRows: SummaryRow[] = [
    { label: "From", value: extraction.sender.value, confidence: extraction.sender.confidence },
    {
      label: "Deadline",
      value: extraction.deadline.value,
      confidence: extraction.deadline.confidence,
    },
    {
      label: "Amount",
      value: extraction.amount.value !== null ? `${extraction.amount.value} EUR` : null,
      confidence: extraction.amount.confidence,
    },
  ];
  const rows = allRows.filter((row) => row.value !== null);

  if (rows.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-3 rounded-xl border border-neutral-200 bg-white p-4 sm:grid-cols-3 dark:border-neutral-800 dark:bg-neutral-900">
      {rows.map((row) => (
        <div key={row.label} className="flex flex-col gap-0.5">
          <span className="text-xs uppercase tracking-wide text-neutral-400 dark:text-neutral-600">
            {row.label}
          </span>
          <span className={`text-sm font-medium ${TIER_COLOR[confidenceTier(row.confidence)]}`}>
            {row.value}
          </span>
        </div>
      ))}
    </div>
  );
}
