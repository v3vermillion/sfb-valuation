// measure.mjs — real-browser performance numbers for the judges, not estimates.
// Chromium (Playwright) at Pixel-7 size with 4x CPU throttling (a mid-range phone), fake camera fed with a UPC-A clip.
//   node tools/measure.mjs [--url http://127.0.0.1:8787/] [--cpu 4] [--video path.y4m] [--runs 5] [--json out.json]
import { chromium, devices } from "playwright";
import fs from "node:fs";

const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => (a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : [])).filter((x) => x.length));
const URL_ = args.url || "http://127.0.0.1:8787/";
const CPU = Number(args.cpu || 4);
const RUNS = Number(args.runs || 5);
const VIDEO = args.video || null;
const QUERIES = ["peanut butter", "gv corn 15 oz", "diapers size 4", "toothpaste", "cheerios 18", "tide pods", "2% milk gallon", "pb"];
const pct = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
const stats = (a) => ({ n: a.length, p50: +pct(a, 0.5).toFixed(1), p95: +pct(a, 0.95).toFixed(1), max: +Math.max(...a).toFixed(1) });

const launchArgs = ["--no-sandbox", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"];
if (VIDEO) launchArgs.push(`--use-file-for-fake-video-capture=${VIDEO}`);
const browser = await chromium.launch({ args: launchArgs });
const device = devices["Pixel 7"];
const out = { url: URL_, cpuThrottle: CPU, device: "Pixel 7 viewport (412x915 @2.625)", runs: RUNS };

async function newPage(ctx) {
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: CPU });
  return { page, cdp };
}

// ---- 1. first install (download + index) and cold starts with the DB already on the phone
{
  const ctx = await browser.newContext({ ...device, permissions: ["camera"] });
  const { page } = await newPage(ctx);
  const t0 = Date.now();
  await page.goto(URL_, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("html[data-ready='1']", { timeout: 180000 });
  const boot = await page.evaluate(() => window.__sfb.perf.boot);
  out.firstInstall = { ms: boot.interactiveMs, wall: Date.now() - t0, note: "download 33 MB from local server + index; happens once" };
  await page.waitForTimeout(500);
  const colds = [];
  for (let i = 0; i < RUNS; i++) {
    await page.goto("about:blank");
    await page.goto(URL_, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("html[data-ready='1']", { timeout: 60000 });
    const b = await page.evaluate(() => ({ boot: window.__sfb.perf.boot, nav: performance.getEntriesByType("navigation")[0]?.toJSON?.() }));
    colds.push({ interactive: b.boot.interactiveMs, dbLoad: b.boot.wallMs, script: b.boot.scriptMs, fcp: Math.round(await page.evaluate(() => performance.getEntriesByName("first-contentful-paint")[0]?.startTime || 0)) });
  }
  out.coldStart = { interactive: stats(colds.map((c) => c.interactive)), dbLoad: stats(colds.map((c) => c.dbLoad)), firstPaint: stats(colds.map((c) => c.fcp)), runs: colds, note: "reload with DB cached (service worker + Cache Storage); interactive = search answers" };

  // ---- 2. per-keystroke: type each query one character at a time; measure input->rendered (rAF after DOM swap)
  const ks = [];
  for (const q of QUERIES) {
    await page.fill("#q", "");
    await page.evaluate(() => (window.__sfb.perf.keystrokes.length = 0));
    for (const ch of q) { await page.type("#q", ch, { delay: 0 }); await page.waitForTimeout(90); }
    await page.waitForTimeout(250);
    const k = await page.evaluate(() => window.__sfb.perf.keystrokes.slice());
    ks.push(...k.map((x) => ({ ...x, query: q })));
  }
  out.keystroke = { total: stats(ks.map((k) => k.totalMs)), worker: stats(ks.map((k) => k.workerMs)), samples: ks.length, note: "totalMs = input event -> results painted (incl. worker round-trip + DOM); frame budget 16.7 ms", worst: ks.slice().sort((a, b) => b.totalMs - a.totalMs).slice(0, 5) };
  // frame timing while typing: count long tasks
  const long = await page.evaluate(async () => new Promise((res) => {
    const obs = new PerformanceObserver((l) => {}); let longs = [];
    const po = new PerformanceObserver((list) => longs.push(...list.getEntries().map((e) => Math.round(e.duration))));
    po.observe({ type: "longtask", buffered: true });
    setTimeout(() => res(longs), 100);
  }));
  out.longTasksDuringTyping = long;

  // ---- 3. search quality spot checks (top result for a few queries)
  out.topResults = {};
  for (const q of ["peanut butter", "gv corn", "diapers size 4", "cheerios", "2% milk", "tide pods", "pb", "chese"]) {
    await page.fill("#q", q); await page.waitForTimeout(300);
    out.topResults[q] = await page.evaluate(() => { const r = window.__sfb.state.last; return r ? { total: r.total, relaxed: r.relaxed, fuzzy: r.fuzzy, ms: r.ms, top: r.items.slice(0, 3).map((i) => `${i.brand ? i.brand + " " : ""}${i.name} — $${(i.priceCents / 100).toFixed(2)}`) } : null; });
  }

  // ---- 4. typed-barcode -> price (resolution + sheet render), no camera involved
  const lookups = [];
  for (const code of ["078742054261", "4011", "201234928751", "012345678905", "078742054261"]) {
    await page.fill("#q", "");
    const t = await page.evaluate(async (c) => { const t0 = performance.now(); const r = await window.__sfb.resolveCode(c); const t1 = performance.now(); window.__sfb.openCode(c); await new Promise((r2) => requestAnimationFrame(() => requestAnimationFrame(r2))); return { code: c, kind: r?.kind, resolveMs: +(t1 - t0).toFixed(1), toSheetMs: +(performance.now() - t0).toFixed(1) }; }, code);
    lookups.push(t);
    await page.evaluate(() => document.getElementById("sheet").close());
    await page.waitForTimeout(150);
  }
  out.lookup = { resolve: stats(lookups.map((l) => l.resolveMs)), toSheet: stats(lookups.map((l) => l.toSheetMs)), runs: lookups };
  await ctx.close();
}

// ---- 5. scan -> price with the fake camera (full path: camera frame -> decoder -> lookup -> sheet painted)
if (VIDEO) {
  const scans = [];
  for (let i = 0; i < RUNS; i++) {
    const ctx = await browser.newContext({ ...device, permissions: ["camera"] });
    const { page } = await newPage(ctx);
    await page.goto(URL_, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("html[data-ready='1']", { timeout: 60000 });
    await page.click("#scanBtn");
    await page.waitForFunction(() => document.getElementById("video").readyState >= 2, null, { timeout: 15000 });
    const tCam = await page.evaluate(() => performance.now());
    await page.waitForSelector("#sheet[open]", { timeout: 20000 });
    await page.waitForFunction(() => window.__sfb.perf.scans.length > 0);
    const s = await page.evaluate(() => ({ ...window.__sfb.perf.scans[0], engine: window.__sfb.state.engine, title: document.getElementById("sheetTitle")?.textContent, kind: document.querySelector("#sheet .kind")?.textContent }));
    const tSheet = await page.evaluate(() => performance.now());
    scans.push({ ...s, cameraReadyToSheetMs: +(tSheet - tCam).toFixed(0) });
    if (i === 0) await page.screenshot({ path: new URL("../build/scan-sheet.png", import.meta.url).pathname }).catch(() => {});
    await ctx.close();
  }
  out.scan = { decodeFrame: stats(scans.map((s) => s.decodeMs)), decodeToPrice: stats(scans.map((s) => s.toPriceMs)), cameraReadyToSheet: stats(scans.map((s) => s.cameraReadyToSheetMs)), runs: scans, note: "decodeMs = one decoder pass on a frame; toPriceMs = decoder hit -> lookup -> sheet painted; cameraReadyToSheet includes waiting for 2 agreeing reads at ~10 fps" };
}

await browser.close();
console.log(JSON.stringify(out, null, 2));
if (args.json) fs.writeFileSync(args.json, JSON.stringify(out, null, 2));
