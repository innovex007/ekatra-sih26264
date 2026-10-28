// Screenshots every route at 1366x768 and 1920x1080 and fails on horizontal overflow.
// Usage: node scripts/screenshots.mjs [outDir]   (UI must be running on http://localhost:5174)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BASE = process.env.EKATRA_URL ?? "http://localhost:5174";
const OUT = process.argv[2] ?? fileURLToPath(new URL("../docs/screenshots", import.meta.url));
const ROUTES = {
  dashboard: "/", cases: "/cases", institutions: "/institutions/1", watchlist: "/watchlist",
  overlap: "/overlaps", casedetail: "/cases/PGRC/2026/0457", ask: "/ask", alerts: "/alerts", reports: "/reports", audit: "/audit", evaluation: "/evaluation",
};
const SIZES = [[1366, 768], [1920, 1080]];

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
let bad = 0;
for (const [w, h] of SIZES) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  for (const [name, path] of Object.entries(ROUTES)) {
    await page.goto(BASE + path, { waitUntil: "networkidle" });
    await page.waitForTimeout(700);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    const inner = await page.evaluate(() => {
      const m = document.querySelector("main");
      return m ? m.scrollWidth - m.clientWidth : 0;
    });
    const vscroll = name === "dashboard" ? await page.evaluate(() => { const m = document.querySelector("main"); return m.scrollHeight - m.clientHeight; }) : 0;
    if (vscroll > 0 && h <= 768) console.log(`SCROLLS   ${w}x${h} dashboard needs ${vscroll}px of vertical scroll`);
    const flag = overflow > 0 || inner > 0 || (vscroll > 0 && h <= 768);
    if (flag) bad++;
    console.log(`${flag ? "OVERFLOW" : "ok      "} ${w}x${h} ${name} (page ${overflow}px, main ${inner}px)`);
    await page.screenshot({ path: `${OUT}/${name}-${w}.png` });
  }
  await page.close();
}
await browser.close();
process.exit(bad ? 1 : 0);
