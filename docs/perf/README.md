# Measured performance

Last run: 2026-10-07 · Pixel 7 viewport (412x915 @2.625) · CPU throttle ×4 · 5 runs per number · http://127.0.0.1:8787/
Method: `app/tools/measure.mjs` (Playwright + Chromium DevTools CPU throttling; the pack is the full 760k-item
build; scan path uses Chromium's fake camera fed a real UPC-A clip). p50 / p95 across runs. Raw data: `measure-2026-10-07.json`.

| what | budget | measured p50 / p95 | |
|---|---|---|---|
| Cold start → interactive (DB already on the phone) | < 2000 ms | 623 / 698 ms | ✅ |
|   of which: open the pack from Cache Storage |  | 479 / 588 ms |  |
|   first contentful paint |  | 88 / 100 ms |  |
| First install (download 32 MB from local server + index), once | one-time | 1846 ms | ✅ |
| Search in the worker, per keystroke | < 16 ms | 4 / 8.4 ms | ✅ |
| Keystroke → results painted (worker round trip + DOM + next frame) | ≈ 1 frame | 24.7 / 34.2 ms | ✅ |
| Typed barcode → resolution |  | 4 / 9.1 ms |  |
| Typed barcode → sheet painted | < 300 ms | 46.2 / 60.1 ms | ✅ |
| Scan: one decoder pass on a camera frame (zxing wasm) |  | 19 / 23 ms |  |
| Scan: decoder hit → lookup → sheet painted | < 300 ms | 71.3 / 78 ms | ✅ |
| Scan: camera ready → sheet (incl. two agreeing reads at ~14 fps) | < 300 ms (p50) | 297 / 378 ms | ✅ |

Notes
- "Interactive" = the moment the search box answers (database opened in the worker + first frame painted).
- The keystroke number is input event → the frame in which the new rows are painted, so it includes up to one
  frame of waiting; the worker's own search time is the first "search" row. Long tasks (> 50 ms) during typing: [].
- Worst keystrokes: "toothpa" 37.1 ms, "peanu" 36.7 ms, "peanut bu" 36.3 ms, "2% milk g" 35 ms, "ch" 34.2 ms.
- Scan runs: zxing 16/73.7/301 ms; zxing 22/71.3/286 ms; zxing 19/63.5/378 ms; zxing 15/78/297 ms; zxing 23/68.4/285 ms.
- Search quality spot checks (top result): "peanut butter" → Great Value Great Value Peanut Butter - 16 oz — $1.36; "gv corn" → Great Value Great Value Corn Starch 16oz — $0.84; "diapers size 4" → Parent's Choice Parent's Choice Size 4 Diapers, 32 Count — $4.44; "cheerios" → Honey Nut Cheerios Honey Nut Cheerios Honey Nut Cereal - 20.35 oz — $4.96; "2% milk" → Great Value Great Value 2% Milk Shells & Cheese, 12 oz, 2 Pack Cups — $2.48; "tide pods" → Tide Tide Pods Original Laundry Pods, 35 ct — $4.97; "pb" → Great Value Great Value Peanut Butter - 16 oz — $1.36; "chese" → Marketside Marketside Cheese Danish, 4 ct — $4.86 (spelling adjusted).
