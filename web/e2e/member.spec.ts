import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { initialState, mockApi } from "./mock-api";

test("member: opens a community link, logs in, pays and sees the real payment status", async ({ page, context }) => {
  const state = initialState();
  await mockApi(page, state);

  // A logged-out visitor on a community link is sent to login and brought back
  await page.goto("/c/c1");
  await expect(page).toHaveURL(/\/m\/login\?next=%2Fc%2Fc1/);
  await page.getByLabel("Email").fill("ravi@example.com");
  await page.getByRole("button", { name: "Send code" }).click();
  await page.getByLabel("6-digit code").fill("123456");

  await expect(page).toHaveURL(/\/c\/c1$/);
  await expect(page.getByText("30 days")).toBeVisible();
  await page.getByRole("button", { name: "Pay for Monthly" }).click();

  // Payment page: pay link opens in a new tab, status comes from the backend
  await expect(page).toHaveURL(/\/m\/payments\/pay1/);
  await expect(page.getByText("Awaiting payment")).toBeVisible();
  const payLink = page.getByRole("link", { name: /Pay ₹499 on Razorpay/ });
  await expect(payLink).toHaveAttribute("target", "_blank");
  await expect(payLink).toHaveAttribute("href", "https://rzp.io/l/abc");

  // Razorpay confirms (simulated): the page updates itself, no click needed
  state.paymentStatus = "paid";
  await expect(page.getByText("Payment received.")).toBeVisible({ timeout: 15_000 });
  await expect(payLink).toHaveCount(0);

  await page.getByRole("link", { name: "My subscriptions" }).first().click();
  await expect(page.getByText("Active")).toBeVisible();
  void context;
});

test("member: asked to connect Telegram before paying, then returned to the plans", async ({ page }) => {
  const state = initialState();
  state.memberLoggedIn = true;
  state.memberTelegramConnected = false;
  await mockApi(page, state);

  await page.goto("/m/login?next=%2Fc%2Fc1");
  await page.getByLabel("Email").fill("ravi@example.com");
  await page.getByRole("button", { name: "Send code" }).click();
  await page.getByLabel("6-digit code").fill("123456");

  await expect(page.getByText("Connect Telegram before you pay.")).toBeVisible();
  await page.getByRole("main").getByRole("link", { name: "Connect Telegram" }).click();
  await expect(page).toHaveURL(/\/m\/connect-telegram\?next=%2Fc%2Fc1/);
  await expect(page.getByText("+919876543210")).toBeVisible();
});

test("member: a rejected token sends them back to login", async ({ page }) => {
  const state = initialState();
  await mockApi(page, state);

  await page.goto("/m/login?next=%2Fm%2Fsubscriptions");
  await page.getByLabel("Email").fill("ravi@example.com");
  await page.getByRole("button", { name: "Send code" }).click();
  await page.getByLabel("6-digit code").fill("123456");
  await expect(page).toHaveURL(/\/m\/subscriptions/);

  await expect(page.getByRole("heading", { name: "My subscriptions" })).toBeVisible();

  // A reload (or coming back from the Razorpay tab) keeps them logged in.
  await page.reload();
  await expect(page.getByRole("heading", { name: "My subscriptions" })).toBeVisible();

  // The server stops accepting the token. The next request that member makes finds out.
  await page.route("**/api/v1/telegram/connect/member", (route) =>
    route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Token expired" }) }),
  );
  await page.getByRole("link", { name: "Telegram", exact: true }).click();
  await expect(page).toHaveURL(/\/m\/login\?next=/);
});

test("member pages have no serious a11y issues and no sideways scroll", async ({ page }) => {
  const state = initialState();
  state.memberLoggedIn = true;
  await mockApi(page, state);

  // Log in once so the member token exists
  await page.goto("/m/login?next=%2Fc%2Fc1");
  await page.getByLabel("Email").fill("ravi@example.com");
  await page.getByRole("button", { name: "Send code" }).click();
  await page.getByLabel("6-digit code").fill("123456");
  await expect(page.getByText("30 days")).toBeVisible();

  const checks: [string, () => Promise<void>][] = [
    ["plans", async () => {}],
    ["subscriptions", async () => { await page.getByRole("link", { name: "My subscriptions" }).click(); await expect(page.getByRole("heading", { name: "My subscriptions" })).toBeVisible(); }],
    ["telegram", async () => { await page.getByRole("link", { name: "Telegram", exact: true }).click(); await expect(page.getByRole("heading", { name: "Connect Telegram" })).toBeVisible(); }],
  ];

  for (const [name, go] of checks) {
    await go();
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious, `${name}: ${JSON.stringify(serious.map((v) => [v.id, v.nodes.map((n) => n.target)]))}`).toEqual([]);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `${name} scrolls sideways`).toBeLessThanOrEqual(0);
  }
});

test("member login works by keyboard alone", async ({ page }) => {
  await mockApi(page, initialState());
  await page.goto("/m/login");
  await page.getByLabel("Email").focus();
  await page.keyboard.type("ravi@example.com");
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("6-digit code")).toBeVisible();
  await page.keyboard.type("123456");
  await expect(page).toHaveURL(/\/m\/subscriptions/);
});
