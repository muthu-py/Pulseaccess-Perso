import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { initialState, mockApi } from "./mock-api";

test("creator: sign up, log in, connect Telegram, create a community, connect the group, add a plan", async ({ page }) => {
  const state = initialState();
  await mockApi(page, state);

  // Sign up
  await page.goto("/signup");
  await page.getByLabel(/^Name/).fill("Asha Kumar");
  await page.getByLabel("Username").fill("asha_k");
  await page.getByLabel("Email").fill("asha@example.com");
  await page.getByRole("button", { name: "Create account" }).click();

  // Signup already sent the first code, so login opens on the code step. Six digits submit by themselves.
  await expect(page).toHaveURL(/\/login\?registered=1&sent=1/);
  await expect(page.getByText("Account created")).toBeVisible();
  await expect(page.getByText("We sent a 6-digit code to asha@example.com.")).toBeVisible();
  await page.getByLabel("6-digit code").fill("000000");
  // Next also renders its own route announcer with role=alert, so look inside <main>.
  await expect(page.locator('main [role="alert"]')).toContainText("isn't right");
  await page.getByLabel("6-digit code").fill("123456");

  // New creators are sent to onboarding
  await expect(page).toHaveURL(/\/app\/onboarding/);
  await page.getByRole("button", { name: "Connect Telegram" }).click();
  const open = page.getByRole("link", { name: "Open Telegram" });
  await expect(open).toHaveAttribute("href", /t\.me/);

  // The page notices on its own when Telegram confirms
  await expect(page.getByLabel("Community name")).toBeVisible({ timeout: 15_000 });
  await page.getByLabel("Community name").fill("Java Masters");
  await page.getByRole("button", { name: "Create community" }).click();

  // Back on the list, with a text status
  await expect(page).toHaveURL(/\/app$/);
  await page.getByRole("link", { name: /Java Masters/ }).click();
  await expect(page.getByRole("heading", { name: "Java Masters" })).toBeVisible();
  await expect(page.getByText("Waiting for the bot to be added")).toBeVisible();
  await expect(page.getByRole("button", { name: "New plan" })).toBeDisabled();

  // The group connects (simulated); the panel flips by itself and plans unlock
  state.groupStatus = "CONNECTED";
  await expect(page.getByText("-1001234567890")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("button", { name: "New plan" })).toBeEnabled();

  await page.getByRole("button", { name: "New plan" }).click();
  await page.getByLabel("Plan name").fill("Monthly");
  await page.getByLabel("Price").fill("499");
  await page.getByRole("button", { name: "Create plan" }).click();
  await expect(page.getByRole("listitem", { name: "Monthly" })).toContainText("₹499");

  // Log out returns to login
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);
});

test("creator: an earlier session never skips the code on the login page", async ({ page }) => {
  const state = initialState();
  state.creatorLoggedIn = true; // refresh cookie left over from someone else's login
  await mockApi(page, state);

  await page.goto("/login");
  await expect(page.getByText("This browser is already logged in.")).toBeVisible();
  await expect(page.getByText("Naveen", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByRole("button", { name: "Log out and use another account" }).click();
  await page.getByLabel("Email or username").fill("asha_k");
  await page.getByRole("button", { name: "Send code" }).click();
  await page.getByLabel("6-digit code").fill("123456");
  await expect(page).toHaveURL(/\/app/);
});

test("creator: signed-out visitors are sent to login", async ({ page }) => {
  await mockApi(page, initialState());
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login/);
});

test("creator pages have no serious a11y issues and no sideways scroll", async ({ page }) => {
  const state = initialState();
  state.creatorLoggedIn = true;
  state.creatorTelegramConnected = true;
  state.communities = [{ id: "c1", name: "Java Masters", description: "Weekly deep dives" }];
  state.groupStatus = "CONNECTED";
  state.plans = [{ id: "p1", community_id: "c1", name: "Monthly", description: null, price_paise: 49900, price: "499.00", currency: "INR", duration_days: 30, is_active: true, created_at: "2026-10-01T00:00:00Z" }];
  await mockApi(page, state);

  for (const path of ["/signup", "/login", "/app", "/app/communities/c1", "/app/communities/new"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious, `${path}: ${JSON.stringify(serious.map((v) => [v.id, v.nodes.map((n) => n.target)]))}`).toEqual([]);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `${path} scrolls sideways`).toBeLessThanOrEqual(0);
  }
});
