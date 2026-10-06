// shots.mjs — screenshots of the real app at phone sizes (light + dark), plus a scripted accessibility audit:
// accessible names on every control, tap-target sizes, text sizes and contrast of visible text.
//   node tools/shots.mjs [--url http://127.0.0.1:8787/] [--out build/shots]
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { AUDIT_JS } from "./audit-lib.mjs";

const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => (a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : [])).filter((x) => x.length));
const URL_ = args.url || "http://127.0.0.1:8787/";
const OUT = path.resolve(args.out || "build/shots");
fs.mkdirSync(OUT, { recursive: true });

const SIZES = [{ name: "390x844", width: 390, height: 844, dpr: 3 }, { name: "360x780", width: 360, height: 780, dpr: 2.75 }, { name: "768x1024", width: 768, height: 1024, dpr: 2 }];
const browser = await chromium.launch({ args: ["--no-sandbox"] });
const audit = { controls: [], smallTargets: [], smallText: [], lowContrast: [], pages: [] };


for (const scheme of ["light", "dark"]) {
  for (const sz of SIZES) {
    const ctx = await browser.newContext({ viewport: { width: sz.width, height: sz.height }, deviceScaleFactor: sz.dpr, isMobile: sz.width < 700, hasTouch: true, colorScheme: scheme });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    const tag = `${scheme}-${sz.name}`;
    await page.goto(URL_, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("html[data-ready='1']", { timeout: 180000 });
    await page.waitForTimeout(400);
    const shoot = async (name) => { await page.screenshot({ path: `${OUT}/${tag}-${name}.png` }); const a = await page.evaluate(AUDIT_JS); audit.pages.push({ page: `${tag}-${name}`, ...a }); };
    await shoot("1-home");
    await page.fill("#q", "peanut butter"); await page.waitForTimeout(400); await shoot("2-results");
    await page.locator("#list .row").first().click(); await page.waitForSelector("#sheet[open]"); await page.waitForTimeout(600); await shoot("3-sheet");
    await page.click("#sheet [data-act=add]"); await page.waitForTimeout(300);
    await page.fill("#q", "4011"); await page.waitForTimeout(300); await page.press("#q", "Enter"); await page.waitForSelector("#sheet[open]"); await page.waitForTimeout(500); await shoot("4-plu");
    await page.click("#sheet .x-btn"); await page.waitForTimeout(400);
    await page.fill("#q", "201234928759"); await page.waitForTimeout(300); await page.press("#q", "Enter"); await page.waitForSelector("#sheet[open]"); await page.waitForTimeout(500); await shoot("5-label");
    await page.click("#sheet .x-btn"); await page.waitForTimeout(400);
    await page.fill("#q", "corn 99 oz"); await page.waitForTimeout(400); await shoot("6-closest");
    await page.locator("#list .row").first().click(); await page.waitForSelector("#sheet[open]"); await page.waitForTimeout(500); await shoot("7-closest-sheet");
    await page.click("#sheet .x-btn"); await page.waitForTimeout(400);
    await page.click("#tallyBtn"); await page.waitForSelector("#tallySheet[open]"); await page.waitForTimeout(500); await shoot("8-tally");
    await page.click("#tallySheet .x-btn"); await page.waitForTimeout(400);
    await page.click("#settingsBtn"); await page.waitForSelector("#settings[open]"); await page.waitForTimeout(500); await shoot("9-settings");
    await page.click("#settings .x-btn"); await page.waitForTimeout(300);
    await page.fill("#q", ""); await page.waitForTimeout(300); await shoot("10-home-recent");
    if (errors.length) audit.pages.push({ page: tag, errors });
    await ctx.close();
  }
}
await browser.close();
const flat = (k) => audit.pages.flatMap((p) => (p[k] || []).map((x) => ({ page: p.page, ...x })));
const summary = {
  pages: audit.pages.length,
  missingNames: flat("controls").filter((c) => c.missingName),
  smallTargets: flat("smallTargets"),
  smallText: flat("smallText"),
  lowContrast: flat("lowContrast"),
  errors: audit.pages.filter((p) => p.errors).map((p) => ({ page: p.page, errors: p.errors })),
};
fs.writeFileSync(`${OUT}/audit.json`, JSON.stringify({ summary, pages: audit.pages }, null, 2));
console.log(JSON.stringify(summary, null, 2));
console.log(`screenshots -> ${OUT}`);
