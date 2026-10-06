# sfb-valuation

Offline donation-valuation PWA for Strongsville Emergency Food Bank. Volunteers type the product they're holding and get its current Walmart.com price, with no connectivity and no subscription.

- `pipeline/` — Cloudflare Worker that signs Walmart I/O Affiliate API requests and builds the item database.
- `data/` — category map and per-category item files (JSONL).
- `app/` — the PWA (not started).
- `docs/` — plan, decisions, schema, runbook. Start with `CLAUDE.md`.
