# Plan

## Problem
Volunteers receiving donations estimate item values roughly. Paid barcode apps (~$100/mo) were too expensive. Donations can be anything except clothing.

## Solution
Fully offline PWA: local item DB in IndexedDB + fuzzy search bar. Volunteer types brand/flavor/size and gets the price. Nothing is written back.

## Phases
1. Auth: Walmart I/O Taxonomy test call succeeds from the pipeline Worker.
2. Map 23 categories to Walmart taxonomy IDs (data/categories.json).
3. Pull Product Catalog per taxonomy ID (paginated) → data/items/<category>.jsonl. QA each category before merging.
4. Normalize: parse size/unit/pack from product names; fail loudly on unexpected API fields.
5. Build the PWA; ship DB as versioned compressed JSON via service worker.
6. Pilot: one real donation batch + 50-item spot-check vs. a physical Walmart shelf.
7. Quarterly refresh via Worker cron trigger.
8. Phase 2: other-store brands (Aldi, Giant Eagle, Meijer).

## App requirements
- Fuzzy search tolerant of abbreviations (GV, pb, oz/ounce); rank brand match, then size.
- Fallbacks: nearest size by price-per-oz (flagged as estimate) → manual entry with category median.
- Per-lb items prompt for weight.
- Show price source and observed date.
- Install to home screen on iOS (Safari evicts storage for uninstalled sites after 7 days); re-download DB if missing.

## Open questions (food bank)
- What happens to the price after lookup (running tally? receipt?)
- Shared tablet vs. personal phones
- Named owner to approve pricing policy
