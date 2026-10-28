// Follows the README's 2-minute click-path exactly, in the real UI, and checks what each step shows.
// Starts from a clean demo (run .\reset_demo.ps1 first) and leaves the demo dirty (it assigns a Lead Bureau): reset afterwards.
import { chromium } from "playwright";
const BASE = process.env.EKATRA_URL ?? "http://localhost:5174";
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
const page = await ctx.newPage();
let bad = 0;
const ok = (c, m) => { console.log(`${c ? "PASS" : "FAIL"}  ${m}`); if (!c) bad++; };
const settle = () => page.waitForTimeout(800);
const text = () => page.evaluate(() => document.body.innerText);

await page.goto(BASE + "/", { waitUntil: "networkidle" }); await settle();
let t = await text();
ok(/Open overlaps\s*\n?\s*110/.test(t) && t.includes("Command Dashboard"), "0:00 Dashboard opens by default with Open overlaps = 110");
await page.getByRole("button", { name: /Shri Venkatadri Institute of Technology/ }).click(); await settle();
t = await text();
ok(page.url().includes("/overlaps?cluster=") && t.includes("Potential Overlapping Cases – Coordination Required"), "0:15 Needs attention → Overlap Centre");
ok(t.includes("SVIT, Tirupati - 517502") && t.includes("श्री वेंकटाद्रि") && t.includes("Sri Venkatadri Inst. of Tech."), "0:20 the three spellings (incl. Devanagari) are listed");
ok(t.includes("Why linked?") && t.includes("pincode 517502 found") && t.includes("1.00"), "0:20 Why linked? shows acronym, pincode 517502 and confidence 1.00 for the first row");
await page.getByRole("row", { name: /RB\/2026\/1182/ }).click(); await settle();
t = await text();
ok(t.includes("floored at 0.92") && t.includes("0.92"), "0:40 clicking RB/2026/1182 shows the 0.92 exact-alias note");

await page.getByRole("link", { name: "PGRC/2026/0457" }).first().click(); await settle();
await page.getByRole("button", { name: "Dispose", exact: true }).first().click();
await page.getByRole("button", { name: "Confirm Dispose" }).click();
await page.getByText("Action paused – linked case active").waitFor();
ok(true, "1:00 Dispose → Confirm Dispose → interlock modal");
await page.getByRole("button", { name: "Assign Lead Bureau" }).click();
await page.getByRole("button", { name: "Confirm Lead Bureau: RB" }).click();
await page.getByText(/Lead Bureau RB assigned/).waitFor();
ok(true, "1:15 Assign Lead Bureau → RB confirmed");

await page.getByRole("link", { name: "Shri Venkatadri Institute of Technology" }).first().click(); await settle();
t = await text();
ok(t.includes("Institution 360°") && t.includes("श्री वेंकटाद्रि") && t.includes("Possible systemic issue") && t.includes("Cross-Bureau timeline"), "1:25 Institution 360°: Hindi alias, systemic card, timeline");
const sys = t.match(/(\d+) different problems reported to (\d+) Bureaus/);
console.log(`      systemic text: ${sys ? sys[0] : "not found"}`);
const briefResp = ctx.waitForEvent("response", (r) => r.url().includes("/brief.pdf"));
await page.getByRole("button", { name: /Generate Institution Brief/ }).click();
const br = await briefResp;
ok(br.status() === 200 && (br.headers()["content-type"] ?? "").includes("pdf"), `1:35 Generate Institution Brief opens a PDF in a new tab (${br.status()} ${br.headers()["content-type"]})`);

await page.getByRole("link", { name: "Audit log" }).click(); await settle();
await page.getByRole("button", { name: "Verify integrity" }).click();
await page.getByText(/Chain intact – [\d,]+ events/).waitFor();
ok(true, "1:45 Audit log → " + (await page.getByText(/Chain intact/).innerText()));

await page.getByRole("link", { name: "Alert Centre" }).click(); await settle();
await page.getByRole("button", { name: /^Contradicting findings\s*\d+/ }).click(); await settle();
ok((await text()).includes("days apart") || (await text()).includes("day apart"), "1:52 Alert Centre → Contradicting findings shows side-by-side verdicts");
await page.getByRole("link", { name: "Evaluation" }).click(); await settle();
t = await text();
ok(t.includes("6.5×") && t.includes("15 / 16") && t.includes("5 / 5"), "1:58 Evaluation shows 6.5×, 15 / 16 and systemic 5 / 5");
await browser.close();
process.exitCode = bad ? 1 : 0;
