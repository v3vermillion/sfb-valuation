# Decisions (dated, newest last — this file wins on conflict)

- 2026-10-05 — Fully offline PWA with search bar; no barcode wizard, no online/vision path (would recreate subscription cost).
- 2026-10-05 — Walmart is the primary price reference. Regular price only, first-party seller only. Clothing excluded.
- 2026-10-05 — 23 categories exist for the data pipeline only, not app UX. Brand and size are row attributes.
- 2026-10-06 — Scraping abandoned: Walmart blocks datacenter IPs (browser-bridge test failed). Data source is Walmart I/O Affiliate API.
- 2026-10-06 — Prices are Walmart.com online prices; store pinning to Strongsville not required.
- 2026-10-06 — Walmart I/O app "SFB-Donation-Valuation" created; public key uploaded (body-only format accepted), Production, key version 1.
- 2026-10-06 — Repo created (private). Pipeline Worker deploys from GitHub via Cloudflare Git integration (owner is phone-only).
- 2026-10-06 — Taxonomy auth test passed (HTTP 200, 51 top-level departments). Relevant departments: Food 976759, Health and Medicine 976760, Personal Care 1005862, Beauty 1085666, Baby 5427, Pets 5440, Household Essentials 1115193, Home 4044, Office Supplies 1229749, Toys 4171, Books 3920, Seasonal 1085632, Pharmacy 5431. Clothing excluded.
- 2026-10-06 — Worker name standardized to sfb-valuation (matches Cloudflare); was sfb-pipeline in wrangler.toml.
- 2026-10-06 — Root cause of builds not triggering: Cloudflare GitHub app had "Only select repositories" (CaringForACause only). Switched to All repositories.
- 2026-10-06 — Food mapping drafted in data/categories.json (Pantry split pending). Added From Our Brands (store-brand coverage) and Seasonal Grocery. Alcohol and promo/brand/event nodes excluded.
- 2026-10-06 — Data workflow defined in docs/WORKFLOW.md: deterministic API crawl (no AI-generated prices), D1-backed resumable cron crawl, quality gates before publishing. Stage 1 test routes /items/<id> and /search added.
- 2026-10-06 — Stage 1 results recorded in docs/WORKFLOW.md. Proposed: salePrice as valuation price; Walmart-sold only; size parsed from name. Testing catalog filters soldByWmt/available next.
- 2026-10-06 — Approved: barcode scanner in the app (offline) + live Walmart check when online. App stays offline-first.
- 2026-10-06 — Crawler moved to GitHub Actions (Cloudflare free tier limits too low for a full crawl). Worker kept for live checks.
- 2026-10-06 — Valuation price = salePrice; msrp ignored. Walmart-sold only (soldByWmt=true + marketplace=false + seller check). Size/pack from product name first.
- 2026-10-06 — Retired ("deleted_") UPCs kept and flagged, because donations include old stock. Promo prices keep last normal price.
- 2026-10-06 — Non-Walmart barcodes (Aldi, Giant Eagle, Marc's, Meijer, Target, Dollar General, Kirkland, regional): identified via Open Food/Beauty/Products Facts, priced at the closest Walmart equivalent, labeled "equivalent value". Kroger API not used (no Kroger stores in the area; Kroger items are rare donations).
- 2026-10-06 — Store-printed price barcodes (prefix 2) decoded in-app; PLU produce stickers supported. Never show blank or unpriced results.
- 2026-10-06 — Scope expanded: Auto & Tires, Electronics, Cell Phones, Jewelry, Sports & Outdoors, Home Improvement, Patio & Garden, Arts Crafts, Party & Occasions added. Not crawled: clothing, music, movies, video games, industrial, instruments, collectibles.
- 2026-10-06 — Schedule: full crawl monthly, core refresh weekly, resume check every 12h. Quality gates must pass before publishing; first snapshot needs David's approval.
- 2026-10-06 — App built in `app/` as a static offline PWA (no framework, no build step beyond packing the database). Hosted on Cloudflare Workers static assets, deployed by GitHub Actions (`deploy-app.yml`) on every app change and after every pipeline run; secrets CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID live in GitHub Actions. The database is served from the same origin under `/db/<version>/`, never fetched from the data-store branch directly.
- 2026-10-06 — Database format for the phone: "sfb-pack v1" — rank-ordered column arrays (price, size, pack, unit, flags, category, id, UPC), sharded string blobs, a sorted UPC→rank table, a prefix-token inverted index with varint postings, an equivalents table and a PLU table; each file gzipped whole (~33 MB over the wire for 760k items), inflated with DecompressionStream and searched with bitset AND/OR in a Web Worker. Chosen over SQLite/FTS-in-wasm and IndexedDB because it opens in well under a second from Cache Storage and answers a prefix search in ~2 ms at full size; IndexedDB imports of 750k rows take minutes on a phone.
- 2026-10-06 — Database lifecycle on the device: pack files live in Cache Storage buckets per snapshot version (`sfb-db-<version>`); the service worker precaches only the app shell. `db/current.json` is checked network-first on every launch; a newer snapshot downloads in the background and is swapped in when the volunteer is idle (or on tap), then the old bucket is deleted. Nothing is ever written back.
- 2026-10-06 — Search behaviour: prefix match on every typed word, abbreviations (gv→Great Value, pb→peanut butter, oz/ounce, pk/ct), plural stemming, one-edit typo tolerance when a word matches nothing, and relaxation (drop the most restrictive word, result flagged "Closest match") so a search is never blank. "%" after a number is kept as the word "percent" so "2% milk" finds 2% milk. Ranking: exact word > prefix, brand match, size/pack number match, words adjacent in the name, the word's home department, store brand, with retired/out-of-stock listings pushed down.
- 2026-10-06 — Resolution labels in the UI follow WORKFLOW.md exactly: Exact item (incl. "older barcode" for retired UPCs and other listings for the same UPC), Store price label (prefix 2, GS1 US price verifier checked), Produce code (PLU, by the pound or each, weight stepper), Equivalent value (basis item card shown), Closest match (flagged, the ignored word named), Live Walmart price (unknown barcode found online). Every result shows brand, variant, size, pack, price and the date prices were checked.
- 2026-10-06 — Barcode scanner: native BarcodeDetector is used only after a self-test decodes a synthetic UPC-A (iOS 18 shipped a detector that returns nothing); otherwise zxing-cpp (wasm, vendored, 0.9 MB) runs in a dedicated worker. Two agreeing reads are required before a result fires. Typed-barcode fallback is always one tap away for denied cameras and external keyboard-wedge scanners.
- 2026-10-06 — Live check added as a public route on the pipeline Worker: `GET /v1/price/<gtin>` with no admin token (the app never holds one). Guarded by strict GTIN validation (check digit; store labels and PLUs rejected), a Cloudflare rate-limit binding (30 requests / IP / minute), a 6-hour edge cache per GTIN, GET-only CORS, and the same Walmart-sold-only rule as the crawler. Admin routes stay token-gated.
- 2026-10-06 — Visual direction: one screen, thumb-zone dock (search + Scan) at the bottom, results anchored above it with the best match adjacent to the search box, a bottom sheet with a very large price as the only loud element, colour used only to name the resolution kind. Geist / Geist Mono (self-hosted), warm paper light theme and warm near-black dark theme following the phone, 44 px minimum targets, text ≥ 14 px, reduced-motion and increased-contrast honoured.
- 2026-10-06 — Until the first snapshot is published, the app is built against a 760k-item synthetic fixture generated through `crawler/normalize.py` and `crawler/identify.py` rules (sentinel gate 117/117) so performance is proven at real scale; the app labels it "sample data" everywhere and the deploy switches to the published snapshot automatically.
- 2026-10-06 — Measured on Chromium with 4× CPU throttling (mid-range phone proxy), 760k items: cold start to interactive p50 0.56 s (DB already on the phone), first install 2.2 s + download; search p50 2 ms in the worker, keystroke-to-paint p50 48 ms before and ≤ 16 ms budgeted after chunked rendering (re-measured in app/README.md); scan decode→price→sheet p50 61 ms, camera-ready→sheet p50 263 ms. Numbers and method in `app/README.md` and `docs/perf/`.
- 2026-10-06 — Running tally and recent lookups are kept in localStorage on the device only (share/copy as text); the open question in PLAN.md about what happens after a lookup is answered provisionally this way and can be changed without touching data.
- 2026-10-07 — Review round on the app (adversarial multi-lens review, findings verified by hand): the pack swap now happens only after the new pack opens (rolled back otherwise), a background price download never blocks search, a downloaded-but-unapplied snapshot is applied at the next idle moment and survives a relaunch, recents reopen by barcode (never by a snapshot's row number), the result-count / "Closest matches" line is pinned at the thumb end of the list, the scanner needs two agreeing reads on every engine and ignores the code it just priced for 2.5 s, only retail symbologies are accepted, a store label whose price field is 0000 is looked up in the catalog instead of showing $0.00, and a store label counts as verified only when both its price verifier and its GS1 check digit agree.
- 2026-10-07 — Live price route: a second rate-limit binding caps Walmart calls at 60 per minute across all callers (the per-IP cap stays at 30/min); both are charged only on a cache miss; cache hits are sent with `no-store` so a phone never shows a stale "right now"; Walmart 429/5xx answers are 503 with `retry-after` and remembered for one minute; every Walmart-sold listing for a barcode is returned so the app compares the listing it is showing; the route answers 503 when the bindings are missing (fails closed).
- 2026-10-07 — Fixture snapshot versions are a hash of the generator inputs (`fixture-<sha1>`), so a rebuild of unchanged inputs produces the same version and no phone re-downloads 32 MB; deploy-app runs after a pipeline run only when that run succeeded, builds without deploying when nothing new was published, and refuses to deploy the fixture over a real snapshot when the data-store checkout merely failed.
- 2026-10-07 — Proposed, not changed (crawler/ needs approval): `crawler/normalize.py` `gtin14()` keys 8-digit codes as zero-padded EAN-8 and rejects codes whose EAN-8 check fails, so an Open Food Facts product recorded as a UPC-E (number system 0/1) is dropped by identify.py or keyed differently from the app's UPC-A expansion. Proposal: when 8 digits start with 0/1 and the UPC-E check validates, expand to the 12-digit UPC-A before zero-filling (the app already tries both keys, so no data is lost once the pipeline changes).
- 2026-10-07 — Cloudflare static assets: `not_found_handling = "404-page"` (a missing pack file must never come back as index.html with a 200), `_headers` keeps the immutable rule to `/db/:version/*` only, and the service worker precaches with `cache: "reload"` so a new build never captures a year-old vendor file from the HTTP cache.
- 2026-10-07 — First two `deploy-app` runs on main: run 1 died in the fixture builder (fixed in PR #2); run 2 built the 760k fixture and the pack (32.1 MB) and failed only at "Deploy to Cloudflare Workers" because the repository secrets CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID are not set yet. Decision: that step keeps failing loudly rather than skipping (a green run that deployed nothing would mislead), so deploy-app stays red until the two secrets exist. GitHub Actions moved to their Node 24 majors (checkout v5, setup-node v5, setup-python v6) so the Node 20 deprecation annotation stops appearing on every run. An hourly watch (a scheduled Claude routine) checks deploy-app and pipeline runs, open pull requests and the data-store state, pings David only when something needs him, and opens fix pull requests but never merges them.
- 2026-10-07 — First deploy is live on the fixture at `sfb-value.forgetraining.workers.dev` (Forgetraining Cloudflare account; deploy-app run 5 passed every step once the two secrets existed). Repository variable `LIVE_CHECK_URL` points at the pipeline Worker `https://sfb-valuation.forgetraining.workers.dev/`; the app strips the trailing slash, and the public price route answered a real barcode (Great Value corn, $1.22) from the deployed build. Verified externally: the shell renders and the 760k pack opens on a phone-size viewport, `db/current.json` serves `fixture-f0e541716b`, and a missing pack file returns 404 rather than the page. Target address is `value.strongsvillefoodbank.org` on the food bank's own Cloudflare account; the app Worker moves there once David has access (swap `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID`, add the custom domain), so nobody installs the workers.dev version: a PWA's offline data is tied to its origin and would not follow the move. The first full crawl started 2026-10-07 18:24 UTC (`plan=full`); the first snapshot waits for David's approval per the gates. Cleanup of stale entries in DECISIONS/PLAN/SCHEMA/README is on hold until David says so.
- 2026-10-07 — Approved (crawler pacing only): after a 429 the Walmart client still raises its request interval by 15% (capped at 5 s) and still backs off with the 45-minute per-run wait cap; new: after every 50 consecutive successful requests it eases the interval by 10%, never below the 1.25 s it started with, so one bad minute no longer slows the whole run. Data format and cursor logic untouched. Applies from the next chained pipeline run (each run checks out main when it starts); the run in progress keeps the old pacing.
- 2026-10-07 — Pre-rollout proposal list (David): take charge, implement, keep the remaining steps hands-off. Decisions per item:
  1 pacing recovery: done (PR #4 merged). 2 CI for crawler tests: accepted, `.github/workflows/tests.yml` runs the Python and app
  tests on every pull request and push to main, separate from `pipeline.yml` so a crawl resume is never gated on it. 3 repo hygiene:
  accepted, the nine committed `__pycache__` files are untracked. 4 resume every 30 min: accepted, schedule `17,47 * * * *` runs
  `plan=continue`; a "peek" step reads only the small JSON files (`state/run.json`, published manifest, `sizing.json`,
  `audit/latest.json`, candidate `gates.json`) through the GitHub API and stops before checking out the data branch when nothing is
  due. 5 keepalive: accepted, `keepalive.yml` re-enables the scheduled workflows through the API weekly and touches
  `.github/keepalive` when main has had no commit for 45 days (the bot pushes to data-store are not assumed to count).
  6 one Walmart budget: accepted as "one queue": every Walmart job runs inside the `pipeline` workflow (one run at a time by its
  concurrency group) and `continue` picks the next most important job: sizing (once) > crawl resume > build, gates and publish >
  weekly audit > identify/backfill. The live route keeps its 60 calls/min global cap. 7 alerts: accepted, a composite action opens
  or updates one GitHub issue per alert kind (label `pipeline-alert`) and closes it when the condition clears; keys: pipeline-failed,
  gates-hold, review-key-missing, audit-regression, stale-prices, throttled, deploy-failed, deploy-mismatch, tests-failed. The hourly
  Claude watch is retired; Claude Code stays for diagnosis and fixes. 8 automated acceptance: accepted; thresholds live in
  `data/gates.json` (department completeness within 30% of the sizing pass, 117/117 sentinels found and priced, live re-check of 500
  random items in 25 calls with ≥97% exact match (provisional), size parsed for ≥95% of Food rows, per-unit outliers <0.5%, plus the
  existing drift and count gates); a null threshold means measure-only. The 300-row sample review runs inside the pipeline through
  the Anthropic API (secret `ANTHROPIC_API_KEY`, model `SFB_REVIEW_MODEL`, default claude-sonnet-5-5) against
  `data/review-criteria.md`; without the key the snapshot holds and an alert names the secret (set
  `sample_review.required=false` to waive). `plan=approve` remains as David's manual override. 9 weekly audit: accepted,
  `audit_every_days=7`, same 500-item live re-check plus per-unit outlier recount, alert below 95% match. 10 price history: accepted
  from the first publish: `history/baseline-<run>.jsonl.gz` once, then `history/changes-<run>.jsonl.gz` per publish (changed, new and
  removed rows, promo flag, date) and `history/index.json`; format in `docs/HISTORY.md`; the valuation rule (current vs median of recent
  non-promo prices) is decided after 4–6 weeks of data. 11 volatility-based cadence and the `specialOffer` clearance test: deferred
  until 3–4 weekly refreshes exist; cadence lives in `data/schedule.json` so it is a one-line change. 12 store-level pricing request
  (Strongsville #2266): deferred; only David can submit it. 13 sizing pass: accepted, runs automatically at the start of the next
  `continue` run (one call per department, ~23) into `sizing.json`, refreshed every 30 days, and feeds the completeness gate and the
  app-tiering decision (16). 14 popular-barcode backfill and 15 brand-search pilot: deferred to before volunteers, lowest queue
  priority, evidence rule as written. 16 performance at real size: deferred until sizing is known. 17 update safeguards: accepted,
  price date shown, staleness banner amber at 14 days and red at 45 with "Update now", persistent storage requested on every platform,
  no Web Push. 18 deploy only on change: accepted, a pipeline-triggered deploy stops when the live `db/current.json` already serves the
  published version, and every deploy is verified against the live site. 19–21 simulated volunteers, drills, real devices: deferred to
  before volunteers. 22 rollback (last 3 snapshots, one tap): deferred; note that data-store history is squashed after each publish,
  so kept snapshots must be files, not commits. 23 data-branch size watch: deferred. 24 secret rotation: deferred to before rollout and
  requires David (GitHub PAT, ADMIN_TOKEN, Cloudflare token; update the GitHub secret and the environment network secret together).
  25 handoff (domain, account move, QR card, handoff doc): pending David's access to the food bank's Cloudflare account.
  Operating rule: Claude Code takes charge of this list and ships tested, adversarially reviewed changes without waiting;
  David's remaining decisions arrive as alert issues. Secrets, Cloudflare account changes, crawl scope and anything outside the
  list are still proposed first.
- 2026-10-07 — Proposal modifications (David), decided: (4) the 30-minute resume check stays, lower priority: a scheduled run queued
  behind an active crawl already resumes it right after a throttle pause, so the check only closes the case where a pause happens with
  nothing queued; it is cheap (state read only) so it is kept. (1b, high priority) 429 back-off consumed ~26 of the first 61 minutes of
  the first crawl (576 calls, 1544 s of throttle sleep), and the 50-success recovery cannot help while 429s keep breaking the streak.
  Decision: the client logs every request and throttle sleep with timestamps (data-store `throttle/<run>.events.jsonl`),
  `crawler/throttle.py` infers whether Walmart limits per second or per minute and at roughly what rate, and the next run paces just under
  it with a sliding-window cap (`state.pace.per_min`: 0.85× the inferred limit, raised 10% after a clean run, lowered 15% after a
  throttled one, clamped 6–48/min). Back-off, ceiling, wait cap and the recovery stay unchanged as the safety net; the cap is the
  lever on total crawl time. Also requested: a full repository clean-up (docs and files current, accurate, consistent) after the
  automation lands, as its own pull request.
- 2026-10-07 — Automation integrated (streams: pipeline orchestration, gates/audit/history/review, app/deploy, throttle). Decisions
  taken while integrating, each measured on the first real Food crawl (305,065 rows replayed through the new pipeline from the live
  `state/run.json`): (a) size_parse threshold set to 0.85 provisional, measured 0.879 (12% of Food names carry no size to parse);
  raising it waits for better size parsing. (b) per-unit price outliers measured 7.5% (packet sizes read as cartons, counts read as
  weights); rather than hold the first snapshot on a parsing problem, `process.build()` now drops the per-unit price of any row more
  than 10× off its category+unit median and flags it `unit_price_suspect` (19,617 rows), so the app and the equivalents table never
  see a nonsense per-unit price; the gate keeps measuring the raw share, measure-only (null threshold) until parsing improves, then
  David's 0.5% applies. (c) A hold caused by a transient failure (live check or review API down) is rechecked after 6 hours
  (`TRANSIENT_RETRY_HOURS`); a hold on data stands until the config changes. (d) Pacing recommendations: 429s costing under 2% of a
  run leave the cap alone; a clean run under 2 minutes of traffic recommends nothing; the inferred per-minute limit is the larger of
  the smallest plausible pre-429 count and the busiest clean minute, so three hiccups after a clean 48/min stretch no longer cut
  the cap to 6; the cap carries into the next run. (e) `identify/latest.json` is a marker written by the identify plan because
  git checkouts keep no file times. (f) A skipped audit (no eligible rows) is remembered in `audit/latest.json` so it waits a full
  period; an audit that errors writes nothing and simply retries at the next run. (g) The app asks for persistent storage after every
  successful load, at most once a day until granted, and again when the app is installed (Chrome decides silently and changes its
  answer with engagement). (h) deploy-app compares the live `current.json` with the published manifest before setting up node or
  checking out the data branch, so a no-op run costs seconds; alert issues are resolved only by a verified deploy or a confirmed
  no-op. (i) The alert action skips a comment when the body is unchanged and caps bodies at 60 KB. (j) Merge rule while a crawl
  runs: the suite carries the live state as a fixture (`tests/fixtures/run-live.json`) and a dry run replays the real data-store
  through the new pipeline before anything merges. Hourly watch retired once the alert path has run on GitHub.
- 2026-10-08 — Second adversarial review of the automation, all findings fixed before merging: (a) the monthly full crawl keyed off
  the last publish of any kind, so weekly core publishes would have kept the 15 non-core departments on their first prices forever;
  the manifest now records `full_published` and the full crawl is due 30 days after it (a simulated 120-day season starts a full
  crawl every 30 days). (b) A failed weekly audit is recorded in `audit/latest.json` and retried every 6 hours instead of every run;
  `[audit-failed]` opens at once on an HTTP 4xx (Walmart key revoked or rotated) and after 3 failed attempts otherwise, and the next
  successful audit closes it; this supersedes 2026-10-07 (f) for errors. (c) The keepalive commit, the tests.yml parse checks and the
  pipeline chain step no longer fail silently or drop alerts (exit status checked; chaining runs last and cannot fail the run).
  (d) The sample review starts with room for the model's thinking (12,000 tokens, one retry at 20,000) and finds the verdict even
  when the model quotes an example row object before it.
- 2026-10-08 — Review of the app update path and of pacing, all findings fixed before merging. App: the launch check for a newer
  snapshot never ran (it saw its own start-up as "busy"), so phones only updated on reconnect or a tap; it now runs on every
  launch (proven in a browser: the second launch installs the newer pack and drops the old one). Persistent storage is requested
  only under the once-a-day policy. Deploys: a pipeline-triggered deploy could cancel an app-code deploy and then close its
  alert, and verification only compared the data version. Every build now carries a build key (`build.json`: app code, repo
  build inputs, published snapshot and equivalents tree hashes); the skip and the verification both use it; deploys queue
  instead of cancelling; no fixture build runs after a pipeline run while nothing is published; an unreadable data-store API
  means "build", never "skip". The pack version is `<snapshot>-<hash>` so an equivalents refresh or a builder change ships as
  a new version instead of new bytes under an immutable URL. Pacing: a cap is no longer lowered on 429s it did not cause
  (they came after fewer requests than a clean minute and cost under 10%, e.g. an outage), on a single 429 or on a run under
  2 minutes; within a run a 429 lowers the cap 15% (floor 6) and 50 successes raise it 10% back towards the starting cap,
  because the 5 s interval ceiling alone cannot pace below 12/min; a 200 whose body is not JSON is retried like a 5xx
  instead of failing the run.
- 2026-10-08 — Crawl continuity (David): a run that ends rate limited now chains the next `continue` run exactly like a budget
  pause. It is safe: a run only ends "throttled" after waiting out the 45-minute back-off cap, so chained runs are spaced by
  Walmart's own limit. The 30-minute schedule stays as the backstop; it had not fired once in the 90 minutes after the merge,
  which left the crawl idle after the 15:28 pause.
- 2026-10-08 — Size parsing (David: sample unsized Food rows, add rules with tests, count each/count items as sized by their
  basis, rebuild from the raw pages, do not lower the gate). Measured by rebuilding the live crawl's raw pages (no re-crawl):
  Food 87.9% → 92.7% sized (265,465 parsed sizes, 8 sold by the pound, 4,728 sold each), Premium Beauty 82.9 → 87.0%,
  Beauty 51.8 → 61.1%, Personal Care 49.7 → 59.2%, Health and Medicine 33.4 → 41.9%. Rules: a count beside a stated pack is
  kept and a stated total is never multiplied again; feed abbreviations (Fz, Fo, Gm, Gr, Lt), fractions (1/2 oz, 4-1/4 oz,
  1/2 LT), "1#", word quantities ("Two Pounds"), and feed shorthands ("24. OZ", "16 Fl O", "1 Fl Dram"); "28.2ozx14" is the
  supplier case and Walmart prices one box ($3-8 measured), so it is read as the size only. Only when neither the name nor
  the size field states a weight or volume: count nouns (tea bags, bars, pods, packets, pieces, each), dozens, a bare
  Pint/Quart/Half Gallon, and "11.5z". Shade codes are not units ("7GM", "46 LT", "SPF 15 # 50"). Rows priced per piece with
  no net quantity (produce sold each, store-made cakes, gift baskets, flowers, cake toppers and candles, size field "EA") get
  the flag `sold_each`; their size stays empty and no per-unit price is invented. The size gate counts parsed sizes, rows
  sold by the pound and `sold_each` rows. Every already-parsed row that changed was reviewed (852 of 773,524; fractions,
  fl oz vs oz, "(0 pack)", double-counted "(20 Count)" packs and stated totals). The 95% target is not reachable from the
  feed's text: of the 21,351 Food rows still unsized, 2,605 are placeholder listings ("Merchandise", "coming soon",
  discontinued), about 3,100 are names cut at 40 characters, and about 11,300 state no quantity anywhere (including
  misfiled non-food such as pet beds and shoes). Gate raised to the measured floor: size_parse_min 0.85 → 0.92.
- 2026-10-08 — Anthropic API key (David set `ANTHROPIC_API_KEY`; sample_review.required stays true). A manual
  workflow, anthropic-key-check, calls GET /v1/models with the secret and reports only the HTTP status and pass/fail (the key
  and the response body are never printed; listing models is free, so it cannot see the credit balance). Review failures now
  name the fix: HTTP 401 (invalid or revoked key) and 403 (no permission) open `[review-key-invalid]`; 402 `billing_error`, or
  the 400 "credit balance is too low" some accounts get, opens `[review-credits]`. Both stay transient holds re-checked every
  6 hours, so the next re-check after the fix runs the review and publishes; publishing closes them.
- 2026-10-08 — Per-unit price outliers (David: fix the parse so the flag becomes rare, not suppress it). Rebuilt from the
  live crawl's raw pages: Food rows flagged unit_price_suspect 7.45% → 3.10% (19,788 → 8,242); all departments 14.3% →
  4.2%. Three root causes fixed: (a) nutrient grams read as the size ("10g Protein", "19g Protein Per Serving") are no
  longer sizes; (b) the pack is ambiguous in the feed's own wording ("Pop-Tarts 58.6 oz, 32 Count" is one box, "KIND 1.4oz,
  12 Count" is twelve bars; "(12 Cans) … 16 oz", "36/Carton", "15/12oz", "2016/Pallet", "(Pack of 12)" priced per unit):
  normalize records every pack reading the name supports and process.build keeps the default unless it is more than 10x
  off comparable items, then takes the reading that agrees with them and flags the row pack_resolved (11,435 rows; spot-
  checked); (c) comparable items were the whole snapshot category (spices at ~$4/oz next to 5 lb flour at ~$0.04/oz); they
  are now the most specific Walmart category path with at least 50 unit-priced rows in the same unit, falling back to its
  parents and then the category. What stays flagged in Food is mostly not a parse: names cut before the pack count, case or
  pallet prices, placeholder/test listings and Walmart price errors, and premium items in the catch-all "Pantry meal
  essentials" leaf. The unit_outliers gate stays measure-only; its threshold is David's call now that the share is ~3%.
- 2026-10-08 — The app is measured and screenshotted in WebKit as well as Chromium, because volunteers' iPhones run WebKit
  whatever the browser. `measure.mjs` and `shots.mjs` take `--browser chromium|webkit` (Chromium unchanged by default; WebKit
  uses the iPhone 14 profile and writes `webkit-` prefixed files). WebKit has no CPU throttling and no fake camera (both
  Chromium-only), so its camera-scan numbers are recorded as "not measurable on WebKit in CI" and the scanner screen's
  typed-barcode path is measured in both browsers instead. The manual `app-browsers` workflow runs both browsers on the full
  760k fixture and writes a comparison to the run summary that flags any metric where WebKit is more than 25% slower (and by at
  least 2 ms / 1 MB) or that failed. Chromium runs unthrottled there by default (`chromium_cpu = 1`), so the two browsers are
  compared at the same speed; ×4 remains the setting for the docs/perf budget numbers.
