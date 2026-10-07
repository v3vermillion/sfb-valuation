// perf-report.mjs — turn build/measure.json into docs/perf/README.md (+ a dated copy of the raw JSON).
//   node tools/perf-report.mjs [build/measure.json] [../docs/perf]
import fs from "node:fs";
import path from "node:path";

const src = process.argv[2] || "build/measure.json";
const outDir = path.resolve(process.argv[3] || "../docs/perf");
const d = JSON.parse(fs.readFileSync(src, "utf8"));
fs.mkdirSync(outDir, { recursive: true });
const stamp = new Date().toISOString().slice(0, 10);
fs.writeFileSync(path.join(outDir, `measure-${stamp}.json`), JSON.stringify(d, null, 2));

const f = (s) => (s ? `${s.p50} / ${s.p95} ms` : "—");
const rows = [
  ["Cold start → interactive (DB already on the phone)", "< 2000 ms", f(d.coldStart?.interactive), d.coldStart?.interactive?.p95 < 2000],
  ["  of which: open the pack from Cache Storage", "", f(d.coldStart?.dbLoad), true],
  ["  first contentful paint", "", f(d.coldStart?.firstPaint), true],
  ["First install (download 32 MB from local server + index), once", "one-time", `${d.firstInstall?.ms} ms`, true],
  ["Search in the worker, per keystroke", "< 16 ms", f(d.keystroke?.worker), d.keystroke?.worker?.p95 < 16],
  ["Keystroke → results painted (worker round trip + DOM + next frame)", "≈ 1 frame", f(d.keystroke?.total), d.keystroke?.total?.p50 < 33],
  ["Typed barcode → resolution", "", f(d.lookup?.resolve), true],
  ["Typed barcode → sheet painted", "< 300 ms", f(d.lookup?.toSheet), d.lookup?.toSheet?.p95 < 300],
  ["Scan: one decoder pass on a camera frame (zxing wasm)", "", f(d.scan?.decodeFrame), true],
  ["Scan: decoder hit → lookup → sheet painted", "< 300 ms", f(d.scan?.decodeToPrice), d.scan?.decodeToPrice?.p95 < 300],
  ["Scan: camera ready → sheet (incl. two agreeing reads at ~14 fps)", "< 300 ms (p50)", f(d.scan?.cameraReadyToSheet), d.scan?.cameraReadyToSheet?.p50 < 300],
];
const md = `# Measured performance

Last run: ${stamp} · ${d.device} · CPU throttle ×${d.cpuThrottle} · ${d.runs} runs per number · ${d.url}
Method: \`app/tools/measure.mjs\` (Playwright + Chromium DevTools CPU throttling; the pack is the full 760k-item
build; scan path uses Chromium's fake camera fed a real UPC-A clip). p50 / p95 across runs. Raw data: \`measure-${stamp}.json\`.

| what | budget | measured p50 / p95 | |
|---|---|---|---|
${rows.map(([w, b, m, ok]) => `| ${w} | ${b} | ${m} | ${b ? (ok ? "✅" : "❌") : ""} |`).join("\n")}

Notes
- "Interactive" = the moment the search box answers (database opened in the worker + first frame painted).
- The keystroke number is input event → the frame in which the new rows are painted, so it includes up to one
  frame of waiting; the worker's own search time is the first "search" row. Long tasks (> 50 ms) during typing: ${JSON.stringify(d.longTasksDuringTyping || [])}.
- Worst keystrokes: ${(d.keystroke?.worst || []).map((w) => `"${w.q}" ${w.totalMs} ms`).join(", ")}.
- Scan runs: ${(d.scan?.runs || []).map((r) => `${r.engine} ${r.decodeMs}/${r.toPriceMs}/${r.cameraReadyToSheetMs} ms`).join("; ")}.
- Search quality spot checks (top result): ${Object.entries(d.topResults || {}).map(([q, r]) => `"${q}" → ${r?.top?.[0] || "—"}${r?.relaxed ? " (closest)" : ""}${r?.fuzzy ? " (spelling adjusted)" : ""}`).join("; ")}.
`;
fs.writeFileSync(path.join(outDir, "README.md"), md);
console.log(md);
