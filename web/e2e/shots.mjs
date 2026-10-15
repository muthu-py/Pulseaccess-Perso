import { chromium } from "@playwright/test";
const b = await chromium.launch();
const pages = [["/", "home"], ["/how-it-works", "how"], ["/login", "login"], ["/signup", "signup"], ["/ui", "ui"]];
for (const [w, tag] of [[1280, "d"], [400, "m"]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
  const page = await ctx.newPage();
  await page.route("**/api/v1/**", (r) => r.fulfill({ status: 401, contentType: "application/json", body: "{}" }));
  for (const [p, n] of pages) {
    await page.goto("http://localhost:3000" + p);
    await page.waitForTimeout(600);
    await page.screenshot({ path: `C:/Users/neele/AppData/Local/Temp/shots-${n}-${tag}.png`, fullPage: false });
  }
  await ctx.close();
}
await b.close();
