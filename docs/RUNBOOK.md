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
Optional variable: WM_KEY_VERSION (default 1).

Run manually: Actions tab → pipeline → Run workflow → plan (continue | core | full | approve | identify | status).
Working data: branch `data-store` (state/, raw/, build/, identify/). Report for the latest build:
`data-store:build/candidate/report.md`. Published snapshot: `data-store:build/published/`.

## App (Cloudflare Workers static assets, deployed by GitHub Actions)
Code: `app/`. Workflow: `.github/workflows/deploy-app.yml` (runs on app changes, after every pipeline run, or manually).
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
The app checks `db/current.json` on each launch and downloads a new snapshot in the background.

Local: `cd app && npm run fixture && npm run build && npm run serve` → http://127.0.0.1:8787/.
Tests: `npm test`. Performance numbers: `npm run measure` (Playwright, 4× CPU throttle; add `--video barcode.y4m`
for a fake camera). Screenshots: `npm run shots`.

### Rate limit bindings for the live check
`pipeline/wrangler.toml` declares two `[[ratelimits]]` bindings (PRICE_LIMITER per IP, PRICE_GLOBAL_LIMITER for
the whole key). On the first deploy after this change Cloudflare creates them automatically; nothing to configure
in the dashboard. `namespace_id` only has to be unique within the account. `/health` reports whether both are bound;
without them the public route answers 503 instead of spending the Walmart key without a cap.
