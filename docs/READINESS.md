# Readiness audit — 2026-10-09

Verdict: **not ready for volunteers.** The app shell is solid (offline, scanner fallback, tally, updates all verified
in a real browser; 288 Python + 53 app tests pass), but no real snapshot can publish yet, the live app still serves
sample data on a temporary domain, and the real-data build shows accuracy problems that must be fixed first.

How this was checked: full read of crawler/, app/, pipeline/ and workflows; a local build of the real crawl
(13 finished departments, 2.31M rows kept) with the deterministic gates; 76 hand-checked everyday donation searches;
the 760k fixture driven in Chromium (install, search, every barcode kind, tally, offline, update, reset);
read-only probes of the deployed Workers and Cloudflare account.

## What blocks the first publish today

| # | Finding | Evidence |
|---|---|---|
| B1 | Home and Home Improvement were truncated by Walmart's paginated endpoint but marked `done` | 1,830 of 31,776 and 495 of 5,903 pages; item ids stop at ~40M while complete departments reach ~55B; `crawl.py:94,109` |
| B2 | That fails `departments_complete`; the candidate holds and `decide()` waits forever | `qa.py:154-159`, `ci.py:325-334`; no single-department recrawl exists (`plan=full` wipes all raw pages, `crawl.py:41-44`) |
| B3 | Books (101k pages, almost all media-excluded) and Auto & Tires (15.5k) are 85% of the remaining crawl | 137k pages left ≈ 12–15 days at the current 6–8/min; without them ≈ 2.5 days |
| B4 | Build memory: 7.0 GB peak on 13 of 23 departments, then `qa.check` reloads every row in the same process | `valuation.py:84-97` (`Valuer` indexes every row), `ci.py:504-511` |
| B5 | The app pack cannot deploy at real size: `cols.bin.gz` 25.4 MiB and `tokens.bin.gz` 30.9 MiB exceed the 25 MiB file limit; whole pack 128.5 MB over the wire | `app/tools/build-db.mjs` |
| B6 | The sample review needs a working `ANTHROPIC_API_KEY`; without it every candidate holds | `review.py`, `gates.json sample_review.required` |

## Ordered plan

Each step lists the change, how it is proven, and its exit condition. Steps in the same phase can run in parallel.

### Phase 1 — Unblock the crawl (day 1)

1. **Drop Books and Auto & Tires from the crawl.** Move them to "not crawled" in `data/categories.json` and remove them
   from `state/run.json` on data-store (the running crawl iterates the frozen list, `crawl.py:78`). Append a DECISIONS entry.
   Note: touches crawl scope, so the owner approves first (CLAUDE.md). Exit: next run's summary shows ~20k pages left.
2. **Truncation guard.** In `crawl.run`, a department whose `pages < (1 - dept_size_tolerance) × total_pages` ends as
   `truncated`, not `done`, and opens a `[crawl-truncated]` alert. Test: a fake client that ends early.
3. **Crawl large departments by child node.** Optional `"split": [child ids]` per department in `categories.json`; each child
   is its own cursor; sizing does one call per child. First verify with one call per child that children do not truncate.
   For Home keep only what a food bank receives (Kitchen & Dining, Bath, Bedding, Storage, Cleaning; not rugs/furniture/decor),
   and the same curation for Home Improvement. Scope change: owner approves the child list.
4. **`plan=recrawl dept=<id>`.** Resets one department's cursor and raw pages, leaves the rest. Then recrawl Home and Home
   Improvement by child nodes. Exit: both pass the page-count gate.
5. **Verify `ANTHROPIC_API_KEY`** with the anthropic-key-check workflow and confirm the `SFB_REVIEW_MODEL` id is valid.
6. Small crawler fixes: a 200 with a non-object body is retried, not a crash (`wm.py:150`, `crawl.py:89`); process departments
   in `state["departments"]` order, not set order (`process.py:34`), so the 104 cross-listed items stop changing department.

### Phase 2 — Make a real build fit (days 1–3, while the crawl finishes)

7. **Build memory under 4 GB.** `Valuer` only for categories that hold withheld rows (~2.3k rows); drop the duplicate `seen`
   set (`process.py:47`); intern `path`/`dept`; don't keep `variants` in memory; run `qa.check` in a fresh subprocess.
   Proof: measure peak RSS on the full real raw data with `/usr/bin/time -v`; record it in RUNBOOK.
8. **Pack builder.** Shard every column/index file above 24 MiB like `strings-N`; reader accepts both forms (format 3, v2
   still readable). Split the pack into **core** (consumable departments, downloaded first, target ≤ 40 MB) and **more**
   (durables, downloaded in the background after core opens; search says "still loading other departments" until then).
   Proof: build from the real snapshot; measure first-install time and memory on a mid-range Android and an iPhone SE.
9. **Promo guard persists.** Carry the kept normal price forward while `prev` has `kept_normal_price` (`process.py:62`), and
   on the first publish fall back to the price-history median or withhold the promo row. Test: two consecutive clearance builds.

### Phase 3 — Accuracy (days 2–6)

10. **Pack and count parsing.** Hand-checked failures: "Charmin 4ct" → 4 ct ×4, "12 Double Rolls", "52 Diapers", "4 Bars",
    "5 oz, 8 Cans" → ×1, "GV Diced Tomatoes 12 Count", "(6 pack) … 24 oz" → ×1. Add each as a gold test in
    `tests/` first, then fix `normalize.py`. Display sizes rounded to 3 significant digits (f32 shows 15.800000190734863).
11. **Suspicious prices that pass sanity.** Similac Advance 12.4 oz $120.72, Carnation 5 fl oz $21.92, Del Monte 8 oz $12.24,
    Sechler's 16 oz $23.94, Parent's Choice 36 ct $2.00: these are multipacks without a parsed pack or feed errors. After
    step 10, extend price sanity: per-unit > 10× the kind's median *with* a parsed size is withheld (not just flagged).
12. **Stale "Not available" rows.** 87% of core rows are not available online. Stratify the live audit by stock status and
    measure the price match of each stratum. If not-available rows match ≥ 95%, keep them; otherwise rank them below
    available rows and label "online price, may be out of date". Owner decides after the numbers.
13. **Department contamination.** Baby contains Cisco gear, server contracts and rugs; Patio holds 183k Home rows. Add an
    out-of-scope rule for enterprise IT/services and check the category gold set still passes ≥ 90%.
14. **Search.** (a) Relaxation drops the most *common* word, not the rarest ("great value dry pinto beans" currently drops
    "pinto" and "beans"). (b) Ranking: product-noun match outranks accessory nouns ("huggies diapers" → diapers before
    diaper bags; "great value sugar" → granulated before sanding sugar; "spam" → SPAM). (c) Add a **gold search set** of
    ~150 real donation queries with the expected item in the top 3, run against the real pack in CI; gate ≥ 95%.
15. **Store-label typos (high risk).** One wrong digit turned a $5.99 label into $206.99 (`barcode.js:121-122`), and an
    11-digit typed code gets a made-up check digit (`barcode.js:78,116`). Fix: no price when the check digit fails; no
    check-digit completion for typed store labels; the 5-digit fallback requires "Matches the printed price?" before Add;
    an 11-digit typed product code shows "Check the last digit" instead of opening another product.
16. **PLU prices.** Match distinctive words (yellow/orange pepper, Vidalia, Cara Cara, portabella), prefer per-lb loose rows
    over bags, fall back to the typical price outside 0.4–2.5× typical (`build-db.mjs:308-322`). Organic pricing is a policy call.
17. **Live check obeys price sanity** (`app.js:523-575`): hide "Use it" outside [$0.10, department cap] or > 20× below the
    saved price; label `STORE_ONLY`/not-available listings.
18. Small: duplicated brand on equivalents (`resolve.js:134`, use `titleOf`); About text says "Strongsville area" but prices
    are online, unpinned (`app.js:687`); implement the open UPC-E item in `gtin14()` (`normalize.py:106-119`).

### Phase 4 — App reliability on real phones (days 3–7)

19. **Failed first download.** Cancel the parallel queue on the first error, ignore late progress, retry with backoff,
    network wording instead of "couldn't be opened" (`db-client.js:166-183`, `app.js:181`).
20. **iOS storage.** First-run banner in Safari tabs with Add to Home Screen steps; warn when a save fails (`writeJson`
    currently swallows quota errors); "Share tally first?" before Reset or Clear.
21. **Old iPhones.** Feature-check DecompressionStream / OffscreenCanvas and say "needs iOS 16.4 or later" plainly.
22. **Scanner offline on Safari.** Ship the zxing worker as a real file (`scanner.js:53-70` builds it from a Blob URL), then
    run app-browsers with WebKit offline.
23. **Tally record.** Per-donation sessions ("New donation" archives the last), CSV export with time, barcode, result kind
    and price; flag non-exact lines. Shape depends on the food bank's answer to "what happens to the price after lookup".

### Phase 5 — Operations and handoff (in parallel; must finish before any install)

24. **Move to the food bank's Cloudflare account and `value.strongsvillefoodbank.org`** before a single volunteer installs:
    offline data does not follow an origin change. Today there is one personal account with no zone. Redeploy both Workers,
    update `APP_URL`, `LIVE_CHECK_URL`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`. (Cloudflare account: owner action.)
25. **Manual plans can be silently cancelled.** One pending run per concurrency group; the chained `continue` replaces a
    pending `approve`/`rollback`. Record requested plans in `state/requests.json` and have the chain step honour them.
26. **Live-check quota.** `PRICE_GLOBAL_LIMITER` is per Cloudflare location; lower it to ~20/min so app traffic cannot
    push the crawler into 429s; restrict CORS to the app origin. Admin token in a header, constant-time compare.
27. **Docs.** Replace the stale "schedule never fires" entries (it fires; cancelled runs are queued runs replaced by the
    chain). Volunteer quick-start (install on iPhone/Android, first sync on Wi-Fi, what each label and banner means);
    coordinator page (who to call, how to tell prices are stale); rotation runbook for every secret (the crawler and Worker
    share the Walmart key); owner and backup per account. Check Walmart affiliate terms on the public `data-store` branch.

### Phase 6 — Acceptance: go/no-go with evidence

28. First real publish with every gate passing (live match ≥ 97%, review passed, sentinels 117/117 on the reduced scope).
29. **Shelf spot-check** at Walmart Strongsville (#2266): 50 items from a real donation table; ≥ 90% within 10% of shelf.
30. **Device matrix:** iPhone SE (iOS 16.4+), a current iPhone, a mid-range Android; installed to Home Screen; scan 30 real
    items each, airplane mode for a day, an update arriving, 7 days without opening (iOS eviction).
31. **Pilot:** 2–3 volunteers, one week of real donations, tally exported each day; log every wrong or missing item and fix.
32. Go when: gold search ≥ 95% top-3, spot-check ≥ 90% within 10%, no blank or crash in the pilot, alerts all closed, handoff
    docs reviewed by the coordinator.

## Decisions needed from the food bank / owner

- Crawl scope: drop Books and Auto & Tires; curated child nodes for Home and Home Improvement (steps 1, 3).
- Cloudflare account and domain (step 24); who owns each account and secret.
- What happens to the tally (step 23); shared tablet or personal phones.
- Pricing policy owner: organic PLUs, used electronics, online "not available" prices (steps 12, 16).
