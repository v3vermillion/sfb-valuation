# Data workflow

Goal: the volunteer scans or types the item in their hand and gets the exact item and its current
price, offline, never a blank. Everything below serves that.

## Architecture
- **Crawler + processing: GitHub Actions** (`.github/workflows/pipeline.yml`, code in `crawler/`).
  Runs for hours, no CPU/DB limits, $0. Working data lives on the `data-store` branch.
- **Live check: Cloudflare Worker** (`pipeline/`). Signs Walmart requests; the app calls it only when online.
- **App: offline PWA** (`app/`, see `app/README.md`). Local database + barcode camera scanner, both offline;
  deployed to Cloudflare Workers static assets by `.github/workflows/deploy-app.yml`.

## Pipeline (automatic)
1. **Crawl** every in-scope Walmart department (`data/categories.json`), every page, `soldByWmt=true`
   (removes third-party sellers whose prices run 5–10x). Cursor saved after every page; a run that hits
   the time budget re-launches itself; a run paused by rate limiting resumes on the 12-hour schedule.
2. **Normalize** (`crawler/normalize.py`, unit-tested): size/pack from the product name (Walmart's size
   field is unreliable), variant words (diet, zero, whole grain...), per-unit price, category, UPC as
   GTIN-14. Rejects: third-party, no price, misfiled media (books/CDs in food), alcohol, clothing.
   Retired UPCs ("deleted_") are KEPT and flagged — donors give old stock.
3. **Promo guard:** clearance/flash/limited-deal prices keep the last normal price.
4. **Quality gates** (`crawler/qa.py`): crawl complete; every sentinel in `data/sentinels.json` found
   with a price; item count not down >10%; category counts within ±20%; ≤2% of prices moved >50%.
   Fail → previous snapshot stays live + report. First snapshot → waits for `approve`.
5. **Publish** → `data-store:build/published/` (items.jsonl.gz + manifest.json). Branch history is
   compacted after each publish so the repo never grows.
6. **Identify + equivalents** (`crawler/identify.py`, monthly): Open Food/Beauty/Products Facts US
   barcodes → product name/brand/size for items Walmart doesn't sell, matched to the closest Walmart item
   for an equivalent price with a confidence level.

## Schedule
- Monthly (1st): full crawl of all departments + identification refresh.
- Weekly (Mon): core departments re-priced (Food, Health, Pharmacy, Personal Care, Beauty, Baby, Pets,
  Household). Non-core items carry over until the monthly run.
- Every 12h: resume anything unfinished. Nothing to do = exits in about a minute.
- Live: when the phone is online, a scanned barcode is also checked against Walmart in real time.
Rationale: Walmart shelf prices change in steps, not daily; weekly keeps food within a week of
current, and the live check covers the moment of donation whenever there's signal.

## How the app resolves an item (decision 2026-10-06, see DECISIONS.md)
Built from a year-in-the-sorting-room view of what actually shows up on the table:
1. **Barcode → exact Walmart item** (including retired UPCs and single cans from multipacks).
2. **Store-printed barcodes** (meat, deli, bakery labels starting with 2) carry the price in the
   barcode itself → decoded directly. Produce stickers (PLU 4011 etc.) → item + per-lb/each price.
3. **Barcode Walmart doesn't sell** (Aldi, Giant Eagle, Marc's, Meijer, Target, Dollar General,
   Kirkland, regional brands) → identified offline, priced at the closest Walmart equivalent,
   labeled "equivalent value" with the basis item shown.
4. **Typed search** → results show brand, variant, size, pack, price; volunteer taps the exact one.
5. **Last resort** (no barcode, no match): same product type at the same size, per-unit, flagged.
   Never blank, never unpriced.
Used electronics/jewelry show the new retail price; whether to adjust for used items is food-bank policy.

## Minutes budget
GitHub gives private repos 2,000 Actions minutes/month. Measure after the first full crawl
(report shows calls); if it's tight, make the repo public (unlimited minutes; secrets stay secret)
or move the weekly refresh to every two weeks.
