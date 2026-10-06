# Decisions (dated, newest last — this file wins on conflict)

- 2026-10-05 — Fully offline PWA with search bar; no barcode wizard, no online/vision path (would recreate subscription cost).
- 2026-10-05 — Walmart is the primary price reference. Regular price only, first-party seller only. Clothing excluded.
- 2026-10-05 — 23 categories exist for the data pipeline only, not app UX. Brand and size are row attributes.
- 2026-10-06 — Scraping abandoned: Walmart blocks datacenter IPs (browser-bridge test failed). Data source is Walmart I/O Affiliate API.
- 2026-10-06 — Prices are Walmart.com online prices; store pinning to Strongsville not required.
- 2026-10-06 — Walmart I/O app "SFB-Donation-Valuation" created; public key uploaded (body-only format accepted), Production, key version 1.
- 2026-10-06 — Repo created (private). Pipeline Worker deploys from GitHub via Cloudflare Git integration (owner is phone-only).
- 2026-10-06 — Taxonomy auth test passed (HTTP 200, 51 top-level departments). Relevant departments: Food 976759, Health and Medicine 976760, Personal Care 1005862, Beauty 1085666, Baby 5427, Pets 5440, Household Essentials 1115193, Home 4044, Office Supplies 1229749, Toys 4171, Books 3920, Seasonal 1085632, Pharmacy 5431. Clothing excluded.
- 2026-10-06 — Worker name standardized to sfb-valuation (matches Cloudflare); was sfb-pipeline in wrangler.toml.
- 2026-10-06 — Root cause of builds not triggering: Cloudflare GitHub app had "Only select repositories" (CaringForACause only). Switched to All repositories.
- 2026-10-06 — Food mapping drafted in data/categories.json (Pantry split pending). Added From Our Brands (store-brand coverage) and Seasonal Grocery. Alcohol and promo/brand/event nodes excluded.
- 2026-10-06 — Data workflow defined in docs/WORKFLOW.md: deterministic API crawl (no AI-generated prices), D1-backed resumable cron crawl, quality gates before publishing. Stage 1 test routes /items/<id> and /search added.
- 2026-10-06 — Stage 1 results recorded in docs/WORKFLOW.md. Proposed: salePrice as valuation price; Walmart-sold only; size parsed from name. Testing catalog filters soldByWmt/available next.
