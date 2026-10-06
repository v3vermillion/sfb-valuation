# Decisions (dated, newest last — this file wins on conflict)

- 2026-10-05 — Fully offline PWA with search bar; no barcode wizard, no online/vision path (would recreate subscription cost).
- 2026-10-05 — Walmart is the primary price reference. Regular price only, first-party seller only. Clothing excluded.
- 2026-10-05 — 23 categories exist for the data pipeline only, not app UX. Brand and size are row attributes.
- 2026-10-06 — Scraping abandoned: Walmart blocks datacenter IPs (browser-bridge test failed). Data source is Walmart I/O Affiliate API.
- 2026-10-06 — Prices are Walmart.com online prices; store pinning to Strongsville not required.
- 2026-10-06 — Walmart I/O app "SFB-Donation-Valuation" created; public key uploaded (body-only format accepted), Production, key version 1.
- 2026-10-06 — Repo created (private). Pipeline Worker deploys from GitHub via Cloudflare Git integration (owner is phone-only).
