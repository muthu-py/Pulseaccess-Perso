import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const PAGES = ["/", "/how-it-works", "/telegram-bot", "/faq", "/privacy", "/terms", "/contact"];

for (const path of PAGES) {
  test(`public page ${path}: heading, title, no serious a11y issues, no sideways scroll`, async ({ page }) => {
    await page.goto(path);

    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page).toHaveTitle(/PulseAccess/);

    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious, JSON.stringify(serious.map((v) => [v.id, v.nodes.map((n) => n.target)]))).toEqual([]);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test("titles are unique across public pages", async ({ page }) => {
  const titles = new Set<string>();
  for (const path of PAGES) {
    await page.goto(path);
    titles.add(await page.title());
  }
  expect(titles.size).toBe(PAGES.length);
});

test("skip link jumps to main content and is the first tab stop", async ({ page }) => {
  await page.goto("/faq");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await expect(skip).toBeFocused();
  await expect(skip).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("robots and sitemap: public pages listed, app areas excluded", async ({ request }) => {
  const robots = await (await request.get("/robots.txt")).text();
  for (const area of ["/app", "/m", "/c", "/ui"]) expect(robots).toContain(`Disallow: ${area}`);
  expect(robots).toContain("sitemap.xml");

  const sitemap = await (await request.get("/sitemap.xml")).text();
  expect(sitemap).toContain("/how-it-works");
  expect(sitemap).not.toMatch(/\/app|\/m\/|\/c\/|\/ui/);
});

test("app, member and UI-kit pages are noindex", async ({ page }) => {
  for (const path of ["/app", "/m/login", "/ui"]) {
    await page.goto(path);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  }
});
