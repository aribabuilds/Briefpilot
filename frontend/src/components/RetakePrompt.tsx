interface RetakePromptProps {
  meanConfidence: number;
  wordCount: number;
}

const TIPS = [
  "Lay the letter flat and fill the frame — avoid folds or curled corners.",
  "Use bright, even light. Avoid shadows across the text and glare from flash.",
  "Hold the camera directly above the page, not at an angle.",
  "Make sure the camera is focused before taking the photo.",
];

export function RetakePrompt({ meanConfidence, wordCount }: RetakePromptProps) {
  return (
    <div className="flex flex-col gap-4 text-center">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
          We couldn&apos;t read this photo clearly enough
        </p>
        <p className="text-xs text-neutral-500 dark:text-neutral-500">
          {wordCount === 0
            ? "No readable text was found."
            : `Only ${wordCount} word${wordCount === 1 ? "" : "s"} recognized, at ${Math.round(
                meanConfidence * 100,
              )}% average confidence.`}
        </p>
      </div>
      <ul className="flex flex-col gap-2 text-left text-sm text-neutral-700 dark:text-neutral-300">
        {TIPS.map((tip) => (
          <li key={tip} className="flex gap-2">
            <span aria-hidden className="text-neutral-400 dark:text-neutral-600">
              •
            </span>
            <span>{tip}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
