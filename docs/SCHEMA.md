# Snapshot row schema

`data-store:build/{candidate,published}/items.jsonl.gz` (shards `.s000`, `.s001`, ... past 45 MB): one JSON object per
Walmart listing, written by `crawler/process.py` from `crawler/normalize.py`. The app's pack is built from it by
`app/tools/build-db.mjs`.

| field | meaning |
|---|---|
| `id` | Walmart item id (the key) |
| `upc` | GTIN-14 string, or null |
| `name` | product name as Walmart lists it, feed markers ("***Discontinued***", "[Incomplete Data]") removed |
| `brand` | brand name, or null |
| `size`, `unit` | stated net quantity of one unit ("15.25", "oz"), or null when no quantity is stated |
| `pack` | units in the listing (default 1) |
| `base_qty`, `base_unit` | size in oz (weight), fl oz (volume) or ct (count) |
| `price` | Walmart's price in USD, exactly as listed (also when withheld, below) |
| `unit_price` | price per base unit for the whole pack; consumable departments only, null elsewhere, null when withheld or `unit_price_suspect` |
| `basis` | `each` or `lb` (sold by weight) |
| `cat` | store category id (data/categories.json, docs/CATEGORIES.md) |
| `dept` | Walmart department the listing was crawled from |
| `path` | Walmart category path (a hint for the category, not the answer) |
| `variants` | variant words found in the name (diet, organic, unscented, ...) |
| `store_brand` | true for Walmart's own brands |
| `stock`, `online`, `offer` | Walmart availability fields at crawl time |
| `size_src` | `name` or `size_field`: where the size came from |
| `primary` | the listing a barcode lookup shows first among listings sharing a UPC |
| `prev_price`, `promo` | previous snapshot's price; the deal price when a promo price was replaced by the normal one |
| `price_withheld` | true when `price` is outside the department's plausible range (data/gates.json price_sanity) |
| `equiv` | for a withheld price: `{price, method, confidence, basis_id, basis_name}`, the value the app shows |
| `flags` | see below |

Flags: `no_size`, `sold_each` (priced per piece; sized by its basis), `size_conflict`, `retired_upc`, `upc_check_digit`,
`promo_price`, `kept_normal_price`, `carried_over` (department not re-crawled this run), `pack_resolved`,
`unit_price_suspect` (per-unit price more than 10x off comparable items; dropped), `placeholder` (name identifies no
product: barcode lookup only, never in typed search, not in the size-parse rate), `discontinued` (Walmart marks it so),
`price_withheld`.

Not carried at all (rejected with a reason in `stats.json` `rejects_by_department`): `apparel`, `footwear`, `pet_bed`,
`alcohol`, `tobacco`, `media`, `marketplace`, `third_party_seller`, `no_price`, `no_name`, `duplicate`,
`food_without_upc_or_size`, `placeholder_no_barcode`, `placeholder_price`.
