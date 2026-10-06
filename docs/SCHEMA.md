# Item row schema (JSONL, one object per line)

| field | notes |
|---|---|
| walmart_item_id | stable key |
| upc | optional |
| brand | |
| product_name | |
| variant | flavor/scent/etc. |
| size | numeric |
| unit | oz, fl oz, lb, ct, ... |
| pack_count | default 1 |
| price_basis | each / lb / oz |
| regular_price | USD; the price the app uses |
| sale_price | recorded, never used for valuation |
| seller | must be Walmart.com |
| product_url | |
| walmart_category_path | from API |
| category | one of the 23 in data/categories.json |
| subcategory | |
| observed_date | ISO date |

Dedupe: walmart_item_id, else brand+product_name+size.
