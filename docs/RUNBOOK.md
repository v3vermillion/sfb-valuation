# Runbook

## Walmart I/O auth
Each request carries four headers:
- WM_CONSUMER.ID
- WM_CONSUMER.INTIMESTAMP — epoch milliseconds
- WM_SEC.KEY_VERSION
- WM_SEC.AUTH_SIGNATURE — base64 RSA-SHA256 (PKCS#1 v1.5) signature of `consumerId\ntimestamp\nkeyVersion\n`

Public key format accepted by the portal: base64 body only (no BEGIN/END lines).

## Deploying the pipeline Worker (phone-only)
1. Cloudflare → Workers & Pages → Create → Continue with GitHub → select v3vermillion/sfb-valuation.
2. Root directory: `pipeline`. Deploy command: `npx wrangler deploy` (default).
3. Worker → Settings → Variables and Secrets → add (type Secret):
   - WM_PRIVATE_KEY — full PEM from password manager (BEGIN/END lines included)
   - WM_CONSUMER_ID — Prod Consumer ID from walmart.io
   - ADMIN_TOKEN — any long random string; required on every request
   WM_KEY_VERSION=1 is set in wrangler.toml.
4. Redeploy (or push any commit) so secrets apply.

## Endpoints
- GET /v1/price/<gtin> — PUBLIC (no token): live Walmart price for the app, the Strongsville store's own price
  (`STORE_ID` in wrangler.toml; `priceSource` "store"). Rate limited 30/min per IP and
  20 Walmart calls/min in total (`[[ratelimits]]` bindings PRICE_LIMITER and PRICE_GLOBAL_LIMITER in
  wrangler.toml; charged only on a cache miss), 6 h edge cache per GTIN, CORS GET only.
  Returns `{ok:true, price, name, brand, upc, stock, listings[], checkedAt}` or `{ok:false, reason}`;
  429 when limited, 503 (`retry-after`) when Walmart throttles/fails or the bindings are missing.
  Local dev without bindings: set `ALLOW_UNLIMITED_DEV=1` in `.dev.vars` (never in production).
- GET /health?token=ADMIN_TOKEN — config check, never prints secret values
- GET /taxonomy?token=ADMIN_TOKEN — signed Walmart Taxonomy call; top-level departments
- GET /taxonomy/<id>?token=ADMIN_TOKEN — children of one category node
- GET /items/<id>?token=ADMIN_TOKEN&pages=N&raw=1 — test pull of product catalog for a node (read-only)
- GET /search?token=ADMIN_TOKEN&q=TEXT[&category=ID] — coverage spot-check

## Rotating keys
Generate new pair → upload public key on walmart.io (key version increments) → update WM_PRIVATE_KEY and WM_KEY_VERSION.

## Data pipeline (GitHub Actions)
Required repository secrets (Settings → Secrets and variables → Actions):
- WM_PRIVATE_KEY — full PEM from the password manager
- WM_CONSUMER_ID — Prod Consumer ID
- ANTHROPIC_API_KEY — used only by the 300-row sample review before a publish (console.anthropic.com → API keys).
  Without it a finished snapshot holds and the `[review-key-invalid]` (the review API call was rejected: 401 invalid or revoked key, or 403 no permission -> replace the secret), `[review-credits]` (out of Anthropic credits -> add credits; auto-reload is off), `[review-key-missing]` issue says so; `sample_review.required=false` in
  `data/gates.json` waives the review.
Optional variables: WM_KEY_VERSION (default 1), SFB_REVIEW_MODEL (default claude-sonnet-5-5).

### How it runs
`pipeline.yml` runs `plan=continue` at 17 and 47 past every hour. A peek step reads only `state/run.json`, the published
manifest, `sizing.json`, `audit/latest.json` and the candidate `gates.json` through the GitHub API and ends the run when nothing
is due (no data-branch checkout). Otherwise `crawler/ci.py` runs ONE Walmart job per run, in this order: sizing pass (one call per
department, every 30 days) > crawl resume (300-minute budget, then chains `continue`) > build + gates + publish > weekly live
audit > identify refresh. Only one run executes at a time (concurrency group `pipeline`); a crawl paused by Walmart 429s (after the
45-minute back-off cap) chains the next run too, so the crawl never waits on the schedule, which stays as the backstop. Cadence: `data/schedule.json` (full_every_days 30, core_every_days 7, audit_every_days 7,
identify_every_days 30, sizing_every_days 30, stale_days 14, budget_min 300).

### Acceptance gates (`data/gates.json`; a null threshold = measure only)
departments_complete (every department done, kept > 0, pages within 30% of `sizing.json`), sentinels (every one of data/sentinels.json found and priced; 116 since Auto & Tires left the crawl),
live_match (500 random items re-checked live in 25 calls, ≥ 97% exact), size_parse (≥ 92% of Food rows sized: a parsed size, sold by the pound, or sold each; 92.7% measured 2026-10-08),
unit_outliers (< 0.5% of unit-priced rows outside 10× of their category median), the existing drift and count gates, and
sample_review (300 random rows judged against `data/review-criteria.md`; systematic junk or > 5% junk holds). All pass → publish;
otherwise hold + `[gates-hold]` issue with the report. `plan=approve` publishes a held candidate after the owner has read the report.
Editing `data/gates.json`, `data/sentinels.json` or `data/categories.json` makes the next run re-evaluate a held candidate.

### Alerts (GitHub issues, label `pipeline-alert`)
One open issue per kind, updated in place, closed automatically when the condition clears: `[pipeline-failed]`, `[gates-hold]`,
`[review-key-missing]`, `[audit-regression]`, `[audit-failed]` (the audit could not reach Walmart: a 401/403 means the WM_* secrets no longer match), `[data-store-size]` (the files on the data-store branch passed 1 GB; the issue carries the breakdown and the proposal to move raw pages to Cloudflare R2), `[snapshot-archive]` (a publish could not be kept as a GitHub Release; the publish itself stands and the next one retries), `[stale-prices]` (no publish for stale_days while idle), `[throttled]`
(three consecutive runs ended on Walmart throttling), `[crawl-truncated]` (a department or child node ended far short of
Walmart's page count or its id was refused; see "Crawl scope edits" below), `[deploy-failed]`, `[deploy-mismatch]`, `[tests-failed]`.
Watch the repository (or just the issues) on the GitHub app for phone notifications.

### Pacing (`state.pace`, data-store `throttle/`)
Every request and every 429 sleep is logged to `throttle/<run>.events.jsonl`; at the end of each crawl invocation
`crawler/throttle.py` infers whether Walmart limits per second or per minute and at what rate, writes
`throttle/<run>.analysis.json`, and sets `state.pace = {per_min, inferred, updated, run_id}`: the next run paces under that cap
(0.85× the inferred limit after 3+ 429s; +10% after a clean run; −15% after a costly one; unchanged when 429s cost under 2%;
clamped 6–48/min on top of the 1.25 s floor). A cap is never lowered on a single 429, on a run under 2 minutes, or on 429s that
came after fewer requests than a clean minute (an outage, not the cap) costing under 10%. Within a run, each 429 also lowers the
cap 15% (not below 6) and every 50 successes raise it 10% back towards the starting cap. The job summary prints one pace line per crawl.
Read a log by hand: `python -m crawler.throttle store/throttle/<run>.events.jsonl --cap <per_min>`.

### Holds and retries
A held candidate stands until `data/gates.json`, `data/sentinels.json` or `data/categories.json` changes (the candidate's
`gates.json` carries their hash). A hold marked `transient` (live check or review API unavailable) is rechecked after 6 hours.
`peek` prints `work=inspect` when `state/run.json` is unreadable so the full job runs and fails loudly. The pipeline-failed issue
is resolved only by a run whose Run step succeeded (a peek-only run clears nothing). Alerts from Finish win over Run over peek.
`identify/latest.json` is a marker written by the identify plan (git keeps no file times). A skipped audit (no eligible rows) is
remembered in `audit/latest.json` and waits a full period; an audit that errored writes nothing and retries next run.
Rows whose per-unit price is more than 10× off their category+unit median keep their item price but lose the per-unit price
and carry the flag `unit_price_suspect`; the `unit_outliers` gate reports the raw share (measure-only until parsing improves).

### Schedule
The schedule fires, though GitHub delays and drops scheduled runs, so they come hours apart rather than every 30 minutes. A
scheduled run that arrives while a crawl is running waits in the `pipeline` concurrency group and is cancelled when the crawl's
chained run takes its place (cancelled runs with 0 jobs in the Actions tab): by design. If a run ends with nothing chained and
no scheduled run follows within a few hours, start `plan=continue` from the Actions tab.

### Store prices (Strongsville, store #2266)
`data/store.json` names the store. After a publish, when no crawl, build, audit or identify is due, `decide()` runs the
`store` job: `crawler/storeprice.py refresh` asks Walmart for the store's own price and stock of every barcode row of the
snapshot, 20 per call, consumable departments first and the oldest check first, within the crawl budget, and chains the
next run while rows remain (`store_prices/2266.jsonl.gz`, `store_prices/latest.json`). The next build shows the store
price of every row checked within `max_age_days` (21), keeps Walmart.com's in `online_price`, and flags it `store_price`;
the app labels it "Strongsville Walmart shelf price". The live_match gate and the weekly audit compare store-priced rows
with the store's live price. Manual: Actions → pipeline → plan `store`. At about 8 calls a minute a pass over a million
rows takes several days of pipeline time; consumable departments come first so food and household items are covered
soonest. `store-price-probe.yml` (manual, read-only) re-checks which store id the API returns near a ZIP code.

### Search gold set
`data/gold-search.json` holds 330 queries as volunteers type them, each with the words the right item must contain (and a
size when the query states one). deploy-app runs `app/tools/gold.mjs` on every real pack (not the fixture): the summary
lists every miss with the top 3 found; below 95% opens `[search-gold]`, below 90% the step fails and the live site keeps
the previous build. Locally: `node --max-old-space-size=6144 app/tools/gold.mjs --db app/dist/db`. When a volunteer
reports a wrong result, add it as a query first, then fix the ranking (app/public/js/db-worker.js) until it passes.

### Crawl scope edits, split departments, early ends
An edit of `data/categories.json` applies to the crawl in progress (`crawl.sync`, printed as `scope:` lines in the run log):
a department removed from `departments` is `dropped`; one given a `split` (a list of Walmart child node ids) is re-crawled
as those nodes, each with its own cursor, under `raw/<run>/<dept>/<node>/`; other finished departments are untouched.
Sizing covers each node and records the department as their sum. Walmart has ended department listings early (Home stopped
at page 1,830 of 31,781): an end with many hits left is retried from the next cursor, and a crawl that still ends short of
(1 − `dept_size_tolerance`) of Walmart's page count is `truncated`; a category id Walmart refuses is `failed`. Both open
`[crawl-truncated]` and hold the snapshot at the departments_complete gate; fix the scope in `data/categories.json`.

### Other automation
- `keepalive.yml` (weekly): re-enables the scheduled workflows through the API and touches `.github/keepalive` when main has
  had no commit for 45 days, so GitHub never disables the schedules after 60 quiet days.
- `tests.yml`: Python and app unit tests on every pull request and push to main; failures on main open `[tests-failed]`.
- Price history: `data-store:history/` (`baseline-<run>.jsonl.gz`, `changes-<run>.jsonl.gz`, `index.json`); see docs/HISTORY.md.
- Weekly audit results: `data-store:audit/<date>.json` and `audit/latest.json`.
- Department sizes: `data-store:sizing.json`.
- Merge rule while a crawl runs: `tests/fixtures/run-live.json` (the live state) must resume through `decide()` and `continue`
  in the suite, and the scratch dry run must replay a copy of the real data-store through the new code without an exception.

Run manually: Actions tab → pipeline → Run workflow → plan (continue | core | full | approve | identify | audit | size | status | rollback | store).
Working data: branch `data-store` (state/, raw/, build/, identify/, history/, audit/, sizing.json). Report for the latest build:
`data-store:build/candidate/report.md`. Published snapshot: `data-store:build/published/`.

## App (Cloudflare Workers static assets, deployed by GitHub Actions)
Code: `app/`. Workflow: `.github/workflows/deploy-app.yml` (runs on app changes, after every pipeline run, or manually).
Every build carries a build key in `$APP_URL/build.json` (a hash of the app code, the repo's build inputs, the published
snapshot and the equivalents table). After a pipeline run it deploys only when that key differs from the live one, and every
deploy is verified by polling `build.json` and `db/current.json` for the new build; mismatches open `[deploy-mismatch]`,
failures `[deploy-failed]`. Deploys queue rather than cancel each other. The pack version is `<snapshot>-<hash>`, so an
equivalents refresh or a builder change reaches phones as a new version.
Optional repository variable: APP_URL — the app's address (default `https://sfb-value.forgetraining.workers.dev`); change it
when the Worker moves to the food bank's account and custom domain.
Required repository secrets (Settings → Secrets and variables → Actions):
- CLOUDFLARE_API_TOKEN — API token with "Workers Scripts: Edit" (Cloudflare dashboard → My Profile → API Tokens → Edit Cloudflare Workers template)
- CLOUDFLARE_ACCOUNT_ID — Workers & Pages → Overview → Account ID
Optional repository variable: LIVE_CHECK_URL — the pipeline Worker URL (e.g. `https://sfb-valuation.<account>.workers.dev`).
Without it the app hides the live check and says "Not configured" in Settings.

Data source: the published snapshot on `data-store` (`build/published/items.jsonl.gz` + `identify/equivalents.jsonl.gz`).
If none is published yet the workflow builds the synthetic 760k fixture and the app shows "sample data".
Manual run: Actions → deploy-app → Run workflow → data = auto | fixture | snapshot, deploy = true/false.

After the first deploy the app is at `https://sfb-value.<account>.workers.dev` (rename or add a custom domain in the
Cloudflare dashboard). Volunteers open it once online and "Add to Home Screen"; everything then works offline.
The app checks `db/current.json` on each launch and downloads a new snapshot in the background. It shows the price date,
turns the banner amber after 14 days without new prices and red after 45, with an "Update now" button; it asks the browser for
persistent storage on every platform. There is no Web Push (iOS cannot refresh data in the background from a push).

Local: `cd app && npm run fixture && npm run build && npm run serve` → http://127.0.0.1:8787/.
Tests: `npm test`. Performance numbers: `npm run measure` (Playwright, 4× CPU throttle; add `--video build/barcode.y4m`
for a fake camera, made by `node tools/make-barcode-clip.mjs`). Screenshots: `npm run shots`. Both take `--browser webkit`
(iPhone's engine). From the phone: Actions → app-browsers → Run workflow compares Chromium and WebKit on the 760k fixture
(summary table plus screenshot artifacts; nothing is deployed).

### Rate limit bindings for the live check
`pipeline/wrangler.toml` declares two `[[ratelimits]]` bindings (PRICE_LIMITER per IP, PRICE_GLOBAL_LIMITER for
the whole key). On the first deploy after this change Cloudflare creates them automatically; nothing to configure
in the dashboard. `namespace_id` only has to be unique within the account. `/health` reports whether both are bound;
without them the public route answers 503 instead of spending the Walmart key without a cap.

### Rollback (last three published snapshots)
Every publish uploads `build/published/*` (shards as they are) to a GitHub Release tagged `snapshot-<version>` (not marked
latest) and deletes all but the newest three (`crawler/releases.py`). To put an earlier one back from a phone: Actions →
pipeline → Run workflow → plan `rollback`, `rollback_to` = `previous` (the newest kept snapshot that is not live; run it
again to go forward) or a version from the repo's Releases page. The run downloads it, checks the manifest and that every
item reads back, replaces `data-store:build/published/` (manifest gains `rolled_back` {from, to, at}) and pushes; deploy-app
then ships it, and phones treat any live version other than their own as an update (older or newer), so it arrives through
the normal "Update now" banner. The crawl state and any candidate are untouched. After a rollback, new crawls (start-core /
start-full) wait `core_every_days` so the restored prices stay live while the cause is fixed; a crawl already running
continues, and its publish would replace the rollback, so fix the cause (rules, thresholds) first or run plan=core/full when
ready. A refused rollback (unknown version, incomplete download) changes nothing.

### Data-store size (GitHub limits)
GitHub rejects any pushed file over 100 MB and warns over 50 MB. `store.write_jsonl_gz` writes any `.jsonl.gz` whose
compressed size passes 45 MB as shards `<name>.s000`, `<name>.s001`, ... (each a complete gzip stream; concatenated they
are one valid stream), and every reader (`store.iter_jsonl_gz`, `app/tools/build-db.mjs`) accepts either form. The first
real snapshot (773k items) is already 57 MB, so it is sharded from the first publish. `store.checkpoint` refuses to commit
or push when any file passes 95 MB and names it. Every pipeline run prints the branch size by top-level folder in its
summary and opens `[data-store-size]` past 1 GB.

