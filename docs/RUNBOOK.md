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
- GET /health?token=ADMIN_TOKEN — config check, never prints secret values
- GET /taxonomy?token=ADMIN_TOKEN — signed Walmart Taxonomy call; top-level departments
- GET /taxonomy/<id>?token=ADMIN_TOKEN — children of one category node
- GET /items/<id>?token=ADMIN_TOKEN&pages=N&raw=1 — test pull of product catalog for a node (read-only)
- GET /search?token=ADMIN_TOKEN&q=TEXT[&category=ID] — coverage spot-check

## Rotating keys
Generate new pair → upload public key on walmart.io (key version increments) → update WM_PRIVATE_KEY and WM_KEY_VERSION.
