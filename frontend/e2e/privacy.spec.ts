import { expect, test } from "@playwright/test";

// M23: "I can read, in plain language, exactly what happens to my data."
// Proves the page renders and is actually reachable from where a real user
// would look for it -- the landing page and a result page -- not just that
// the route exists in isolation.

test("the privacy page is reachable from the landing page and explains real behavior", async ({
  page,
}) => {
  await page.route("**/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' }),
  );

  await page.goto("/");
  await page.getByRole("link", { name: /What happens to your data/ }).click();

  await expect(page).toHaveURL("/privacy");
  await expect(page.getByRole("heading", { name: "What happens to your document" })).toBeVisible();
  // The two claims M22 actually implements: the 24h ceiling and one-click delete.
  await expect(page.getByText(/24 hours after upload/)).toBeVisible();
  await expect(page.getByText(/Delete my document/)).toBeVisible();
  // The real third-party disclosure -- must not be silently omitted.
  await expect(page.getByText(/Google's Gemini API/)).toBeVisible();

  await page.getByRole("link", { name: /Back to BriefPilot/ }).click();
  await expect(page).toHaveURL("/");
});
