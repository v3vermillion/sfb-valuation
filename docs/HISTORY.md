# Price history

Recorded by `crawler/history.py` from `qa.publish()`, before `build/published` is replaced, on the
`data-store` branch under `history/`. The branch history is compacted to one commit after every
publish, so these files are the only record of past prices; they are small (changes only) and are
never rewritten.

## Files

| file | written | one line per |
|---|---|---|
| `history/baseline-<run_id>.jsonl.gz` | first publish (or the first publish after history was introduced: then the baseline is the *previous* snapshot, named after its version) | item: `{"id", "upc", "price", "promo"}` |
| `history/changes-<run_id>.jsonl.gz` | every later publish | item whose price changed, appeared or disappeared: `{"id", "upc", "old", "new", "promo", "date"}` |
| `history/index.json` | appended at every publish | publish: `{"run_id", "date", "kind": "baseline" or "changes", "rows", "file"}` |

- `id` is the Walmart item id (the snapshot row's `id`); `upc` the GTIN-14 key (may be null).
- `price` / `old` / `new` is the valuation price of the row at that publish: the `salePrice` Walmart
  reported, except that a clearance/flash/limited-time price keeps the last normal price
  (`process.py` promo guard). A deal price that could not be replaced (first sighting) is recorded as the
  price with `promo: true`.
- `promo` is true when the row carried the `promo_price` flag at that publish.
- A new item has `old: null`; an item that left the snapshot has `new: null`.
- Unchanged items are not written. The current price of every item is always in
  `build/published/items.jsonl.gz`; history answers "what did it cost before".
- `date` is the publish date (UTC, `YYYY-MM-DD`); the manifest's `published` timestamp is exact.

Replaying the baseline and every changes file in `index.json` order rebuilds the price of every item at
every publish. Nothing else is needed.

## Per-item medians of non-promo prices over the last N publishes

The valuation-rule question in four to six weeks is whether to value donations at the current price or
at a median over recent publishes. Compute it like this (run on a checkout of `data-store`):

```python
import gzip, json, statistics
from collections import defaultdict

def rows(path):
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

index = json.load(open("history/index.json"))
N = 4                                   # publishes to look back over
prices = {}                             # id -> current (price, promo) while replaying
observed = defaultdict(list)            # id -> [price at each of the last N publishes, non-promo only]

for k, entry in enumerate(index):
    f = "history/" + entry["file"]
    if entry["kind"] == "baseline":
        prices = {r["id"]: (r["price"], r["promo"]) for r in rows(f)}
    else:
        for r in rows(f):
            if r["new"] is None:
                prices.pop(r["id"], None)
            else:
                prices[r["id"]] = (r["new"], r["promo"])
    if k >= len(index) - N:             # one of the last N publishes: snapshot every item's price
        for i, (p, promo) in prices.items():
            if p is not None and not promo:
                observed[i].append(p)

median = {i: statistics.median(v) for i, v in observed.items() if v}
```

`median[i]` is the median of the item's non-promo prices over the last N publishes (fewer when the
item appeared recently). An item that was on promo at every one of those publishes has no entry; fall
back to its current price. To weight by time instead of by publish, use `entry["date"]`.

## Size

A full snapshot is ~760k rows; a baseline is about the size of the price column (a few MB gzipped).
A weekly core refresh changes a small share of prices, so a changes file is typically well under a
megabyte. `index.json` grows by one line per publish.
