// shots.mjs — screenshots of the real app at phone sizes (light + dark), plus a scripted accessibility audit:
// accessible names on every control, tap-target sizes, text sizes and contrast of visible text.
// --browser webkit runs the same script in WebKit (every iPhone browser's engine) with an iPhone user agent at phone
// sizes; its files are prefixed "webkit-" and default to build/shots-webkit so the two runs never overwrite each other.
//   node tools/shots.mjs [--browser chromium|webkit] [--url http://127.0.0.1:8787/] [--out build/shots]
import { chromium, webkit, devices } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { AUDIT_JS, browserNote, foldNotes } from "./audit-lib.mjs";

const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => (a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : [])).filter((x) => x.length));
const BROWSER = String(args.browser || "chromium").toLowerCase();
if (BROWSER !== "chromium" && BROWSER !== "webkit") { console.error(`shots: --browser must be chromium or webkit (got ${args.browser})`); process.exit(2); }
const IS_CHROMIUM = BROWSER === "chromium";
const URL_ = args.url || "http://127.0.0.1:8787/";
const OUT = path.resolve(args.out || (IS_CHROMIUM ? "build/shots" : `build/shots-${BROWSER}`));
fs.mkdirSync(OUT, { recursive: true });

const SIZES = [{ name: "390x844", width: 390, height: 844, dpr: 3 }, { name: "360x780", width: 360, height: 780, dpr: 2.75 }, { name: "768x1024", width: 768, height: 1024, dpr: 2 }];
// --no-sandbox is a Chromium switch; WebKit takes no launch arguments here
const exe = process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {};   // a preinstalled Chromium
const browser = IS_CHROMIUM ? await chromium.launch({ args: ["--no-sandbox"], ...exe }) : await webkit.launch();
const IPHONE_UA = devices["iPhone 14"]?.userAgent;
const audit = { controls: [], smallTargets: [], smallText: [], lowContrast: [], pages: [] };
let failed = 0;


for (const scheme of ["light", "dark"]) {
  for (const sz of SIZES) {
    const options = { viewport: { width: sz.width, height: sz.height }, deviceScaleFactor: sz.dpr, isMobile: sz.width < 700, hasTouch: true, colorScheme: scheme };
    if (!IS_CHROMIUM && sz.width < 700 && IPHONE_UA) options.userAgent = IPHONE_UA;   // phone sizes look like Safari on iPhone
    const ctx = await browser.newContext(options);
    // unhandled promise rejections are logged as console errors, so they count whether or not the engine also
    // reports them as a "pageerror"
    await ctx.addInitScript(() => addEventListener("unhandledrejection", (e) => console.error(`Unhandled promise rejection: ${e.reason?.message || e.reason}`)));
    const page = await ctx.newPage();
    const errors = [], notes = [];
    page.on("pageerror", (e) => errors.push(e.message));
    // console.error is a page error unless it is a known, harmless browser message (audit-lib.mjs BROWSER_NOTES)
    page.on("console", (m) => {
      if (m.type() !== "error") return;
      const note = browserNote(m.text());
      if (note) { if (!notes.some((n) => n.message === note.message)) notes.push(note); } else errors.push(m.text());
    });
    const tag = `${IS_CHROMIUM ? "" : `${BROWSER}-`}${scheme}-${sz.name}`;
    try {
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
      await page.fill("#q", "201234928751"); await page.waitForTimeout(300); await page.press("#q", "Enter"); await page.waitForSelector("#sheet[open]"); await page.waitForTimeout(500); await shoot("5-label");
      await page.click("#sheet .x-btn"); await page.waitForTimeout(400);
      await page.fill("#q", "corn 99 oz"); await page.waitForTimeout(400); await shoot("6-closest");
      await page.locator("#list .row").first().click(); await page.waitForSelector("#sheet[open]"); await page.waitForTimeout(500); await shoot("7-closest-sheet");
      await page.click("#sheet .x-btn"); await page.waitForTimeout(400);
      await page.click("#tallyBtn"); await page.waitForSelector("#tallySheet[open]"); await page.waitForTimeout(500); await shoot("8-tally");
      await page.click("#tallySheet .x-btn"); await page.waitForTimeout(400);
      await page.click("#settingsBtn"); await page.waitForSelector("#settings[open]"); await page.waitForTimeout(500); await shoot("9-settings");
      await page.click("#settings .x-btn"); await page.waitForTimeout(300);
      await page.fill("#q", ""); await page.waitForTimeout(300); await shoot("10-home-recent");
    } catch (err) {
      // one size failing (a step that never finishes in this browser) is recorded with a picture of where it stopped;
      // the remaining sizes still run, and the run exits non-zero
      failed++;
      errors.push(`run stopped: ${String(err?.message || err).split("\n")[0]}`);
      await page.screenshot({ path: `${OUT}/${tag}-failed.png` }).catch(() => {});
    }
    if (errors.length || notes.length) audit.pages.push({ page: tag, ...(errors.length ? { errors } : {}), ...(notes.length ? { notes } : {}) });
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
  // known browser messages that are not errors (listed, never counted)
  notes: foldNotes(audit.pages),
};
// colours the browser could not resolve through a canvas are left out of the contrast check, so say so
const unparsed = flat("unparsedColors");
if (unparsed.length) summary.unparsedColors = unparsed;
fs.writeFileSync(`${OUT}/audit.json`, JSON.stringify({ browser: BROWSER, summary, pages: audit.pages }, null, 2));
console.log(JSON.stringify(summary, null, 2));
console.log(`screenshots -> ${OUT}`);
if (failed) { console.error(`shots: ${failed} of ${SIZES.length * 2} runs stopped early (${BROWSER}); see audit.json errors`); process.exitCode = 1; }
