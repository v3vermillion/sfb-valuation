# CLAUDE.md — read this first

## What this is
Offline PWA for Strongsville Emergency Food Bank volunteers: scan or type the donated item, get the
exact item and its current price. Prices come from the Walmart I/O Affiliate API. Design: docs/WORKFLOW.md.

## Rules
- Since 2026-10-07 Claude Code owns the pre-rollout automation (docs/DECISIONS.md, that date): it ships tested, reviewed
  changes without waiting, and David's decisions arrive as `pipeline-alert` issues. Still proposed first, never done unilaterally:
  anything touching secrets or the Cloudflare account, crawl scope, and work outside that list.
- docs/DECISIONS.md is the source of truth; append a dated entry for every new decision.
- Never commit secrets. They live in GitHub Actions secrets, Cloudflare Worker secrets, and David's password manager.
- David works from a phone. Anything that must run goes through GitHub Actions or Cloudflare.

## How the pipeline runs itself (since 2026-10-07)
Nothing waits for a human. `.github/workflows/pipeline.yml` runs `plan=continue` every 30 minutes (17 and 47 past the hour):
a cheap peek reads `state/run.json`, the published manifest, `sizing.json`, `audit/latest.json` and the candidate `gates.json`
through the GitHub API and stops when nothing is due. Otherwise `crawler/ci.py` picks ONE Walmart job per run, in priority order:
sizing pass (once per 30 days) > crawl resume > build + gates + publish > weekly live audit > identify refresh. Cadence lives in
`data/schedule.json`; gate thresholds in `data/gates.json`; the 300-row sample review uses the `ANTHROPIC_API_KEY` secret.
A snapshot publishes only when every gate passes; otherwise it holds and an issue is opened.

## What David decides (everything else is automatic)
- An open issue labelled `pipeline-alert` is the to-do list: `[gates-hold]` (read the report in the issue; fix rules or thresholds,
  or run `plan=approve` to override), `[review-key-missing]` (add the `ANTHROPIC_API_KEY` secret or set
  `sample_review.required=false` in data/gates.json), `[pipeline-failed]`, `[deploy-failed]`, `[deploy-mismatch]`,
  `[audit-regression]`, `[audit-failed]`, `[stale-prices]`, `[throttled]`, `[tests-failed]`. Issues close themselves when the condition clears.
- Changing scope or rules: edit `data/categories.json`, `data/sentinels.json`, `data/gates.json`, `data/schedule.json`;
  the next run re-evaluates a held candidate automatically when those files change.
- When Claude Code is asked to look: read the open alert issues and `data-store:build/candidate/report.md`, diagnose, propose fixes
  (never edit published data by hand; change rules, rebuild, re-check). Manual plans still work from the Actions tab:
  continue | full | core | approve | identify | audit | size | status.

## Commands (also runnable locally with WM_CONSUMER_ID / WM_PRIVATE_KEY set and SFB_STORE pointing at a data-store checkout)
- `python -m crawler.ci --plan continue|core|full|approve|identify|audit|size|status|peek|finish`
- `python -m unittest discover tests` (201 tests; `tests/fixtures/run-live.json` is the live crawl state the pipeline must resume from)
- `cd app && node --test tests/*.test.mjs`

## Layout
- crawler/ — wm.py (signed client, pacing), crawl.py (resumable), normalize.py (rules), process.py (snapshot),
  qa.py (gates/publish), audit.py (weekly live audit), history.py (price history), review.py (sample review),
  sizing.py (department sizes), throttle.py (429 analysis, pace cap), identify.py (non-Walmart barcodes → equivalents), ci.py (orchestrator + decide())
- data/categories.json — scope (departments), category rules, exclusions
- data/sentinels.json — items that must always be found and priced
- data/gates.json — acceptance thresholds (null = measure only); data/schedule.json — cadence; data/review-criteria.md — sample review rules
- .github/workflows/ — pipeline.yml (30-min continue, manual plans), deploy-app.yml, tests.yml, keepalive.yml; actions/alert (issue alerts)
- pipeline/ — Cloudflare Worker (public /v1/price/<gtin> live check, token-gated test routes)
- app/ — PWA (public/ shell + workers, tools/ fixture + pack builder + measure, tests/); deploy-app.yml deploys it
- docs/ — PLAN, DECISIONS, SCHEMA, RUNBOOK, WORKFLOW
