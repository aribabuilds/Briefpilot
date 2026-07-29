# Golden letters

Real German official letters, collected and labeled by the project owner —
never fabricated. This is what M12's eval harness scores against, and what
M13's accuracy iteration and M25's failure analysis are built on, so the
format is fixed here even though the set starts empty.

Fabricating "realistic" letters would defeat the entire point of the eval
suite: the scorecard is supposed to say something true about real-world OCR
and extraction quality, not about how well the pipeline handles synthetic
fixtures a developer wrote to be easy.

## Collecting a letter

1. **Redact first, save second.** Black out anything you would not want in a
   public GitHub repo — Steuer-ID, IBAN, full name if you'd rather not, case
   numbers. The redaction itself should be visible (a black box), not
   invisible (deleted text), since OCR and the eval harness need to see that
   *something* was there.
2. Save the source scan/photo under `eval/golden/documents/<id>/source.<ext>`
   (`.pdf`, `.jpg`, or `.png` — whatever ingestion already accepts).
3. Write `eval/golden/documents/<id>/label.json` by hand (format below). This
   is the ground truth the eval harness compares extraction against.
4. Add one row to `eval/golden/manifest.json` (see below) so the harness knows
   the fixture exists and what letter type it is.

## `manifest.json`

```json
{
  "documents": [
    { "id": "finanzamt-001", "doc_type": "finanzamt", "notes": "" }
  ]
}
```

`doc_type` is one of the eight in-scope types from `CLAUDE.md` §1: `finanzamt`,
`auslaenderbehoerde`, `krankenkasse`, `bussgeld`, `rundfunkbeitrag`,
`jobcenter`, `rental_utility`, `other`.

## `label.json` (per document)

This mirrors the eventual extraction schema (`{value, confidence, source_span}`
lands for real at M9) but only needs `value` filled in by hand for now — it's
ground truth, not a confidence estimate:

```json
{
  "sender": "Finanzamt Muenchen",
  "doc_type": "finanzamt",
  "letter_date": "2026-03-04",
  "deadline": "2026-03-25",
  "amount": 184.50,
  "legal_references": ["§ 152 AO"],
  "required_actions": ["Pay by deadline", "Submit missing receipts"]
}
```

Leave a field `null` if the real letter genuinely doesn't have one — that's
real data, not a gap to fill in.

## Current count: 0

M6's job is this scaffold; M3–M7 target 10 letters, growing to 20 (M14) and 30
(M21, frozen for M25's final scorecard). Nothing here is fabricated to hit
those numbers — if the count is behind, the honest scorecard says so.
