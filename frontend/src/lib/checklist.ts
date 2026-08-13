import type { LetterExtraction } from "@/types/job";

// M16: "a deadline-sorted action checklist... urgent (<14 days) flagged."
// The extraction schema (ADR-0004, frozen) has exactly one `deadline` per
// letter, not one per action -- every required_actions item shares it. That
// makes "sorted by deadline" a no-op today (one group), a known, documented
// simplification tied to the schema, not an oversight: a genuine multi-
// deadline letter would need a schema change (see ADR-0004's own "revisit
// when" list), not a UI fix.
const URGENT_WINDOW_DAYS = 14;

export interface ActionItem {
  action: string;
  deadline: string | null; // ISO date string, e.g. "2026-03-31"
  // True when the deadline is within URGENT_WINDOW_DAYS of *now* (including
  // already overdue) -- computed at render time, not stored, since urgency
  // is relative to today, not to whenever the letter was processed.
  urgent: boolean;
}

function daysUntil(deadlineIso: string): number {
  const deadline = new Date(deadlineIso);
  const now = new Date();
  const msPerDay = 24 * 60 * 60 * 1000;
  // A day-granularity approximation, not exact-to-the-hour -- appropriate
  // for "how soon should I worry about this," not a precise countdown.
  return (deadline.getTime() - now.getTime()) / msPerDay;
}

export function buildChecklist(extraction: LetterExtraction): ActionItem[] {
  const actions = extraction.required_actions.value ?? [];
  const deadline = extraction.deadline.value;
  const urgent = deadline !== null && daysUntil(deadline) <= URGENT_WINDOW_DAYS;

  return actions.map((action) => ({ action, deadline, urgent }));
}
