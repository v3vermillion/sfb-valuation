import { test } from "node:test";
import assert from "node:assert/strict";
import { METRICS, SLOWER_RATIO, NOISE_FLOOR, metricState, compareMetric, compareTable, browserSummary } from "../tools/perf-table.mjs";

const s = (p50, p95 = p50) => ({ n: 5, p50, p95, max: p95 });
const metric = (id) => METRICS.find((m) => m.id === id);
// the shape measure.mjs writes (only the keys the tables read)
const chromium = {
  url: "http://127.0.0.1:8787/", cpuThrottle: 1, device: "Pixel 7 viewport (412x915 @2.625)", runs: 5, browser: "chromium",
  firstInstall: { ms: 1800 }, coldStart: { interactive: s(600, 700), dbLoad: s(450, 580), firstPaint: s(90) },
  keystroke: { worker: s(4, 8.4), total: s(24.7, 34.2) }, longTasksDuringTyping: [],
  lookup: { resolve: s(4, 9.1), toSheet: s(46.2, 60.1) }, scanTyped: { toSheet: s(80, 95), runs: [{ camera: "live (zxing)" }] },
  memory: { pageHeapMB: 3.1, workerHeapMB: 2, workerBuffersMB: 95 },
  scan: { decodeFrame: s(19, 23), decodeToPrice: s(71.3, 78), cameraReadyToSheet: s(297, 378) },
};
const webkit = {
  url: "http://127.0.0.1:8787/", cpuThrottle: null, device: "iPhone 14 viewport (390x844 @3)", runs: 5, browser: "webkit",
  firstInstall: { ms: 2100 }, coldStart: { interactive: s(700, 800), dbLoad: s(470, 590), firstPaint: null },
  keystroke: { worker: s(4.5, 8.9), total: s(26, 36) }, longTasksDuringTyping: null,
  lookup: { resolve: s(5, 10), toSheet: s(48, 62) }, scanTyped: { toSheet: s(85, 99), runs: [{ camera: "refused: No camera was found" }] },
  memory: null, scan: null,
  notMeasurable: {
    cpuThrottle: "no CPU throttling on WebKit", memory: "no heap API on WebKit", scan: "not measurable on WebKit in CI: no fake camera",
    longTasksDuringTyping: "no Long Tasks API", "coldStart.firstPaint": "no first-contentful-paint entry",
  },
};

test("every metric id reads a number from a complete Chromium result", () => {
  for (const m of METRICS) assert.equal(metricState(chromium, m).state, "ok", m.id);
});

test("metrics WebKit cannot measure are 'nm' with the reason, not failures", () => {
  for (const id of ["scan.decodeFrame.p50", "memory.pageHeapMB", "longTasksDuringTyping.count", "coldStart.firstPaint.p50"]) {
    const st = metricState(webkit, metric(id));
    assert.equal(st.state, "nm", id);
    assert.ok(st.note.length > 0);
  }
  assert.equal(metricState(webkit, metric("keystroke.worker.p95")).state, "ok");
});

test("a failed measure step marks its metrics failed; an absent camera clip is 'not run'", () => {
  const d = { ...chromium, lookup: undefined, coldStart: undefined, failures: [{ step: "lookup", error: "Timeout" }, { step: "firstInstall + coldStart", error: "never ready" }] };
  assert.deepEqual(metricState(d, metric("lookup.toSheet.p95")), { state: "failed", note: "Timeout" });
  assert.equal(metricState(d, metric("coldStart.interactive.p50")).state, "failed");
  assert.equal(metricState({ ...chromium, scan: undefined }, metric("scan.decodeToPrice.p95")).state, "not-run");
  assert.equal(metricState(null, metric("lookup.toSheet.p95")).state, "missing");
  // a value that is simply absent, with no reason, is a failure (never silently blank)
  assert.equal(metricState({ ...chromium, keystroke: {} }, metric("keystroke.worker.p50")).state, "failed");
});

test(`WebKit is flagged above ${Math.round((SLOWER_RATIO - 1) * 100)}% slower, and only beyond the noise floor`, () => {
  const m = metric("coldStart.interactive.p50");
  const at = (c, w) => compareMetric({ ...chromium, coldStart: { ...chromium.coldStart, interactive: s(c) } }, { ...webkit, coldStart: { ...webkit.coldStart, interactive: s(w) } }, m);
  assert.equal(at(600, 750).flag, "");                    // exactly +25%: not flagged
  assert.match(at(600, 751).flag, /^WebKit 25% slower$/);  // just over
  assert.match(at(600, 900).flag, /50% slower/);
  assert.equal(at(600, 500).flag, "");                    // faster is fine
  assert.equal(at(600, 900).delta, "+300 ms (+50%)");
  assert.equal(at(1, 2).flag, "", `+100% but under the ${NOISE_FLOOR.ms} ms floor`);
  assert.match(at(1, 3.5).flag, /slower/);
});

test("a metric that failed on either side is flagged; not measurable is not", () => {
  const failedW = { ...webkit, lookup: undefined, failures: [{ step: "lookup", error: "sheet never opened" }] };
  assert.match(compareMetric(chromium, failedW, metric("lookup.toSheet.p95")).flag, /^failed on WebKit: sheet never opened/);
  assert.match(compareMetric(null, webkit, metric("lookup.toSheet.p95")).flag, /^failed on Chromium/);
  assert.match(compareMetric(chromium, null, metric("lookup.toSheet.p95")).flag, /^failed on WebKit/);
  assert.match(compareMetric(null, null, metric("lookup.toSheet.p95")).flag, /^failed on both/);
  assert.equal(compareMetric(chromium, webkit, metric("scan.decodeToPrice.p95")).flag, "");
  assert.equal(compareMetric(chromium, webkit, metric("memory.workerBuffersMB")).flag, "");
});

test("comparison table: one row per metric, throttle mismatch called out, audits compared", () => {
  const md = compareTable(chromium, webkit, { summary: { smallTargets: [1, 2], errors: [] } }, { summary: { smallTargets: [1, 2, 3], errors: [] } });
  for (const m of METRICS) assert.ok(md.includes(`| ${m.label} |`), m.label);
  assert.ok(!md.includes("Not like-for-like"));
  assert.ok(md.includes("Not measurable on WebKit:"));
  assert.match(md, /Audit flag:.*Tap targets under 44 px/);
  assert.match(compareTable({ ...chromium, cpuThrottle: 4 }, webkit), /Not like-for-like/);
  // one side missing still renders a full table
  const half = compareTable(chromium, null, undefined, undefined);
  assert.ok(half.includes("WebKit: missing results"));
  assert.ok(!half.includes("Screenshots + accessibility audit"));
});

test("per-browser summary marks budgets and lists what is not measurable", () => {
  const md = browserSummary(webkit, { summary: { missingNames: [], smallTargets: [{}], smallText: [], lowContrast: [], errors: [] } });
  assert.match(md, /^### WebKit — iPhone 14/);
  assert.match(md, /\| Cold start → interactive, p95 \| 800 ms \| < 2000 ms \| within \|/);
  assert.match(md, /\| Scan: decoder hit → sheet painted, p95 \| not measurable \|/);
  assert.match(md, /CPU throttle: none/);
  assert.match(md, /Camera when the scanner opened: refused/);
  assert.match(md, /\| Tap targets under 44 px \| 1 \|/);
  assert.match(browserSummary({ ...chromium, keystroke: { worker: s(4, 20), total: s(24, 30) } }), /per keystroke, p95 \| 20 ms \| < 16 ms \| \*\*over\*\*/);
  assert.match(browserSummary(null, undefined, "webkit"), /No measure results/);
});

test("browser notes are listed with their reason and never counted as page errors", () => {
  const note = { message: 'Viewport argument key "interactive-widget" not recognized and ignored.', why: "WebKit does not implement it", pages: ["webkit-light-390x844", "webkit-dark-390x844"] };
  const ca = { summary: { errors: [] } }, wa = { summary: { errors: [], notes: [note] } };
  const md = compareTable(chromium, webkit, ca, wa);
  assert.match(md, /\| Screens with page errors or a stopped run \| 0 \| 0 \|/);
  assert.ok(!md.includes("Audit flag"), "a note is not a finding");
  assert.match(md, /Browser notes .*not page errors/);
  assert.match(md, /- WebKit, 2 screens: `Viewport argument key "interactive-widget" not recognized and ignored\.` — WebKit does not implement it/);
  assert.ok(!compareTable(chromium, webkit, ca, { summary: { errors: [] } }).includes("Browser notes"));
  assert.match(browserSummary(webkit, wa), /- WebKit, 2 screens: `Viewport argument key/);
});

test("the two-frame 'presented' mark and the first-install split are diagnosis rows, never flagged", () => {
  const c = { ...chromium, lookup: { ...chromium.lookup, presented: s(40, 42), withoutBackdropFilter: { presented: s(38, 40) } }, firstInstall: { ms: 686, downloadMs: 300, dbLoadMs: 350, workerMs: 320 } };
  const w = { ...webkit, lookup: { ...webkit.lookup, presented: s(146, 1169), withoutBackdropFilter: { presented: s(40, 45) } }, scanTyped: { ...webkit.scanTyped, presented: s(254, 2349) }, firstInstall: { ms: 1795, downloadMs: 1200 } };
  const md = compareTable(c, w);
  assert.match(md, /\| Typed barcode → sheet presented \(two frames\), p50 \/ p95 \| 40 \/ 42 ms \| 146 \/ 1169 ms \|/);
  assert.match(md, /\| Typed barcode → sheet presented, every backdrop-filter switched off \| 38 \/ 40 ms \| 40 \/ 45 ms \|/);
  assert.match(md, /\| Scanner screen, typed barcode → sheet presented \(two frames\), p50 \/ p95 \| — \| 254 \/ 2349 ms \|/);
  assert.match(md, /\| First install: download the pack into Cache Storage \| 300 ms \| 1200 ms \|/);
  assert.match(md, /\| First install: of which the worker \(read, inflate, index\) \| 320 ms \| — \|/);
  // the flagged rows are still only the METRICS ones
  assert.equal((md.match(/\*\*WebKit \d+% slower\*\*/g) || []).length, METRICS.filter((m) => compareMetric(c, w, m).flag.startsWith("WebKit")).length);
  assert.ok(!compareTable(chromium, webkit).includes("Diagnosis"), "no diagnosis table when no run recorded one");
});
