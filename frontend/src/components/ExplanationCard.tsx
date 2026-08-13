import { GlossaryText } from "@/components/GlossaryText";
import type { ExplanationResult } from "@/types/job";

interface ExplanationCardProps {
  explanation: ExplanationResult;
}

export function ExplanationCard({ explanation }: ExplanationCardProps) {
  const hasAdvicePhrases = explanation.advice_phrases_found.length > 0;
  const readabilityFlagged = explanation.exceeds_word_limit || explanation.below_readability_target;

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        In plain English
      </h2>
      <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">
        <GlossaryText text={explanation.text} />
      </p>
      {readabilityFlagged && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          This explanation is longer or more complex than intended ({explanation.word_count} words)
          — the text above is shown as generated, not shortened or simplified further.
        </p>
      )}
      {hasAdvicePhrases && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
          ⚠ This explanation may contain advice-like language. Treat it as a description of the
          letter, not instructions — always confirm with the sender or a qualified advisor.
        </p>
      )}
    </div>
  );
}
