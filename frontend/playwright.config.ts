import { defineConfig, devices } from "@playwright/test";

// M20: "the full journey keeps working from one release to the next." A
// FAST smoke test against the frontend's own rendering logic -- API
// responses are mocked via route interception in the spec itself, so this
// needs no live backend, no Tesseract, no Gemini key/quota (a genuinely
// free, deterministic CI check, unlike the backend's real-Tesseract e2e
// tests). `webServer` boots the actual Next.js dev server so the test hits
// real rendered HTML, not a component in isolation.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
