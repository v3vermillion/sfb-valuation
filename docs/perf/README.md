# Measured performance

Last run: 2026-10-09 · Pixel 7 viewport (412x915 @2.625) · CPU throttle ×4 · 5 runs per number · http://127.0.0.1:8787/
Method: `app/tools/measure.mjs` (Playwright + Chromium DevTools CPU throttling; the pack is the 760k-item fixture in
pack format 3, 19 department shards; the camera path was not run this time, the typed paths were). p50 / p95 across runs.
Raw data: `measure-2026-10-09.json`; the 2026-10-07 column is the single-file format 2 pack (`measure-2026-10-07.json`).

| what | budget | 2026-10-09 (v3) p50 / p95 | 2026-10-07 (v2) | |
|---|---|---|---|---|
| Cold start → interactive (DB already on the phone) | < 2000 ms | 872 / 943 ms | 623 / 698 ms | ✅ |
|   of which: open the pack from Cache Storage |  | 711 / 732 ms | 479 / 588 ms |  |
|   first contentful paint |  | 84 ms | 88 / 100 ms |  |
| First install (download 33 MB core from local server + index), once | one-time | 1178 ms | 1846 ms (32 MB, all) | ✅ |
| Search in the worker, per keystroke | < 16 ms | 3.4 / 12.8 ms | 4 / 8.4 ms | ✅ |
| Keystroke → results painted (worker round trip + DOM + next frame) | ≈ 1 frame | 24.5 / 38.4 ms | 24.7 / 34.2 ms | ✅ |
| Typed barcode → resolution |  | 3.2 ms | 4 / 9.1 ms |  |
| Typed barcode → sheet painted | < 300 ms | 42.8 / 53.3 ms | 46.2 / 60.1 ms | ✅ |
| Scanner screen, typed barcode → sheet | < 300 ms | 78.7 / 100.3 ms |  | ✅ |
| Scan: decoder hit → lookup → sheet painted | < 300 ms | not run | 71.3 / 78 ms |  |
| Search worker memory (the open pack) |  | 99.6 MB |  |  |

Format 3 trades about 250 ms of cold start (19 shards opened instead of one pack) for an app that is usable as soon
as the consumable departments arrive, weekly updates that download only the shards whose bytes changed, and a pack
that can grow past one file. The first measurement of format 3 had a 101 ms p95 keystroke: one-letter queries scored
400 candidates in every shard. Candidates are now one budget of about 400 shared by the shards (in proportion to their
matches, at least 40 each) and each item's words, brand words and head noun are cached; the gold set is unchanged
(328/330 on the real crawl).

Notes
- "Interactive" = the moment the search box answers (database opened in the worker + first frame painted).
- The keystroke number is input event → the frame in which the new rows are painted, so it includes up to one
  frame of waiting; the worker's own search time is the first "search" row. Long tasks (> 50 ms) during typing: 1.
- Worst keystrokes: "p" 59.7 ms, "p" 52.8 ms, "to" 43.1 ms, "pea" 41.1 ms, "cheeri" 38.4 ms (one long task in all the typing).
- Search quality spot checks (top result): "peanut butter" → Great Value Peanut Butter - 16 oz — $1.26; "gv corn" → Great Value Muffin Mix Corn, 7 oz — $0.90; "diapers size 4" → Parent's Choice Size 4 Diapers, 32 Count — $4.64; "cheerios" → Cheerios with Almonds Cereal 18oz — $3.28; "2% milk" → Marketside Lactose Free 2% Milk, 96 fl oz — $3.89; "tide pods" → Tide Pods Lavender Laundry Pods, 16 ct — $2.64; "pb" → Great Value Peanut Butter - 16 oz — $1.26; "chese" → Marketside Pimento Cheese 12oz — $3.79 (spelling adjusted). The real-crawl gold set is the quality measure; these are fixture rows.
