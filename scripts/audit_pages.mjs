// Visits every sidebar page and every tab at 1366x768 and reports: console/page errors, failed or 4xx/5xx requests,
// empty-state phrases, blank charts and horizontal overflow. Optionally saves screenshots (docs/screenshots/<name>-1366.png).
// Usage: node scripts/audit_pages.mjs [--shots]   (UI :5174 + API :8010 running, DB seeded)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const ROOT = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const BASE = process.env.EKATRA_URL ?? "http://localhost:5174";
const OUT = path.join(ROOT, "docs", "screenshots");
const SHOTS = process.argv.includes("--shots");
mkdirSync(OUT, { recursive: true });

const EMPTY = /No data|Nothing to show|Nothing to flag|No cases match|No clusters match|No matches|No overlaps|No open cases|No automatic link|Select a row|Select an|Choose an institution|No results yet|\bLoading\b/i;
const problems = [];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
let where = "";
const note = (kind, msg) => problems.push(`${where}: ${kind} - ${msg}`);
page.on("console", (m) => { if (m.type() === "error") note("console", m.text().slice(0, 160)); });
page.on("pageerror", (e) => note("pageerror", String(e).slice(0, 160)));
page.on("requestfailed", (r) => note("requestfailed", `${r.url().replace(BASE, "")} ${r.failure()?.errorText}`));
page.on("response", (r) => { if (r.status() >= 400 && r.url().includes("/api/")) note(`http ${r.status()}`, r.url().replace(BASE, "")); });

async function check(name, { charts = 0, shot, expect = [] } = {}) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(900);
  const body = await page.evaluate(() => document.body.innerText);
  const m = body.match(EMPTY);
  if (m) note("empty-state text", `"${m[0]}"`);
  for (const t of expect) if (!body.includes(t)) note("missing expected text", `"${t}"`);
  const c = await page.evaluate(() => [...document.querySelectorAll("canvas")].filter((x) => x.width > 40 && x.height > 40).length);
  if (c < charts) note("blank chart", `expected >= ${charts} chart canvases, found ${c}`);
  const ov = await page.evaluate(() => { const m = document.querySelector("main"); return Math.max(document.documentElement.scrollWidth - document.documentElement.clientWidth, m ? m.scrollWidth - m.clientWidth : 0); });
  if (ov > 0) note("horizontal overflow", `${ov}px`);
  if (SHOTS && shot) await page.screenshot({ path: path.join(OUT, `${shot}-1366.png`) });
  console.log(`checked  ${name}`);
}
async function go(p, name, opts) { where = name; await page.goto(BASE + p, { waitUntil: "domcontentloaded" }); await check(name, opts); }

await go("/", "Dashboard", { charts: 3, shot: "dashboard", expect: ["since last reset"] });
await go("/cases", "Case Tracker", { expect: ["PGRC/2026"] });
await go("/case", "Case detail (no case)", { expect: ["PGRC/2026/0457", "Hash chain intact"] });
await go("/institutions", "Institution 360 (default)", { charts: 1, shot: "institution360", expect: ["Shri Venkatadri Institute of Technology", "Possible systemic issue", "SVIT", "Cross-Bureau timeline"] });
await go("/watchlist", "Watchlist", { shot: "watchlist", expect: ["Worsening", "6-MONTH TREND"] });
await go("/overlaps", "Overlap Centre", { shot: "overlap", expect: ["Potential Overlapping Cases – Coordination Required", "Why linked?", "Shri Venkatadri Institute of Technology"] });
await go("/ask", "Ask Ekatra", { shot: "ask", expect: ["Understood as", "Beyond timeline", "matching cases"] });

where = "Alert Centre";
await page.goto(BASE + "/alerts", { waitUntil: "domcontentloaded" });
const tabs = [["Conflicts", null, ["CONFLICTING"]], ["Contradicting findings", "alerts-contradiction", ["days apart", "non-compliant"]], ["Systemic", "alerts-systemic", ["Possible systemic issue"]],
  ["Deadline risk", null, ["due"]], ["Ping-pong", null, ["transfers"]], ["Duplicates", null, ["DUPLICATE"]]];
await check("Alert Centre (landing)");
for (const [label, shot, expect] of tabs) {
  where = `Alert Centre / ${label}`;
  await page.getByRole("button", { name: new RegExp(`^${label}\\s*\\d+`) }).click();
  await check(`Alert Centre / ${label}`, { shot, expect });
}
await go("/reports", "Reports", { charts: 1, shot: "reports", expect: ["Bureau-wise", "CSV", "PDF", "Monthly pack"] });
await go("/audit", "Audit log", { shot: "audit", expect: ["Verify integrity", "events"] });
await go("/evaluation", "Evaluation", { shot: "evaluation", expect: ["Systemic problems found", "Contradictions found", "Risk DNA trend correct"] });
await browser.close();
console.log(problems.length ? `\n${problems.length} PROBLEM(S):\n - ` + problems.join("\n - ") : "\nNo problems found.");
process.exitCode = problems.length ? 1 : 0;
