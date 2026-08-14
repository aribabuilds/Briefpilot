import { expect, test } from "@playwright/test";

// M20: "the full journey keeps working from one release to the next." A
// FAST smoke test of the frontend's own rendering logic -- every backend
// call (health, upload, poll, page image) is mocked via route interception,
// so this needs no live backend, no Tesseract, no Gemini quota. It proves
// the same thing the backend's own e2e tests (test_pipeline_e2e.py,
// test_extraction_e2e.py, test_full_pipeline_e2e.py) prove for the
// pipeline: that a real user journey, not just individual components in
// isolation, still works after a change.

const JOB_ID = "e2e-test-job";

const PROCESSING_JOB = {
  id: JOB_ID,
  status: "processing",
  filename: "letter.png",
  created_at: "2026-01-01T00:00:00Z",
  result: null,
  error: null,
};

const DONE_JOB = {
  id: JOB_ID,
  status: "done",
  filename: "letter.png",
  created_at: "2026-01-01T00:00:00Z",
  error: null,
  result: {
    filename: "letter.png",
    page_count: 1,
    word_count: 20,
    mean_confidence: 0.9,
    text: "Finanzamt Muenchen Steuerbescheid vom 01.03.2026 Betrag 250,00 EUR faellig 31.03.2026",
    doc_type: "finanzamt",
    doc_type_confidence: 0.95,
    extraction: {
      sender: {
        value: "Finanzamt Muenchen",
        confidence: 0.9,
        source_span: { page: 0, bboxes: [{ x: 0.1, y: 0.1, width: 0.2, height: 0.05 }] },
        validation_issues: [],
      },
      letter_date: {
        value: "2026-03-01",
        confidence: 0.9,
        source_span: null,
        validation_issues: [],
      },
      deadline: { value: "2026-03-31", confidence: 0.9, source_span: null, validation_issues: [] },
      amount: { value: "250.00", confidence: 0.9, source_span: null, validation_issues: [] },
      legal_references: { value: [], confidence: 0.5, source_span: null, validation_issues: [] },
      required_actions: {
        value: ["Pay the amount by the deadline"],
        confidence: 0.85,
        source_span: null,
        validation_issues: [],
      },
    },
    explanation: {
      text: "This is a tax bill from the Finanzamt asking for 250 EUR by March 31.",
      word_count: 14,
      flesch_reading_ease: 70,
      exceeds_word_limit: false,
      below_readability_target: false,
      advice_phrases_found: [],
    },
  },
};

// A minimal valid 1x1 PNG -- content doesn't matter, every response in this
// test is mocked; only its byte validity matters so <img> doesn't error.
const TINY_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

test("happy path: upload a letter and see the full results page", async ({ page }) => {
  let pollCount = 0;

  await page.route("**/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' }),
  );

  await page.route("**/api/v1/jobs", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: JOB_ID, status: "processing" }),
    });
  });

  await page.route(`**/api/v1/jobs/${JOB_ID}`, async (route) => {
    pollCount += 1;
    const body = pollCount < 2 ? PROCESSING_JOB : DONE_JOB;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await page.route(`**/api/v1/jobs/${JOB_ID}/pages/*`, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: TINY_PNG }),
  );

  await page.goto("/");
  await expect(page.getByText("Backend connected")).toBeVisible();

  await page
    .locator("#document")
    .setInputFiles({ name: "letter.png", mimeType: "image/png", buffer: TINY_PNG });
  await page.getByRole("button", { name: "Analyze letter" }).click();

  await expect(page).toHaveURL(`/result/${JOB_ID}`);

  // Terminal state: every major section rendered from the mocked DONE_JOB.
  // (The transient "processing" state has its own dedicated test below --
  // asserting on it here would race against how fast the mocked poll
  // resolves to "done", which isn't a meaningful thing to pin down.)
  await expect(page.getByRole("heading", { name: "Your letter" })).toBeVisible();
  await expect(page.getByText("does not give legal advice")).toBeVisible(); // Disclaimer
  await expect(page.getByText("In plain English")).toBeVisible(); // ExplanationCard
  await expect(page.getByText("What to do")).toBeVisible(); // ActionChecklist
  // Appears twice: once in the checklist, once as the required_actions value
  // in ExtractionSummary -- both are correct, so assert presence, not uniqueness.
  await expect(page.getByText("Pay the amount by the deadline").first()).toBeVisible();
  await expect(page.getByText("Extracted fields")).toBeVisible(); // ExtractionSummary
  await expect(page.getByRole("button", { name: /Finanzamt Muenchen/ })).toBeVisible();
  await expect(page.getByText("Original scan")).toBeVisible(); // DocumentViewer

  // M19: tapping a verified field highlights it in the document viewer.
  await page.getByRole("button", { name: /Finanzamt Muenchen/ }).click();
  await expect(page.locator(".animate-pulse")).toBeVisible();
});

test("the processing state shows an honest, non-terminal message", async ({ page }) => {
  // Poll never resolves to a terminal status -- proves the processing view
  // itself renders correctly, without racing a mock that also transitions.
  await page.route("**/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' }),
  );
  await page.route(`**/api/v1/jobs/${JOB_ID}`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(PROCESSING_JOB),
    }),
  );

  await page.goto(`/result/${JOB_ID}`);

  await expect(page.getByText("Reading your letter…")).toBeVisible();
  await expect(page.getByText("This usually takes a few seconds.")).toBeVisible();
});

test("navigating back to upload another letter returns to the landing page", async ({ page }) => {
  await page.route("**/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' }),
  );
  await page.route(`**/api/v1/jobs/${JOB_ID}`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(DONE_JOB) }),
  );

  await page.goto(`/result/${JOB_ID}`);
  await expect(page.getByRole("heading", { name: "Your letter" })).toBeVisible();

  await page.getByRole("link", { name: /Upload another letter/ }).click();
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { name: "BriefPilot" })).toBeVisible();
});
