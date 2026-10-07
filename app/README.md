# SFB Value — the volunteer app

Scan or type a donated item, see its exact Walmart price. Works with no network after the first open,
on the phone already in the volunteer's hand. Lives in `app/`; deployed to Cloudflare Workers static assets
by `.github/workflows/deploy-app.yml`; the price data comes from the pipeline's published snapshot
(`data-store` branch) or, until the first snapshot is published, a full-size synthetic fixture that the app
labels "sample data".

```
app/
  public/            the app as served (no bundler; plain ES modules)
    index.html       one screen: header, home, results, dock (search + Scan), sheets, scanner, toasts
    app.css          design tokens + components (light/dark, reduced motion, high contrast)
    sw.js            app-shell service worker (precache list + build hash stamped at build time)
    js/app.js        UI controller
    js/db-client.js  install / cache / update the database pack; proxy to the worker
    js/db-worker.js  pack reader + search + lookups (runs off the main thread)
    js/tokenize.js   shared tokenizer (same file is imported by the pack builder)
    js/barcode.js    GTIN / UPC-E / store-label / PLU mathematics
    js/resolve.js    resolution engine (exact → label → PLU → equivalent → closest)
    js/scanner.js    camera + native BarcodeDetector (self-tested) or zxing-cpp wasm in a worker
    vendor/          zxing-wasm reader (ESM + wasm, Apache-2.0)   fonts/  Geist + Geist Mono (OFL)
  tools/
    make_fixture.py  760k-row synthetic snapshot in the crawler's row format (through crawler/normalize.py); its
                     version is a hash of the inputs, so unchanged inputs never make phones re-download
    build-db.mjs     snapshot (items.jsonl.gz + equivalents) → sfb-pack v1 under dist/db/<version>/
    build-site.mjs   public/ → dist/, stamps sw.js + config meta, writes _headers
    serve.mjs        local static server that mirrors production headers
    measure.mjs      the performance numbers below (Playwright, 4× CPU throttle, fake camera)
    shots.mjs        phone-size screenshots (light/dark) + accessibility audit
  tests/             node --test: barcode maths, tokenizer, resolution engine
  wrangler.toml      assets-only Worker config
```

Commands: `npm run fixture` · `npm run build` (db + site) · `npm run serve` · `npm test` · `npm run measure` · `npm run shots`.

## Screens

One screen, two ways in. The **dock** at the bottom holds the search field and the Scan button, where a thumb
rests. Results are a bottom-anchored list: the best match sits right above the search box and the list grows
upward, so the eye never travels. Tapping a result (or a scan, a produce code, a store label) opens a
**bottom sheet** whose only loud element is the price, followed by the exact item (brand bold, variant, size,
pack, per-item price for packs), the date the price was checked, a note explaining anything unusual, a
quantity or weight stepper, and **Add to tally**. The sheet's coloured label names the resolution kind:

| label | when | what is shown |
|---|---|---|
| Exact item | barcode or chosen search hit found in the snapshot (incl. retired UPCs, "older barcode") | item, price, other listings for the same barcode |
| Store price label | barcode starting with 2 (scale labels: meat, deli, bakery) | price decoded from the barcode, GS1 verifier checked |
| Produce code | 4-digit PLU (and 9xxxx organic) | produce name, price per lb or each, weight stepper |
| Equivalent value | barcode Walmart doesn't sell, present in the equivalents table | estimated price, confidence, the Walmart basis item (tappable) |
| Closest match | the search had to drop a word to find anything | nearest item, the ignored word named |
| Live Walmart price | unknown barcode, phone online, Walmart has it | live price and name from the Worker route |
| Not in database | unknown barcode, nothing online | "Find it by name" (search focused) — never a silent blank |

Also: running tally (count, total, share/copy), recent lookups, settings (appearance, haptics, live check, database
facts, check for new prices, reset), scanner with torch, typed-barcode fallback for denied cameras and keyboard-wedge scanners.

## Visual direction

Warm paper in light mode, warm near-black in dark mode, following the phone. Geist for text, Geist Mono for
barcodes. One accent (deep green) for the primary action; the five resolution kinds have their own hues, used
only as labels with a dot and text, never as the only signal. Type is 14 px minimum, prices 20 px in lists and
52–64 px in the sheet, targets 44 px minimum. Motion is a 320 ms rise on the rows nearest the thumb and a spring
on the sheet; `prefers-reduced-motion` turns it off and `prefers-contrast: more` lifts the secondary greys.

## Data: loading and indexing

**Pack format (sfb-pack v1)** — built once per snapshot by `tools/build-db.mjs`, served as static files under
`/db/<version>/` with immutable caching, ~32 MB over the wire for 760k items:

| file | contents |
|---|---|
| `cols.bin.gz` | per-item columns in rank order: price (u32 cents), size (f32), pack (u16), unit, basis, flags, category (u8), Walmart id (f64), GTIN-14 (f64) |
| `strings-N.bin.gz` | `brand\x1Fname` blobs with offset tables, sharded so no file exceeds Cloudflare's 25 MiB limit |
| `upc.bin.gz` | sorted GTIN-14 keys → rank, primary listing first for each barcode |
| `tokens.bin.gz` | sorted dictionary + varint-delta posting lists + each token's home category |
| `equiv.bin.gz` | equivalents: GTIN → estimated price, confidence, basis rank, name/quantity |
| `plu.json` | PLU → produce name, unit, price (from the snapshot's produce rows, else a typical price) |

Items are stored in *rank order* (primary listing, store brand, in stock, core department, short name first),
so a search that scans the AND of two bitsets from rank 0 upward meets the best candidates first and can stop
early. Each posting list decodes into a `Uint32Array` bitset (one bit per item, 95 KB); single-letter prefixes
are warmed after load and the rest live in a small LRU.

**On the device** — `db-client.js` downloads the pack into a Cache Storage bucket named after the snapshot
version, remembers the version in localStorage and asks the worker to open it. Opening means: read each file
from Cache Storage, inflate with `DecompressionStream`, wrap typed arrays over the buffers (no parsing, no copy),
decode the dictionary. On every launch the app fetches `db/current.json` (network-first, 1 KB); a newer
snapshot downloads in the background into its own bucket while the current one keeps answering, and is swapped in
when nothing is open (or on tap, or at the next launch). The swap is committed only after the new pack opens; a pack
that fails to open is deleted and the previous one restored.
The service worker precaches only the app shell (HTML, CSS, JS, fonts, wasm, icons: ~1.2 MB).

**Search** (`db-worker.js`) — tokenize the query (shared tokenizer), expand abbreviations (gv, pb, oz, pk…),
plural stems and synonyms, prefix-match every word against the dictionary, OR the postings of each word's
expansions, AND the words, collect the first 400 candidates by rank, score them (exact word > prefix, brand
match, size/pack number match, words adjacent in the name, the word's home department, repeated word, coverage
of the item's content words, store brand; retired or out-of-stock pushed down) and return 40. A word that
matches nothing gets one-edit alternatives; if the AND is empty the most restrictive word is dropped and the
result is flagged. The main thread renders 12 rows synchronously and the rest on the next idle slice;
off-screen rows skip layout via `content-visibility`.

**Barcodes** (`barcode.js`) — GS1 check digits, UPC-E → UPC-A expansion, 11-digit typed codes completed, EAN-13
with a leading zero folded into UPC-A, GTIN-14 keys as exact doubles (≤ 2^53), GS1 US store labels
`2 IIIII V PPPP C` with the 4-digit price verifier (and the 5-digit no-verifier fallback), PLU 3000–4999 with
8/9 prefixes (8xxxx codes are their own items). The scanner accepts retail symbologies only, requires two agreeing
reads on either engine before it fires, and ignores the code it just priced for 2.5 s so an item left in frame after
"Add to tally" is not counted twice.

## Performance budget and measured numbers

Method: `tools/measure.mjs` drives the built app in Chromium (Pixel 7 viewport) with **4× CPU throttling** as a
mid-range-phone proxy, the full 760k-item pack, a local server, and Chromium's fake camera fed a real UPC-A
clip for the scan path. Every number below comes from that script (`build/measure.json`); nothing is estimated.

| requirement | budget | measured (p50 / p95) |
|---|---|---|
| cold start to interactive, DB already on the phone | < 2 s | see `docs/perf/measure.json` → `coldStart.interactive` |
| first install (download 32 MB + index) | one-time | `firstInstall` |
| search per keystroke, worker | < 16 ms | `keystroke.worker` |
| keystroke → results painted (worker round trip + DOM) | ≈ one frame | `keystroke.total` |
| typed barcode → sheet painted | < 300 ms | `lookup.toSheet` |
| scan: decoder hit → price → sheet painted | < 300 ms | `scan.decodeToPrice` |
| scan: camera ready → sheet (incl. two agreeing reads) | < 300 ms | `scan.cameraReadyToSheet` |

The latest run is summarised in `docs/perf/README.md` next to the raw JSON.

## Offline and updates

- First open online: shell precached (~1.2 MB), pack downloaded (~32 MB) with a progress bar; "Add to Home
  Screen" keeps iOS from evicting storage.
- Every later open: shell from the service worker, pack from Cache Storage, interactive in well under a second,
  no network needed. `navigator.storage.persist()` is requested.
- Online: `current.json` is checked; a new snapshot is fetched in the background and applied when idle.
- Live check: when online, a scanned/typed barcode is also sent to the pipeline Worker's public
  `/v1/price/<gtin>` route (rate limited, cached, no token); a differing live price is shown with the delta and
  can be used for the tally with one tap. Unknown barcodes that Walmart does sell become a "Live Walmart price".

## Accessibility

Every control has a name; targets are ≥ 44 px; text ≥ 13 px with ≥ 4.5:1 contrast (audited by `tools/shots.mjs`);
dialogs are real `<dialog>` elements with focus trapping and Escape/back-button close; results and status use
`aria-live`; the scanner makes the page behind it inert and closes on Escape; the dock precedes the list in the DOM so
Tab order follows the thumb (search → Scan → best result). The whole app works one-handed from the bottom of the
screen and with an external keyboard (`/` focuses search, Enter opens the best result, digits + Enter from a
keyboard-wedge scanner resolve the code directly).
