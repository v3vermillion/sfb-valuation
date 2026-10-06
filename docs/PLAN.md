# Plan

## Problem
Volunteers receiving donations estimate item values roughly. Paid barcode apps (~$100/mo) were too expensive. Donations can be anything except clothing.

## Solution
Fully offline PWA: local item DB in IndexedDB + fuzzy search bar. Volunteer types brand/flavor/size and gets the price. Nothing is written back.

## Phases
1. Auth: Walmart I/O Taxonomy test call succeeds from the pipeline Worker. DONE
2. Map 23 categories to Walmart taxonomy IDs (data/categories.json).
3. Pull Product Catalog per taxonomy ID (paginated) → data/items/<category>.jsonl. QA each category before merging.
4. Normalize: parse size/unit/pack from product names; fail loudly on unexpected API fields.
5. Build the PWA; ship DB as versioned compressed JSON via service worker.
6. Pilot: one real donation batch + 50-item spot-check vs. a physical Walmart shelf.
7. Quarterly refresh via Worker cron trigger.
8. Phase 2: other-store brands (Aldi, Giant Eagle, Meijer).

## App requirements
- Offline-first PWA, installed to home screen (iOS evicts storage for uninstalled sites after 7 days).
- Barcode scanner (camera, offline): GTIN lookup incl. UPC-E/EAN-13 normalization and retired UPCs.
- Store-printed price barcodes (prefix 2) decoded directly; PLU produce codes with weight/count entry.
- Non-Walmart barcodes → equivalent value from identify/equivalents (labeled, basis item shown).
- Typed search tolerant of abbreviations (GV, pb, oz/ounce, pk/ct); results show brand, variant, size, pack, price.
- Fallback: same type + size per-unit price, flagged. Never blank or unpriced.
- Live Walmart check for scanned items when online (Worker route, to be added).
- Show price source and date. DB shipped as versioned compressed file; updates when the manifest changes.
- About screen: Open Food Facts attribution (ODbL).

## Open questions (food bank)
- What happens to the price after lookup (running tally? receipt?)
- Shared tablet vs. personal phones
- Named owner to approve pricing policy
