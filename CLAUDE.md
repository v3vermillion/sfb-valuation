# CLAUDE.md — read this first

## What this is
Offline PWA for Strongsville Emergency Food Bank volunteers to look up the price of donated items. Data source: Walmart I/O Affiliate API. Prices = Walmart.com online regular price (not sale, first-party seller only).

## Rules
- The owner (David) approves every fix or change before it is applied: find and report, then wait.
- docs/DECISIONS.md is the source of truth. If anything conflicts, DECISIONS.md wins. Append a dated entry for every new decision.
- Never commit secrets. Secrets live only in Cloudflare Worker secrets and David's password manager.
- The owner works from a phone only. Anything that must run goes through Cloudflare (Git-connected Worker builds) or GitHub — never "run this locally".

## Layout
- docs/PLAN.md — scope, phases, app requirements
- docs/DECISIONS.md — dated decision log
- docs/SCHEMA.md — item row schema
- docs/RUNBOOK.md — setup, secrets, deploy, refresh
- pipeline/ — Cloudflare Worker (wrangler.toml, src/index.js)
- data/categories.json — 23 pipeline categories ↔ Walmart taxonomy IDs
- data/items/ — one JSONL per category
- app/ — PWA (not started)

## Current status
See the latest entries in docs/DECISIONS.md.
