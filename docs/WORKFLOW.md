# Data workflow — autonomous, verifiable, resumable

Status: DESIGN. Stages 0–1 are built; Stage 2 onward is built only after the Stage 1 tests pass and David approves.

## Principles
1. **Deterministic collection.** Every item and price comes straight from the Walmart Affiliate API. No AI model writes or guesses a price. AI is used at most for parsing awkward size strings, and those rows are flagged.
2. **Provenance on every row.** itemId, source node, observed_at, raw price fields. Anything can be traced back to the API.
3. **Resumable.** Crawl state lives in a database, not in memory. A failed or rate-limited run resumes where it stopped.
4. **Gated publishing.** A new price snapshot reaches the app only if it passes the quality gates below. Otherwise the previous snapshot stays live and a report explains why.
5. **No human steps in the loop** after the first approved snapshot. David only sees reports and exceptions.

## Stages
**0. Auth** — signed requests, /health, /taxonomy. DONE.

**1. Tests (now)** — answer three questions before building the crawler:
- *Fields:* what /paginated/items returns (price fields, size, seller, UPC). Route: `/items/<node>?pages=1&raw=1`
- *Paging:* does a node include its sub-nodes; how many items per page; is totalPages reported; how fast. Route: `/items/<node>?pages=5`
- *Coverage:* are common donation items in the online catalog. Route: `/search?q=...`
Decide from results: valuation price field (salePrice vs msrp), seller filter, whether "Shop All" nodes are complete.

**2. Discovery** — walk the taxonomy under every mapped node; store every descendant node with its path and our category in D1 `nodes`. Pantry split happens here.

**3. Crawl** — Cloudflare Cron Trigger every few minutes. Each run takes the next pending node from D1 `crawl_jobs`, fetches a bounded number of pages (stays under Worker subrequest limits and Walmart rate limits), upserts items into D1 `items`, saves the nextPage cursor, and stops. Retries with backoff; a node failing 3 times is marked `failed` and reported, never silently skipped.

**4. Normalize** — parse size/unit/pack from `size` and `name` (rules first; unparseable rows flagged `needs_review`). Keep Walmart-sold items only. Dedupe on itemId.

**5. Quality gates** (all must pass to publish):
- Every mapped node crawled to completion (no `pending`/`failed` jobs).
- ≥ 98% of kept items have a price.
- Per-category item count within ±20% of the previous snapshot (first run: David approves manually).
- Sentinel coverage: a fixed list of ~100 common donation items (data/sentinels.json) must each resolve to a priced item.
- Price drift: items whose price moved > 50% since last snapshot are listed in the report (not blocking unless > 2% of items).

**6. Publish** — write a versioned, compressed snapshot plus manifest (version, date, counts, gate results). The PWA checks the manifest when online and downloads only on change.

**7. Refresh** — a monthly cron restarts Stage 3 for all nodes. Status always visible at `/status`.

## Storage
- D1 database `sfb-db`: tables `nodes`, `crawl_jobs`, `items`, `runs`, `reports`.
- Snapshot: served by the Worker from D1 (or R2 if size requires).
- Needs from David: create D1 `sfb-db` in the Cloudflare dashboard and send the database ID (Stage 2).

## Stage 1 findings (2026-10-06)
- Paginated catalog: 200 items/page, includes all sub-nodes, reports totalPages. Fresh Produce = 42 pages (~8.4k items). Pantry = 3,027 pages (~605k items) — mostly third-party listings and junk (cookbooks, CDs, salt cellars).
- Rate limit: HTTP 429 on the 3rd back-to-back request (~1s apart). Crawler must throttle.
- Catalog items have no sellerInfo/offerType, but do have a `marketplace` boolean. Search results do have sellerInfo/offerType.
- msrp is unreliable (e.g. Libby's corn msrp $7.35 vs salePrice $1.22). salePrice matches real shelf prices.
- `size` field is unreliable ("Each", "2", or wrong — "10 oz" salad listed as "23 oz"). Product name is the better size source.
- Some UPCs are prefixed "deleted_" (retired items). Many catalog items are stock "Not available".
- Coverage: search found Great Value canned corn in 8.5, 15, 15.25, 29, 106 oz, store-only frozen items, and multipacks — all priced, seller Walmart.com. Third-party sellers list the same items at 5–10x price.

## Proposed decisions (pending David's OK)
- Valuation price = salePrice. msrp ignored.
- Keep only Walmart-sold items: marketplace == false (catalog) / sellerInfo == "Walmart.com" (search). Drop rows with no salePrice or a "deleted_" UPC.
- Size/pack parsed from name first, size field second; disagreement flagged.
- Multipacks ("(8 pack)", "12 Count") kept as their own rows with pack_count, plus per-unit price.
- Crawl throttled to stay under the 429 limit; exact rate set from the throttle test.
- Pending test: whether catalog filters soldByWmt=true / available=true work (would cut Pantry from ~605k to Walmart-sold items only).
