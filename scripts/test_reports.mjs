// Clicks CSV, PDF and Monthly pack on the Reports page and checks each response is a real, non-empty file.
import { chromium } from "playwright";
const BASE = process.env.EKATRA_URL ?? "http://localhost:5174";
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 }, acceptDownloads: true });
const page = await ctx.newPage();
const seen = [];
ctx.on("response", async (r) => {
  if (r.url().includes("/api/reports/") && r.url().includes("format=")) {
    const body = await r.body().catch(() => Buffer.alloc(0));
    seen.push({ url: r.url().replace(BASE, ""), status: r.status(), type: r.headers()["content-type"], bytes: body.length, head: body.subarray(0, 5).toString("latin1") });
  }
});
let bad = 0;
const ok = (c, m) => { console.log(`${c ? "PASS" : "FAIL"}  ${m}`); if (!c) bad++; };
await page.goto(BASE + "/reports", { waitUntil: "networkidle" });

const [dl] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "CSV", exact: true }).click()]);
const csvPath = await dl.path();
const { readFileSync } = await import("node:fs");
const csv = readFileSync(csvPath, "utf8");
ok(csv.length > 40 && csv.split("\n").length >= 6, `CSV downloaded as "${dl.suggestedFilename()}" (${csv.length} bytes, ${csv.trim().split("\n").length} lines): ${csv.split("\n")[0]}`);

const [pdfTab] = await Promise.all([ctx.waitForEvent("page"), page.getByRole("button", { name: "PDF", exact: true }).click()]);
await pdfTab.waitForLoadState("load").catch(() => {});
const [packTab] = await Promise.all([ctx.waitForEvent("page"), page.getByRole("button", { name: /Monthly pack/ }).click()]);
await packTab.waitForLoadState("load").catch(() => {});
await page.waitForTimeout(1500);

const verify = async (label, hit) => {
  // Chromium does not expose the body of a PDF navigation, so fetch the exact URL the button opened.
  const r = hit ? await ctx.request.get(BASE + hit.url) : null;
  const body = r ? await r.body() : Buffer.alloc(0);
  ok(!!hit && hit.status === 200 && r.ok() && body.subarray(0, 5).toString("latin1").startsWith("%PDF") && body.length > 1000,
     `${label}: click opened ${hit ? hit.url : "nothing"} -> ${hit?.status} ${hit?.type}, file is ${body.length} bytes, header ${JSON.stringify(body.subarray(0, 5).toString("latin1"))}`);
};
await verify("PDF", seen.find((s) => s.url.includes("/reports/bureau") && s.url.includes("pdf")));
await verify("Monthly pack", seen.find((s) => s.url.includes("monthly-pack")));
await browser.close();
process.exitCode = bad ? 1 : 0;
