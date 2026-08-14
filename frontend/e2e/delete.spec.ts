import { expect, test } from "@playwright/test";

// M22: "I can delete my document in one click and know it's really gone."
// Mocks DELETE returning 204, then a subsequent GET returning 404 -- exactly
// what DeleteButton itself checks before claiming success, so this proves
// the two-stage confirm UI wires correctly into that verification, not just
// that clicking a button shows a message.

const JOB_ID = "e2e-delete-job";

const DONE_JOB = {
  id: JOB_ID,
  status: "done",
  filename: "letter.png",
  created_at: "2026-01-01T00:00:00Z",
  error: null,
  result: {
    filename: "letter.png",
    page_count: 1,
    word_count: 5,
    mean_confidence: 0.9,
    text: "Finanzamt Muenchen",
    doc_type: null,
    doc_type_confidence: null,
    extraction: null,
    explanation: null,
  },
};

test("deleting a document requires confirmation, then verifies it's really gone", async ({
  page,
}) => {
  let deleted = false;

  await page.route("**/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' }),
  );

  await page.route(`**/api/v1/jobs/${JOB_ID}`, async (route) => {
    if (route.request().method() === "DELETE") {
      deleted = true;
      await route.fulfill({ status: 204 });
      return;
    }
    if (deleted) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: '{"detail":"Job not found."}',
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(DONE_JOB),
    });
  });

  await page.goto(`/result/${JOB_ID}`);
  await expect(page.getByRole("heading", { name: "Your letter" })).toBeVisible();

  const deleteButton = page.getByRole("button", { name: "Delete my document" });
  await expect(deleteButton).toBeVisible();
  await deleteButton.click();

  // One click doesn't delete anything yet -- a confirm step is required.
  await expect(page.getByText("Delete this document?")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your letter" })).toBeVisible();

  await page.getByRole("button", { name: "Yes, delete it" }).click();

  await expect(
    page.getByText("Deleted. This document and everything extracted from it are gone"),
  ).toBeVisible();
});

test("canceling the confirm step leaves the document untouched", async ({ page }) => {
  await page.route("**/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' }),
  );
  await page.route(`**/api/v1/jobs/${JOB_ID}`, async (route) => {
    if (route.request().method() === "DELETE") {
      throw new Error("DELETE should never be called after Cancel");
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(DONE_JOB),
    });
  });

  await page.goto(`/result/${JOB_ID}`);
  await page.getByRole("button", { name: "Delete my document" }).click();
  await page.getByRole("button", { name: "Cancel" }).click();

  await expect(page.getByRole("button", { name: "Delete my document" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your letter" })).toBeVisible();
});
