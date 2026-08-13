// CLAUDE.md §5.4: "disclaimer component on every results view." BriefPilot
// explains a letter; it never gives legal advice (RDG risk — practicing law
// without a license is a real offense in Germany). Shown on every results
// view that has actual letter content to explain, not just where an
// explanation happens to exist -- the disclaimer applies to the extracted
// fields and OCR text too, not only the plain-English explanation text.
export function Disclaimer() {
  return (
    <p
      role="note"
      className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300"
    >
      BriefPilot explains what this letter says — it does not give legal advice. For decisions with
      real consequences, confirm with the sender or a qualified advisor.
    </p>
  );
}
