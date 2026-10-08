// perf-table.mjs — markdown tables from measure.mjs / shots.mjs results, for the GitHub step summary
// (.github/workflows/app-browsers.yml). Pure functions (tested in tests/perf-table.test.mjs) plus a small CLI:
//   node tools/perf-table.mjs summary --measure build/measure-webkit.json [--audit build/shots-webkit/audit.json]
//   node tools/perf-table.mjs compare --chromium a.json --webkit b.json [--chromium-audit a.json] [--webkit-audit b.json]
// A missing or unreadable file is reported in the table ("missing results"), never a crash, so the comparison
// still renders when one browser's job failed.
import fs from "node:fs";
import { pathToFileURL } from "node:url";

// WebKit is flagged when it is more than SLOWER_RATIO slower than Chromium AND the gap is at least the unit's noise
// floor (a 0.4 ms -> 0.6 ms keystroke is +50% but means nothing).
export const SLOWER_RATIO = 1.25;
export const NOISE_FLOOR = { ms: 2, MB: 1, count: 1 };

const at = (d, p) => p.split(".").reduce((o, k) => (o == null ? undefined : o[k]), d);
const m = (id, label, unit, budget = null, get = null) => ({ id, label, unit, budget, get: get || ((d) => at(d, id)) });
/** Key metrics, in table order. `id` is the JSON path in measure.json; budgets are the README's (p95 unless named). */
export const METRICS = [
  m("coldStart.interactive.p50", "Cold start → interactive, p50", "ms"),
  m("coldStart.interactive.p95", "Cold start → interactive, p95", "ms", 2000),
  m("coldStart.dbLoad.p50", "DB load (open the pack from Cache Storage), p50", "ms"),
  m("coldStart.dbLoad.p95", "DB load (open the pack from Cache Storage), p95", "ms"),
  m("coldStart.firstPaint.p50", "First contentful paint, p50", "ms"),
  m("firstInstall.ms", "First install (download + index), once", "ms"),
  m("keystroke.worker.p50", "Search in the worker per keystroke, p50", "ms"),
  m("keystroke.worker.p95", "Search in the worker per keystroke, p95", "ms", 16),
  m("keystroke.total.p50", "Keystroke → results painted, p50", "ms", 33),
  m("keystroke.total.p95", "Keystroke → results painted, p95", "ms"),
  m("lookup.resolve.p50", "Typed barcode → resolution, p50", "ms"),
  m("lookup.toSheet.p50", "Typed barcode → sheet painted, p50", "ms"),
  m("lookup.toSheet.p95", "Typed barcode → sheet painted, p95", "ms", 300),
  m("scanTyped.toSheet.p50", "Scanner screen, typed barcode → sheet, p50", "ms"),
  m("scanTyped.toSheet.p95", "Scanner screen, typed barcode → sheet, p95", "ms", 300),
  m("scan.decodeFrame.p50", "Scan: one decoder pass on a camera frame, p50", "ms"),
  m("scan.decodeToPrice.p95", "Scan: decoder hit → sheet painted, p95", "ms", 300),
  m("scan.cameraReadyToSheet.p50", "Scan: camera ready → sheet, p50", "ms", 300),
  m("memory.pageHeapMB", "Memory: main-thread JS heap", "MB"),
  m("memory.workerHeapMB", "Memory: search worker JS heap", "MB"),
  m("memory.workerBuffersMB", "Memory: search worker buffers (the open pack)", "MB"),
  m("longTasksDuringTyping.count", "Long tasks (> 50 ms) while typing", "count", null, (d) => (Array.isArray(d?.longTasksDuringTyping) ? d.longTasksDuringTyping.length : undefined)),
];
// which measure.mjs step produces each top-level key (a failed step means its metrics failed)
const STEP_OF = { firstInstall: "firstInstall + coldStart", coldStart: "firstInstall + coldStart", longTasksDuringTyping: "keystroke" };

/** One metric in one result: { state: ok | nm | failed | not-run | missing, value?, note? } */
export function metricState(d, metric) {
  if (!d) return { state: "missing", note: "missing results" };
  const v = metric.get(d);
  if (typeof v === "number" && Number.isFinite(v)) return { state: "ok", value: v };
  const nm = Object.entries(d.notMeasurable || {}).find(([k]) => metric.id === k || metric.id.startsWith(`${k}.`));
  if (nm) return { state: "nm", note: nm[1] };
  const top = metric.id.split(".")[0];
  const stepName = STEP_OF[top] || top;
  const failure = (d.failures || []).find((f) => f.step === stepName);
  if (failure) return { state: "failed", note: failure.error };
  if (top === "scan" && d.scan === undefined) return { state: "not-run", note: "camera path not run (no --video clip)" };
  if (top === "memory" && d.memory === undefined) return { state: "not-run", note: "memory not measured by this version of measure.mjs" };
  return { state: "failed", note: "no value in the results" };
}

const fmt = (v, unit) => (unit === "ms" ? `${v} ms` : unit === "MB" ? `${v} MB` : String(v));
const cell = (s, unit) => (s.state === "ok" ? fmt(s.value, unit) : s.state === "nm" ? "not measurable" : s.state === "not-run" ? "not run" : s.state === "missing" ? "missing results" : "**failed**");
const esc = (s) => String(s ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
const NAMES = { chromium: "Chromium", webkit: "WebKit" };
const titleCase = (b) => NAMES[b] || (b ? b[0].toUpperCase() + b.slice(1) : "?");
const throttleText = (d) => (d?.cpuThrottle == null ? "none (not available in this browser)" : `×${d.cpuThrottle}`);

/** Compare one metric: { chromium, webkit, delta, flag } with flag = "" or the reason it needs a look. */
export function compareMetric(c, w, metric) {
  const sc = metricState(c, metric), sw = metricState(w, metric);
  const out = { metric, chromium: sc, webkit: sw, delta: "", flag: "" };
  if (sc.state === "ok" && sw.state === "ok") {
    const diff = +(sw.value - sc.value).toFixed(1);
    const pct = sc.value ? ((sw.value - sc.value) / sc.value) * 100 : null;
    out.delta = `${diff > 0 ? "+" : ""}${fmt(diff, metric.unit)}${pct == null ? "" : ` (${pct > 0 ? "+" : ""}${pct.toFixed(0)}%)`}`;
    const floor = NOISE_FLOOR[metric.unit] ?? 0;
    const slower = sc.value > 0 ? sw.value > sc.value * SLOWER_RATIO : sw.value > 0;
    if (slower && diff >= floor) out.flag = `WebKit ${pct == null ? "higher" : `${pct.toFixed(0)}% ${metric.unit === "ms" ? "slower" : "higher"}`}`;
  } else if ((sw.state === "failed" || sw.state === "missing") && (sc.state === "failed" || sc.state === "missing")) out.flag = `failed on both${sw.note ? `: ${sw.note}` : ""}`;
  else if (sw.state === "failed" || sw.state === "missing") out.flag = `failed on WebKit${sw.note ? `: ${sw.note}` : ""}`;
  else if (sc.state === "failed" || sc.state === "missing") out.flag = `failed on Chromium${sc.note ? `: ${sc.note}` : ""}`;
  return out;
}

const AUDIT_ROWS = [
  ["missingNames", "Controls without an accessible name"],
  ["smallTargets", "Tap targets under 44 px"],
  ["smallText", "Text under 13 px"],
  ["lowContrast", "Text below WCAG contrast"],
  ["unparsedColors", "Colours the audit could not resolve"],
  ["errors", "Screens with page errors or a stopped run"],
];
const auditCount = (a, k) => (a?.summary ? (a.summary[k] || []).length : null);

/** Markdown for one browser's results; pass `audit` (null when its file is missing) to add the audit counts. */
export function browserSummary(d, audit, label = null) {
  const name = titleCase(d?.browser || label);
  const lines = [`### ${name}${d?.device ? ` — ${d.device}` : ""}`, ""];
  if (!d) lines.push("No measure results (the measure step failed before writing its JSON; see the job log).", "");
  else {
    lines.push(`CPU throttle: ${throttleText(d)} · ${d.runs} runs per number · ${d.url}`, "");
    lines.push("| metric | measured | budget | |", "|---|---|---|---|");
    for (const metric of METRICS) {
      const s = metricState(d, metric);
      const verdict = s.state !== "ok" || metric.budget == null ? "" : s.value < metric.budget ? "within" : "**over**";
      lines.push(`| ${metric.label} | ${cell(s, metric.unit)} | ${metric.budget == null ? "" : `< ${fmt(metric.budget, metric.unit)}`} | ${verdict} |`);
    }
    lines.push("");
    const nm = Object.entries(d.notMeasurable || {});
    if (nm.length) lines.push("Not measurable here:", ...nm.map(([k, v]) => `- \`${k}\`: ${esc(v)}`), "");
    if (d.failures?.length) lines.push("Failed steps:", ...d.failures.map((f) => `- ${esc(f.step)}: ${esc(f.error)}`), "");
    if (d.pageErrors?.length) lines.push("Page errors:", ...d.pageErrors.map((e) => `- ${esc(e)}`), "");
    if (d.scanTyped?.runs?.[0]?.camera) lines.push(`Camera when the scanner opened: ${esc(d.scanTyped.runs[0].camera)}`, "");
  }
  if (audit !== undefined) lines.push(...auditTable([[name, audit]]));
  return lines.join("\n");
}

function auditTable(cols) {
  const lines = ["Screenshots + accessibility audit (counts across all screens and sizes):", "", `| check | ${cols.map(([n]) => n).join(" | ")} |`, `|---|${cols.map(() => "---").join("|")}|`];
  for (const [k, label] of AUDIT_ROWS) lines.push(`| ${label} | ${cols.map(([, a]) => (a ? auditCount(a, k) : "missing results")).join(" | ")} |`);
  return [...lines, ""];
}

/** Markdown comparison table, Chromium vs WebKit; pass the audits (null when missing) to compare them too. */
export function compareTable(c, w, ca, wa) {
  const lines = ["### Chromium vs WebKit", ""];
  lines.push(`- Chromium: ${c ? `${c.device}, CPU throttle ${throttleText(c)}` : "missing results"}`);
  lines.push(`- WebKit: ${w ? `${w.device}, CPU throttle ${throttleText(w)}` : "missing results"}`);
  if (c && w && (c.cpuThrottle ?? 1) !== (w.cpuThrottle ?? 1)) lines.push(`- **Not like-for-like:** Chromium ran with ×${c.cpuThrottle} CPU throttling and WebKit cannot be throttled, so WebKit looks faster than it is. Run with chromium_cpu = 1 for a fair comparison.`);
  lines.push("", "| metric | Chromium | WebKit | delta | flag |", "|---|---|---|---|---|");
  const rows = METRICS.map((metric) => compareMetric(c, w, metric));
  for (const r of rows) lines.push(`| ${r.metric.label} | ${cell(r.chromium, r.metric.unit)} | ${cell(r.webkit, r.metric.unit)} | ${r.delta} | ${r.flag ? `**${esc(r.flag)}**` : ""} |`);
  const flagged = rows.filter((r) => r.flag);
  lines.push("", flagged.length ? `**${flagged.length} metric${flagged.length > 1 ? "s" : ""} flagged.**` : "No metric flagged.");
  lines.push(`Flag = WebKit more than ${Math.round((SLOWER_RATIO - 1) * 100)}% slower (or higher memory) than Chromium and by at least ${NOISE_FLOOR.ms} ms / ${NOISE_FLOOR.MB} MB, or a metric that failed. "not measurable" = the browser has no way to measure it in CI (reason below), not a failure.`, "");
  const nm = Object.entries(w?.notMeasurable || {});
  if (nm.length) lines.push("Not measurable on WebKit:", ...nm.map(([k, v]) => `- \`${k}\`: ${esc(v)}`), "");
  for (const [n, d] of [["Chromium", c], ["WebKit", w]]) {
    if (d?.failures?.length) lines.push(`Failed steps (${n}):`, ...d.failures.map((f) => `- ${esc(f.step)}: ${esc(f.error)}`), "");
    if (d?.pageErrors?.length) lines.push(`Page errors (${n}):`, ...d.pageErrors.map((e) => `- ${esc(e)}`), "");
  }
  if (ca !== undefined || wa !== undefined) {
    lines.push(...auditTable([["Chromium", ca], ["WebKit", wa]]));
    const worse = AUDIT_ROWS.filter(([k]) => ca && wa && auditCount(wa, k) > auditCount(ca, k)).map(([, l]) => l);
    if (worse.length) lines.push(`**Audit flag:** WebKit has more findings than Chromium in: ${worse.join("; ")}.`, "");
  }
  return lines.join("\n");
}

export function readJson(file) {
  if (!file) return null;
  try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return null; }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [cmd, ...rest] = process.argv.slice(2);
  const opt = Object.fromEntries(rest.map((a, i, arr) => (a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : ""] : [])).filter((x) => x.length));
  if (cmd === "summary") {
    console.log(browserSummary(readJson(opt.measure), "audit" in opt ? readJson(opt.audit) : undefined, opt.browser));
  } else if (cmd === "compare") {
    const hasAudit = "chromium-audit" in opt || "webkit-audit" in opt;
    console.log(compareTable(readJson(opt.chromium), readJson(opt.webkit), hasAudit ? readJson(opt["chromium-audit"]) : undefined, hasAudit ? readJson(opt["webkit-audit"]) : undefined));
  } else {
    console.error("usage: perf-table.mjs summary --measure m.json [--audit a.json] [--browser name]\n       perf-table.mjs compare --chromium a.json --webkit b.json [--chromium-audit x.json] [--webkit-audit y.json]");
    process.exit(2);
  }
}
