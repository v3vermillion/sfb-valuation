# CLAUDE.md — read this first

## What this is
Offline PWA for Strongsville Emergency Food Bank volunteers: scan or type the donated item, get the
exact item and its current price. Prices come from the Walmart I/O Affiliate API. Design: docs/WORKFLOW.md.

## Rules
- David approves every fix or change before it's applied: find and report, then wait.
- docs/DECISIONS.md is the source of truth; append a dated entry for every new decision.
- Never commit secrets. They live in GitHub Actions secrets, Cloudflare Worker secrets, and David's password manager.
- David works from a phone. Anything that must run goes through GitHub Actions or Cloudflare.

## "Continue" — what to do when David says continue
1. `gh workflow run pipeline.yml -f plan=status` and read the run summary, or read
   `data-store:state/run.json` (`git fetch origin data-store && git show origin/data-store:state/run.json`).
2. By state.status:
   - no run yet (state empty) → `gh workflow run pipeline.yml -f plan=full` (first full crawl).
   - `crawling` → `gh workflow run pipeline.yml -f plan=continue` (it also chains itself; check it isn't already running: `gh run list -w pipeline`).
   - `crawled` / `built` → `plan=continue` processes, checks gates, publishes.
   - `awaiting_approval` → show David `build/candidate/report.md` (sentinel misses, rejects, counts). Publish only after he says so: `plan=approve`.
   - `needs_review` → diagnose from the report; propose fixes (normalize rules, sentinel entries, scope); wait for approval.
   - `published` → nothing pending; report the manifest.
3. To crawl one department sooner, it's the same `continue`; order is set in data/categories.json.
4. Never edit published data by hand; change rules, rebuild, re-check.

## Commands (also runnable locally with WM_CONSUMER_ID / WM_PRIVATE_KEY set and SFB_STORE pointing at a data-store checkout)
- `python -m crawler.ci --plan continue|core|full|approve|identify|status`
- `python -m unittest discover tests`

## Layout
- crawler/ — wm.py (signed client, pacing), crawl.py (resumable), normalize.py (rules), process.py (snapshot),
  qa.py (gates/publish), identify.py (non-Walmart barcodes → equivalents), ci.py (orchestrator)
- data/categories.json — scope (departments), category rules, exclusions
- data/sentinels.json — items that must always be found and priced
- .github/workflows/pipeline.yml — schedules + manual runs
- pipeline/ — Cloudflare Worker (public /v1/price/<gtin> live check, token-gated test routes)
- app/ — PWA (public/ shell + workers, tools/ fixture + pack builder + measure, tests/); deploy-app.yml deploys it
- docs/ — PLAN, DECISIONS, SCHEMA, RUNBOOK, WORKFLOW
