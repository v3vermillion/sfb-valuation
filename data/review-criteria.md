# Sample review criteria

These rows come from a price snapshot that volunteers at a food bank use to value donated goods:
a volunteer scans or types the item in their hand and the app shows the exact Walmart item and its
current price. Every row is one Walmart listing after automatic cleaning. The review answers one
question: does this sample show a *class* of bad rows that the deterministic checks missed?

## What a valid row looks like

- A sellable consumer item sold by Walmart itself (not a marketplace seller): groceries, health and
  pharmacy items, personal care and beauty, baby, pet, household, home, office and craft supplies,
  toys, books, seasonal and party goods, auto, electronics, jewelry, sports and outdoors.
- A sensible product name, usually with a brand; the name reads like a shelf label, not like a
  search query, a placeholder ("-", "."), a SKU dump or a publisher's catalogue line.
- A size the name states is parsed: `size`/`unit`/`pack` match the name ("15.25 oz Can" -> 15.25 oz,
  "12 fl oz, 12 Pack" -> 12 fl oz x 12, "100 Count" -> 100 ct). Items that state no size (a single
  toy, a phone case) may legitimately have `size` null and the flag `no_size`.
- A plausible price for the item and size: a can of corn under a few dollars, a bag of dog food in the
  tens, a television in the hundreds. The `unit_price` (per oz, per fl oz or per count) should sit in
  the normal range for its category.
- Flags explain oddities: `promo_price` (a clearance or deal price), `kept_normal_price` (the deal
  price was replaced by the last normal price), `retired_upc` (an old barcode kept on purpose because
  donations include old stock), `carried_over` (not re-crawled this run), `size_conflict`,
  `upc_check_digit`. These are expected and are not junk.

## What is NOT a valid row (junk)

- Media and entertainment: music albums, films, video games, e-books, audiobooks, magazines misfiled
  outside the Books department.
- Apparel and shoes; alcohol; tobacco and vaping; gift cards, prepaid cards, subscriptions, services,
  warranties, digital codes, memberships.
- Third-party marketplace listings (prices 5-10x retail), wholesale lots, bundles priced per case while
  named per unit, or industrial/commercial supplies.
- Rows whose name and size disagree in a way that would mislead a volunteer (name says "6 Pack",
  size parsed as 1; name says "2 lb", size parsed as 2 oz), or whose price is implausible for the
  item (a candy bar at $45, a mattress at $0.99).
- Placeholder, test or empty listings.

## Category labels (measured, not junk)

Each row's `category` should name what the item is, the way a store labels it (the list and its boundaries are in
docs/CATEGORIES.md: for example canned soup is Canned & Jarred Foods, frozen pizza is Frozen Foods, shampoo is Beauty,
toothpaste is Personal Care, a cheese board is Kitchen & Dining). A wrong category is not junk; count it separately.

## What "systematic junk" means

Systematic junk is a whole class of bad rows, not an isolated oddity: for example every row from one
department is a marketplace listing, every "fl oz" item has its pack count folded into the size,
every Beauty row is a gift set priced per bundle, or a visible share of Food rows are music albums.
A handful of single strange rows in a sample of 300 is normal for a catalogue of hundreds of
thousands of items and is NOT systematic. Flag `systematic_junk: true` only when the pattern
repeats across several rows and would predictably affect many more rows in the full snapshot.

## What to return

Return strict JSON only, no prose before or after:

```json
{
  "systematic_junk": false,
  "junk_rate": 0.01,
  "junk_examples": [{"id": 123, "why": "one short reason"}],
  "notes": "one or two sentences on what you saw",
  "miscategorized_rate": 0.02,
  "miscategorized_examples": [{"id": 123, "category": "Snacks & Candy", "should_be": "Breakfast & Cereal"}]
}
```

- `junk_rate` is the share of the sampled rows you judge to be junk (0 to 1).
- `junk_examples` lists the junk rows you found (item `id` and a short reason), at most 25.
- `notes` names any repeating pattern, or says the sample looks clean.
- `miscategorized_rate` is the share of sampled rows whose category does not fit the item; `miscategorized_examples`
  lists them (at most 25).
