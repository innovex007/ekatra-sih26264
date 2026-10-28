// v2 screenshots at 1366x768: systemic card, contradicting findings, risk-DNA watchlist.
// Usage: node scripts/v2shots.mjs   (UI :5174 + API :8010 running, DB seeded)
import { chromium } from "playwright";
import { readFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const ROOT = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const BASE = process.env.EKATRA_URL ?? "http://localhost:5174";
const OUT = path.join(ROOT, "docs", "screenshots");
mkdirSync(OUT, { recursive: true });
const key = JSON.parse(readFileSync(path.join(ROOT, "data", "answer_key.json"), "utf8"));
const ok = (c, m) => { console.log(`${c ? "PASS" : "FAIL"}  ${m}`); if (!c) process.exitCode = 1; };

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
const settle = () => page.waitForTimeout(900);

// 1. Institution 360 with the systemic card (a planted institution)
await page.goto(`${BASE}/institutions/${key.systemic.planted[0]}`, { waitUntil: "networkidle" }); await settle();
ok(await page.getByText("Possible systemic issue").isVisible(), "Institution 360° shows the systemic card");
await page.evaluate(() => document.querySelector("main").scrollTo(0, 215)); await page.waitForTimeout(300);
await page.screenshot({ path: path.join(OUT, "systemic-1366.png") });

// 2. Alert Centre -> Contradicting findings
await page.goto(`${BASE}/alerts`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /Contradicting findings/ }).click(); await settle();
ok(await page.getByText("Contradicting findings").first().isVisible() && (await page.getByText("days apart").count()) > 0, "Alert Centre lists contradicting findings side by side");
await page.screenshot({ path: path.join(OUT, "contradiction-1366.png") });

// 3. Watchlist with Risk DNA trends
await page.goto(`${BASE}/watchlist`, { waitUntil: "networkidle" }); await settle();
ok((await page.getByText("Worsening", { exact: true }).count()) > 0, "Watchlist shows trend badges and sparklines");
await page.screenshot({ path: path.join(OUT, "riskdna-1366.png") });
await browser.close();
