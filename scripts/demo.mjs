// End-to-end demo check: final screenshots, real-UI interlock click-through, audit verification, then reset.
// Usage: node scripts/demo.mjs   (API on :8010 and UI on :5174 must be running; the reset reseeds the DB)
import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const ROOT = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const BASE = process.env.EKATRA_URL ?? "http://localhost:5174";
const OUT = path.join(ROOT, "docs", "screenshots");
mkdirSync(OUT, { recursive: true });
const shot = (page, name) => page.screenshot({ path: path.join(OUT, `${name}-1366.png`) });
const api = async (p, init) => (await fetch(`${BASE}/api${p}`, init)).json();
const ok = (cond, msg) => { console.log(`${cond ? "PASS" : "FAIL"}  ${msg}`); if (!cond) process.exitCode = 1; };

const baseline = await api("/dashboard/summary");
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
const settle = () => page.waitForTimeout(900);

// ---- clean-state screenshots --------------------------------------------------
await page.goto(BASE + "/", { waitUntil: "networkidle" }); await settle();
ok((await page.evaluate(() => { const m = document.querySelector("main"); return m.scrollHeight - m.clientHeight; })) <= 0, "dashboard fits 1366x768 without scrolling");
await shot(page, "dashboard");

await page.goto(BASE + "/overlaps", { waitUntil: "networkidle" }); await settle();
ok(await page.getByText("Potential Overlapping Cases – Coordination Required").isVisible(), "Overlap Centre banner text is exact");
ok(await page.getByRole("heading", { name: "Shri Venkatadri Institute of Technology" }).isVisible(), "SVIT cluster is selected first");
await shot(page, "hero_overlap");
await page.evaluate(() => document.querySelector("main").scrollTo(0, 330)); await page.waitForTimeout(300);
await shot(page, "hero_overlap_why");
await page.evaluate(() => document.querySelector("main").scrollTo(0, 0));

await page.goto(BASE + "/cases/PGRC/2026/0457", { waitUntil: "networkidle" }); await settle();
await shot(page, "casedetail");
await page.goto(BASE + "/institutions/1", { waitUntil: "networkidle" }); await settle();
await shot(page, "institution360");
await page.goto(BASE + "/evaluation", { waitUntil: "networkidle" }); await settle();
await shot(page, "evaluation");

// ---- interlock click-through (real UI) ----------------------------------------
await page.goto(BASE + "/cases/PGRC/2026/0457", { waitUntil: "networkidle" }); await settle();
await page.getByRole("button", { name: "Dispose", exact: true }).first().click();
await page.getByRole("button", { name: "Confirm Dispose" }).click();
await page.getByText("Action paused – linked case active").waitFor();
ok(await page.getByRole("dialog").getByRole("link", { name: "RB/2026/1182" }).isVisible(), "interlock modal names RB/2026/1182 as the blocker");
ok(/show-cause issued/.test(await page.getByRole("dialog").innerText()), "modal mentions show-cause issued");
await settle(); await shot(page, "interlock");

await page.getByRole("button", { name: "Assign Lead Bureau" }).click();
await page.getByRole("button", { name: "Confirm Lead Bureau: RB" }).click();
await page.getByText(/Lead Bureau RB assigned/).waitFor();
ok(true, "Assign Lead Bureau: RB recorded (dispose deferred)");
await settle();
ok(!(await page.getByText("Disposed", { exact: true }).first().isVisible().catch(() => false)), "case was NOT disposed by assigning a lead");

await page.getByRole("button", { name: "Dispose", exact: true }).first().click();
await page.getByRole("button", { name: "Confirm Dispose" }).click();
await page.getByText("Action paused – linked case active").waitFor();
await page.getByRole("button", { name: "Record reason & continue" }).click();
const cont = page.getByRole("button", { name: "Continue with reason" });
ok(await cont.isDisabled(), "'Continue with reason' disabled until a reason is typed");
await page.getByRole("dialog").locator("textarea").fill("short");
ok(await cont.isDisabled(), "…and still disabled for a reason under 10 characters");
await page.getByRole("dialog").locator("textarea").fill("RB confirmed the show-cause concerns a different lab block");
await cont.click();
await page.getByText("Disposed", { exact: true }).first().waitFor();
ok(true, "Record reason & continue → case disposed");
await settle();

// ---- audit chain --------------------------------------------------------------
await page.goto(BASE + "/audit", { waitUntil: "networkidle" }); await settle();
await page.getByRole("button", { name: "Verify integrity" }).click();
await page.getByText(/Chain intact – [\d,]+ events/).waitFor();
ok(true, "Audit log: " + (await page.getByText(/Chain intact/).innerText()));
await shot(page, "audit");
const log = await api("/audit?limit=8");
const acts = log.items.map((e) => e.action);
ok(acts.includes("interlock.lead_assigned") && acts.includes("interlock.override") && acts.includes("case.dispose"), `audit has lead_assigned, override, dispose (newest first: ${acts.slice(0, 6).join(", ")})`);
const ev = await api("/interlock/events");
ok(ev.length === 2 && ev.some((e) => e.outcome === "lead_assigned") && ev.some((e) => e.outcome === "override_with_reason" && e.reason.length >= 10), "2 InterlockEvents logged with outcomes + reason");
const caseNow = await api("/cases/PGRC/2026/0457");
console.log("DEBUG timeline:", caseNow.timeline.slice(-3).map((t) => `${t.action}: ${t.remarks.slice(0, 70)}`));
console.log("DEBUG audit:", JSON.stringify(log.items.slice(0, 3).map((e) => [e.id, e.action, e.entity])));
ok(caseNow.chain_intact === true && caseNow.status === "Disposed", "case timeline hash chain intact after actions");
await browser.close();

// ---- reset so the demo starts clean ---------------------------------------------
console.log("Resetting demo data (reseed)…");
const py = path.join(ROOT, "backend", ".venv", "Scripts", "python.exe");
const r = spawnSync(py, ["-m", "data.generator.seed", "--seed", "42"], { cwd: ROOT, env: { ...process.env, PYTHONIOENCODING: "utf-8" }, encoding: "utf8" });
ok(r.status === 0, "reseed finished");
const s = await api("/dashboard/summary");
ok(s.conflicts_blocked === 0 && s.disposed === baseline.disposed && s.total === baseline.total, `demo reset: conflicts_blocked=${s.conflicts_blocked}, disposed=${s.disposed} (was ${baseline.disposed}), total=${s.total}`);
const v = await api("/audit/verify", { method: "POST" });
ok(v.intact, `audit chain intact after reset (${v.events} events)`);
