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
- GET /v1/price/<gtin> — PUBLIC (no token): live Walmart price for the app. Rate limited 30/min per IP and
  60 Walmart calls/min in total (`[[ratelimits]]` bindings PRICE_LIMITER and PRICE_GLOBAL_LIMITER in
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
  Without it a finished snapshot holds and the `[review-key-missing]` issue says so; `sample_review.required=false` in
  `data/gates.json` waives the review.
Optional variables: WM_KEY_VERSION (default 1), SFB_REVIEW_MODEL (default claude-sonnet-5-5).

### How it runs
`pipeline.yml` runs `plan=continue` at 17 and 47 past every hour. A peek step reads only `state/run.json`, the published
manifest, `sizing.json`, `audit/latest.json` and the candidate `gates.json` through the GitHub API and ends the run when nothing
is due (no data-branch checkout). Otherwise `crawler/ci.py` runs ONE Walmart job per run, in this order: sizing pass (one call per
department, every 30 days) > crawl resume (300-minute budget, then chains `continue`) > build + gates + publish > weekly live
audit > identify refresh. Only one run executes at a time (concurrency group `pipeline`); a crawl paused by Walmart 429s simply
resumes at the next half hour. Cadence: `data/schedule.json` (full_every_days 30, core_every_days 7, audit_every_days 7,
identify_every_days 30, sizing_every_days 30, stale_days 14, budget_min 300).

### Acceptance gates (`data/gates.json`; a null threshold = measure only)
departments_complete (every department done, kept > 0, pages within 30% of `sizing.json`), sentinels (117/117 found and priced),
live_match (500 random items re-checked live in 25 calls, ≥ 97% exact), size_parse (≥ 95% of Food rows carry a parsed size),
unit_outliers (< 0.5% of unit-priced rows outside 10× of their category median), the existing drift and count gates, and
sample_review (300 random rows judged against `data/review-criteria.md`; systematic junk or > 5% junk holds). All pass → publish;
otherwise hold + `[gates-hold]` issue with the report. `plan=approve` publishes a held candidate after David has read the report.
Editing `data/gates.json`, `data/sentinels.json` or `data/categories.json` makes the next run re-evaluate a held candidate.

### Alerts (GitHub issues, label `pipeline-alert`)
One open issue per kind, updated in place, closed automatically when the condition clears: `[pipeline-failed]`, `[gates-hold]`,
`[review-key-missing]`, `[audit-regression]`, `[stale-prices]` (no publish for stale_days while idle), `[throttled]`
(three consecutive runs ended on Walmart throttling), `[deploy-failed]`, `[deploy-mismatch]`, `[tests-failed]`.
Watch the repository (or just the issues) on the GitHub app for phone notifications.

### Other automation
- `keepalive.yml` (weekly): re-enables the scheduled workflows through the API and touches `.github/keepalive` when main has
  had no commit for 45 days, so GitHub never disables the schedules after 60 quiet days.
- `tests.yml`: Python and app unit tests on every pull request and push to main; failures on main open `[tests-failed]`.
- Price history: `data-store:history/` (`baseline-<run>.jsonl.gz`, `changes-<run>.jsonl.gz`, `index.json`); see docs/HISTORY.md.
- Weekly audit results: `data-store:audit/<date>.json` and `audit/latest.json`.
- Department sizes: `data-store:sizing.json`.

Run manually: Actions tab → pipeline → Run workflow → plan (continue | core | full | approve | identify | audit | size | status).
Working data: branch `data-store` (state/, raw/, build/, identify/, history/, audit/, sizing.json). Report for the latest build:
`data-store:build/candidate/report.md`. Published snapshot: `data-store:build/published/`.

## App (Cloudflare Workers static assets, deployed by GitHub Actions)
Code: `app/`. Workflow: `.github/workflows/deploy-app.yml` (runs on app changes, after every pipeline run, or manually).
After a pipeline run it deploys only when the published version differs from what the live site serves (`$APP_URL/db/current.json`),
and every deploy is verified against the live site; mismatches open `[deploy-mismatch]`, failures `[deploy-failed]`.
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
Tests: `npm test`. Performance numbers: `npm run measure` (Playwright, 4× CPU throttle; add `--video barcode.y4m`
for a fake camera). Screenshots: `npm run shots`.

### Rate limit bindings for the live check
`pipeline/wrangler.toml` declares two `[[ratelimits]]` bindings (PRICE_LIMITER per IP, PRICE_GLOBAL_LIMITER for
the whole key). On the first deploy after this change Cloudflare creates them automatically; nothing to configure
in the dashboard. `namespace_id` only has to be unique within the account. `/health` reports whether both are bound;
without them the public route answers 503 instead of spending the Walmart key without a cap.
