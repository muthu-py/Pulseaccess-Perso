import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;

// E2E runs against a production build with the API mocked in the browser (see e2e/mock-api.ts),
// so it needs no backend, database, Telegram or Razorpay.
export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    // About 400px wide, as on a small phone.
    { name: "mobile", use: { ...devices["Desktop Chrome"], viewport: { width: 400, height: 800 } } },
  ],
  webServer: {
    command: `npm run build && npx next start -p ${PORT}`,
    url: `http://localhost:${PORT}`,
    timeout: 180_000,
    reuseExistingServer: !process.env.CI,
  },
});
