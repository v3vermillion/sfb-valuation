// measure.mjs — real-browser performance numbers for the judges, not estimates.
// Chromium (Playwright) at Pixel-7 size with 4x CPU throttling (a mid-range phone), fake camera fed with a UPC-A clip.
// WebKit (--browser webkit, the engine of every iPhone browser) at iPhone 14 size: no CPU throttling and no fake camera
// exist there (both are Chromium-only), so those numbers are host-speed and the camera path is reported as not measurable;
// the scanner screen's typed-barcode path (scanTyped) is measured in both browsers instead.
//   node tools/measure.mjs [--browser chromium|webkit] [--url http://127.0.0.1:8787/] [--cpu 4] [--video path.y4m] [--runs 5] [--json out.json]
import { chromium, webkit, devices } from "playwright";
import fs from "node:fs";

const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => (a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : [])).filter((x) => x.length));
const BROWSER = String(args.browser || "chromium").toLowerCase();
if (BROWSER !== "chromium" && BROWSER !== "webkit") { console.error(`measure: --browser must be chromium or webkit (got ${args.browser})`); process.exit(2); }
const IS_CHROMIUM = BROWSER === "chromium";
const URL_ = args.url || "http://127.0.0.1:8787/";
const CPU = Number(args.cpu || 4);
const RUNS = Number(args.runs || 5);
const VIDEO = IS_CHROMIUM ? args.video || null : null;
const QUERIES = ["peanut butter", "gv corn 15 oz", "diapers size 4", "toothpaste", "cheerios 18", "tide pods", "2% milk gallon", "pb"];
const pct = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
const stats = (a) => (a.length ? { n: a.length, p50: +pct(a, 0.5).toFixed(1), p95: +pct(a, 0.95).toFixed(1), max: +Math.max(...a).toFixed(1) } : null);

// Chromium-only switches: fake camera (and the file that feeds it) and --no-sandbox never reach WebKit.
const launchArgs = ["--no-sandbox", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"];
if (VIDEO) launchArgs.push(`--use-file-for-fake-video-capture=${VIDEO}`);
const browser = IS_CHROMIUM ? await chromium.launch({ args: launchArgs }) : await webkit.launch();
const DEVICE_NAME = IS_CHROMIUM ? "Pixel 7" : "iPhone 14";
const device = devices[DEVICE_NAME];
if (!device) throw new Error(`Playwright has no "${DEVICE_NAME}" device profile`);
const out = IS_CHROMIUM
  ? { url: URL_, cpuThrottle: CPU, device: "Pixel 7 viewport (412x915 @2.625)", runs: RUNS, browser: BROWSER }
  : { url: URL_, cpuThrottle: null, device: `${DEVICE_NAME} viewport (${device.screen.width}x${device.screen.height} @${device.deviceScaleFactor})`, runs: RUNS, browser: BROWSER };
// what this browser cannot measure, and why (absent for Chromium unless something there is unavailable too)
const notMeasurable = {};
if (!IS_CHROMIUM) {
  notMeasurable.cpuThrottle = "no CPU throttling on WebKit (it is a Chrome DevTools Protocol feature): WebKit numbers run at host speed";
  if (args.video) console.error("measure: --video is ignored on WebKit (Playwright's WebKit has no fake camera)");
  if (args.cpu) console.error("measure: --cpu is ignored on WebKit (CPU throttling is Chromium-only)");
}
// A step that throws is recorded (and the run exits non-zero) instead of losing every number measured so far.
const failures = [];
async function step(name, fn) {
  try { await fn(); } catch (err) {
    const msg = String(err?.message || err).split("\n")[0];
    failures.push({ step: name, error: msg });
    console.error(`measure: ${name} failed: ${msg}`);
  }
}
const pageErrors = [];
// camera permission: Chromium only (Playwright's WebKit rejects "camera" as an unknown permission)
const contextOptions = () => (IS_CHROMIUM ? { ...device, permissions: ["camera"] } : { ...device });

async function newPage(ctx) {
  const page = await ctx.newPage();
  page.on("pageerror", (e) => pageErrors.push(String(e.message).split("\n")[0]));
  if (!IS_CHROMIUM) return { page, cdp: null };
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: CPU });
  return { page, cdp };
}

/** JS heap of the page and of its workers after a GC, through CDP (Chromium only). The pack lives in the db worker's
 *  ArrayBuffers, which V8 counts as backing storage rather than heap, so that is reported separately. */
async function chromiumMemory(cdp) {
  const attached = [];
  const pending = new Map();
  let id = 0;
  cdp.on("Target.attachedToTarget", (e) => attached.push(e));
  cdp.on("Target.receivedMessageFromTarget", (e) => { const m = JSON.parse(e.message); pending.get(`${e.sessionId}:${m.id}`)?.(m); });
  const ask = (sessionId, method) => new Promise((resolve, reject) => {
    const key = `${sessionId}:${++id}`;
    const timer = setTimeout(() => { pending.delete(key); reject(new Error(`${method} timed out`)); }, 10000);
    pending.set(key, (m) => { clearTimeout(timer); pending.delete(key); m.error ? reject(new Error(m.error.message)) : resolve(m.result); });
    cdp.send("Target.sendMessageToTarget", { sessionId, message: JSON.stringify({ id, method }) }).catch(reject);
  });
  await cdp.send("Target.setAutoAttach", { autoAttach: true, waitForDebuggerOnStart: false, flatten: false });
  await new Promise((r) => setTimeout(r, 300));
  const MB = (b) => +(b / 1048576).toFixed(1);
  try {
    await cdp.send("HeapProfiler.collectGarbage");
    const pageHeap = await cdp.send("Runtime.getHeapUsage");
    const mem = { pageHeapMB: MB(pageHeap.usedSize), workerHeapMB: null, workerBuffersMB: null, workers: [] };
    for (const t of attached.filter((a) => a.targetInfo.type === "worker")) {
      await ask(t.sessionId, "HeapProfiler.collectGarbage").catch(() => {});
      const h = await ask(t.sessionId, "Runtime.getHeapUsage");
      mem.workers.push({ url: t.targetInfo.url.replace(/^.*\//, ""), heapMB: MB(h.usedSize), buffersMB: h.backingStorageSize != null ? MB(h.backingStorageSize) : null });
    }
    if (mem.workers.length) {
      mem.workerHeapMB = +mem.workers.reduce((s, w) => s + w.heapMB, 0).toFixed(1);
      if (mem.workers.every((w) => w.buffersMB != null)) mem.workerBuffersMB = +mem.workers.reduce((s, w) => s + w.buffersMB, 0).toFixed(1);
    }
    mem.note = "after a forced GC, once the searches and lookups above have run; pageHeapMB = main thread JS heap, workerHeapMB = dedicated workers' JS heap (the search worker), workerBuffersMB = their ArrayBuffers (the opened pack)";
    return mem;
  } finally {
    await cdp.send("Target.setAutoAttach", { autoAttach: false, waitForDebuggerOnStart: false, flatten: false }).catch(() => {});
    for (const t of attached) await cdp.send("Target.detachFromTarget", { sessionId: t.sessionId }).catch(() => {});
  }
}

// ---- 1. first install (download + index) and cold starts with the DB already on the phone
{
  const ctx = await browser.newContext(contextOptions());
  const { page, cdp } = await newPage(ctx);
  await step("firstInstall + coldStart", async () => {
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
    // no paint-timing entry at all (an engine without first-contentful-paint) is "not measured", never 0 ms
    const fcpOk = colds.some((c) => c.fcp);
    if (!fcpOk) notMeasurable["coldStart.firstPaint"] = `${BROWSER} reported no first-contentful-paint entry`;
    out.coldStart = { interactive: stats(colds.map((c) => c.interactive)), dbLoad: stats(colds.map((c) => c.dbLoad)), firstPaint: fcpOk ? stats(colds.map((c) => c.fcp)) : null, runs: colds, note: "reload with DB cached (service worker + Cache Storage); interactive = search answers" };
  });

  // ---- 2. per-keystroke: type each query one character at a time; measure input->rendered (rAF after DOM swap)
  await step("keystroke", async () => {
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
    // frame timing while typing: count long tasks (the Long Tasks API exists in Chromium only: null elsewhere, not [])
    const long = await page.evaluate(async () => new Promise((res) => {
      if (!(PerformanceObserver.supportedEntryTypes || []).includes("longtask")) { res(null); return; }
      const obs = new PerformanceObserver((l) => {}); let longs = [];
      const po = new PerformanceObserver((list) => longs.push(...list.getEntries().map((e) => Math.round(e.duration))));
      po.observe({ type: "longtask", buffered: true });
      setTimeout(() => res(longs), 100);
    }));
    if (long === null) notMeasurable.longTasksDuringTyping = `${BROWSER} has no Long Tasks API (PerformanceObserver "longtask")`;
    out.longTasksDuringTyping = long;
  });

  // ---- 3. search quality spot checks (top result for a few queries)
  await step("topResults", async () => {
    out.topResults = {};
    for (const q of ["peanut butter", "gv corn", "diapers size 4", "cheerios", "2% milk", "tide pods", "pb", "chese"]) {
      await page.fill("#q", q); await page.waitForTimeout(300);
      out.topResults[q] = await page.evaluate(() => { const r = window.__sfb.state.last; return r ? { total: r.total, relaxed: r.relaxed, fuzzy: r.fuzzy, ms: r.ms, top: r.items.slice(0, 3).map((i) => `${i.brand ? i.brand + " " : ""}${i.name} — $${(i.priceCents / 100).toFixed(2)}`) } : null; });
    }
  });

  // ---- 4. typed-barcode -> price (resolution + sheet render), no camera involved
  await step("lookup", async () => {
    const lookups = [];
    for (const code of ["078742054261", "4011", "201234928751", "012345678905", "078742054261"]) {
      await page.fill("#q", "");
      const t = await page.evaluate(async (c) => { const t0 = performance.now(); const r = await window.__sfb.resolveCode(c); const t1 = performance.now(); window.__sfb.openCode(c); await new Promise((r2) => requestAnimationFrame(() => requestAnimationFrame(r2))); return { code: c, kind: r?.kind, resolveMs: +(t1 - t0).toFixed(1), toSheetMs: +(performance.now() - t0).toFixed(1) }; }, code);
      lookups.push(t);
      await page.evaluate(() => document.getElementById("sheet").close());
      await page.waitForTimeout(150);
    }
    out.lookup = { resolve: stats(lookups.map((l) => l.resolveMs)), toSheet: stats(lookups.map((l) => l.toSheetMs)), runs: lookups };
  });

  // ---- 4b. memory once the pack is open and has answered searches (heap APIs are Chromium-only: CDP)
  if (IS_CHROMIUM) await step("memory", async () => { out.memory = await chromiumMemory(cdp); });
  else { out.memory = null; notMeasurable.memory = "WebKit exposes no heap measurement to pages or to Playwright (performance.memory and CDP heap usage are Chromium-only)"; }
  await ctx.close();
}

// ---- 4c. the scanner screen's "Type the barcode instead" path: open the scanner, type the digits, submit -> sheet painted.
// Measured in both browsers (on WebKit it stands in for the camera path); also records what the camera did on open.
await step("scanTyped", async () => {
  const ctx = await browser.newContext(contextOptions());
  const { page } = await newPage(ctx);
  const runs = [];
  try {
    for (let i = 0; i < RUNS; i++) {
      await page.goto(URL_, { waitUntil: "domcontentloaded" });
      await page.waitForSelector("html[data-ready='1']", { timeout: 60000 });
      await page.click("#scanBtn");
      await page.waitForSelector("#scanner:not([hidden])", { timeout: 10000 });
      // choose typing at once (as a volunteer would), so a fake camera that reads a barcode cannot open the sheet first.
      // In-page and atomic: a camera that is refused at once swaps the button for the form itself, and a check-then-click
      // from Playwright would race that swap.
      await page.evaluate(() => { if (document.getElementById("scanTypeForm").hidden) document.getElementById("scanTypeBtn").click(); });
      // then wait for the camera to settle: live (Chromium's fake camera) or refused (shows the typed form again)
      const camera = await page.waitForFunction(() => {
        const v = document.getElementById("video"); const denied = document.querySelector("#scanner .scan-denied");
        return denied ? `refused: ${denied.textContent.trim()}` : v && v.readyState >= 2 ? `live (${window.__sfb.state.engine || "engine starting"})` : false;
      }, null, { timeout: 8000 }).then((h) => h.jsonValue()).catch(() => "no answer from the camera within 8 s");
      await page.waitForSelector("#scanTypeForm:not([hidden])", { timeout: 5000 });
      const r = await page.evaluate(async (c) => {
        const input = document.getElementById("scanTypeInput"), form = document.getElementById("scanTypeForm"), sheet = document.getElementById("sheet");
        if (sheet.open) throw new Error("the sheet was already open before the digits were typed (the camera read a barcode first)");
        input.value = c;
        const t0 = performance.now();
        const opened = new Promise((resolve, reject) => {
          const timer = setTimeout(() => { mo.disconnect(); reject(new Error("the sheet did not open within 10 s")); }, 10000);
          const mo = new MutationObserver(() => { if (sheet.open) { clearTimeout(timer); mo.disconnect(); resolve(); } });
          mo.observe(sheet, { attributes: true, attributeFilter: ["open"] });
        });
        form.requestSubmit();
        await opened;
        await new Promise((r2) => requestAnimationFrame(() => requestAnimationFrame(r2)));
        return { code: c, toSheetMs: +(performance.now() - t0).toFixed(1), kind: document.querySelector("#sheet .kind")?.textContent?.trim(), title: document.getElementById("sheetTitle")?.textContent?.trim() };
      }, "078742054261");
      runs.push({ ...r, camera });
    }
  } finally { await ctx.close(); }
  out.scanTyped = { toSheet: stats(runs.map((r) => r.toSheetMs)), runs, note: "scanner open -> 'Type the barcode instead' -> digits submitted -> sheet painted (in-page clock, two frames after the sheet opens); camera = what the camera did when the scanner opened" };
});

// ---- 5. scan -> price with the fake camera (full path: camera frame -> decoder -> lookup -> sheet painted)
if (VIDEO) {
  await step("scan", async () => {
    const scans = [];
    for (let i = 0; i < RUNS; i++) {
      const ctx = await browser.newContext(contextOptions());
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
  });
} else if (!IS_CHROMIUM) {
  out.scan = null;
  notMeasurable.scan = "not measurable on WebKit in CI: Playwright's WebKit has no fake camera (Chromium's --use-fake-device-for-media-stream / --use-file-for-fake-video-capture) and cannot grant the camera permission; scanTyped measures the scanner screen's typed path instead";
}

await browser.close();
if (Object.keys(notMeasurable).length) out.notMeasurable = notMeasurable;
if (pageErrors.length) out.pageErrors = [...new Set(pageErrors)];
if (failures.length) out.failures = failures;
console.log(JSON.stringify(out, null, 2));
if (args.json) fs.writeFileSync(args.json, JSON.stringify(out, null, 2));
if (failures.length) process.exitCode = 1;
