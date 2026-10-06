# Measured performance

Last run: 2026-10-06 · Pixel 7 viewport (412x915 @2.625) · CPU throttle ×4 · 5 runs per number · http://127.0.0.1:8787/
Method: `app/tools/measure.mjs` (Playwright + Chromium DevTools CPU throttling; the pack is the full 760k-item
build; scan path uses Chromium's fake camera fed a real UPC-A clip). p50 / p95 across runs. Raw data: `measure-2026-10-06.json`.

| what | budget | measured p50 / p95 | |
|---|---|---|---|
| Cold start → interactive (DB already on the phone) | < 2000 ms | 520 / 567 ms | ✅ |
|   of which: open the pack from Cache Storage |  | 403 / 415 ms |  |
|   first contentful paint |  | 72 / 112 ms |  |
| First install (download 32 MB from local server + index), once | one-time | 1523 ms | ✅ |
| Search in the worker, per keystroke | < 16 ms | 2.8 / 5.5 ms | ✅ |
| Keystroke → results painted (worker round trip + DOM + next frame) | ≈ 1 frame | 23.7 / 31.3 ms | ✅ |
| Typed barcode → resolution |  | 1.4 / 3.7 ms |  |
| Typed barcode → sheet painted | < 300 ms | 33.1 / 55.4 ms | ✅ |
| Scan: one decoder pass on a camera frame (zxing wasm) |  | 12 / 22 ms |  |
| Scan: decoder hit → lookup → sheet painted | < 300 ms | 62.1 / 69.5 ms | ✅ |
| Scan: camera ready → sheet (incl. two agreeing reads at ~14 fps) | < 300 ms (p50) | 270 / 333 ms | ✅ |

Notes
- "Interactive" = the moment the search box answers (database opened in the worker + first frame painted).
- The keystroke number is input event → the frame in which the new rows are painted, so it includes up to one
  frame of waiting; the worker's own search time is the first "search" row. Long tasks (> 50 ms) during typing: [].
- Worst keystrokes: "pe" 35 ms, "2%" 32.7 ms, "tooth" 32.2 ms, "diapers" 31.7 ms, "gv co" 31.3 ms.
- Scan runs: zxing decoder 12/51.9/333 ms; zxing decoder 8/58.4/215 ms; zxing decoder 21/63.7/325 ms; zxing decoder 8/62.1/244 ms; zxing decoder 22/69.5/270 ms.
- Search quality spot checks (top result): "peanut butter" → Great Value Great Value Peanut Butter - 16 oz — $1.36; "gv corn" → Great Value Great Value Corn Starch 16oz — $0.84; "diapers size 4" → Parent's Choice Parent's Choice Size 4 Diapers, 32 Count — $4.44; "cheerios" → Honey Nut Cheerios Honey Nut Cheerios Honey Nut Cereal - 20.35 oz — $4.96; "2% milk" → Great Value Great Value 2% Milk Shells & Cheese, 12 oz, 2 Pack Cups — $2.48; "tide pods" → Tide Tide Pods Original Laundry Pods, 35 ct — $4.97; "pb" → Great Value Great Value Peanut Butter - 16 oz — $1.36; "chese" → Marketside Marketside Cheese Danish, 4 ct — $4.86 (spelling adjusted).
