"""Price sanity and equivalent values (docs/DECISIONS.md, 2026-10-08).

An item price outside a plausible range for its department is withheld: it stays in the snapshot as Walmart listed it
(`price`, for history and audits) but the app never shows it. The row carries `price_withheld` and an equivalent value
(`equiv`) instead, so a scan of that item is never blank:

  1. the closest comparable item (same category, the most name tokens in common, same base unit), scaled to this item's
     size when both have a per-unit price;
  2. else the median per-unit price of comparable items (qa.unit_price_medians) times this item's size;
  3. else the median price of the item's category in its department.

The range per department is [floor, min(cap, over_p99 x the department's 99th percentile price)], from
data/gates.json "price_sanity". Placeholder listings (barcode only) whose own price fails the range are dropped instead:
there is nothing to show for them.
"""
import math, statistics
from collections import Counter, defaultdict

from .identify import tokens as name_tokens, WALMART_STORE_BRANDS

MATCH_MIN = 0.45


def _quantile(sorted_vals, q):
    if not sorted_vals:
        return None
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))]


def bounds(rows, cfg):
    """{department: (low, high, p99)} from this snapshot's prices."""
    sanity = cfg.get("price_sanity") or {}
    floor = float(sanity.get("floor", 0.10))
    over = float(sanity.get("over_p99", 5))
    caps = sanity.get("caps") or {}
    prices = defaultdict(list)
    for r in rows:
        if "placeholder" not in r.get("flags", []) and isinstance(r.get("price"), (int, float)) and r["price"] > 0:
            prices[r["dept"]].append(r["price"])
    out = {}
    for dept, vals in prices.items():
        vals.sort()
        p99 = _quantile(vals, 0.99)
        cap = float(caps.get(dept, caps.get("default", 5000)))
        out[dept] = (floor, round(min(cap, over * p99), 2), p99)
    return out


def _confidence(score):
    return "high" if score >= 0.7 else "medium" if score >= 0.55 else "low"


class Valuer:
    """Equivalent values for withheld rows, from the rows whose prices are trusted."""

    def __init__(self, rows, group_min=50):
        from .qa import unit_price_medians
        self.trusted = [r for r in rows if not r.get("price_withheld") and "placeholder" not in r.get("flags", [])
                        and "unit_price_suspect" not in r.get("flags", []) and isinstance(r.get("price"), (int, float))]
        self.median_lookup = unit_price_medians(self.trusted, group_min)
        self.index = defaultdict(list)
        self.toks = {}
        by_cat = defaultdict(list)
        for i, r in enumerate(self.trusted):
            t = name_tokens(r["name"], r.get("brand"))
            self.toks[i] = t
            for w in t:
                self.index[(r["cat"], w)].append(i)
            by_cat[(r["dept"], r["cat"])].append(r["price"])
        self.df = Counter({k: len(v) for k, v in self.index.items()})
        self.cat_median = {k: statistics.median(v) for k, v in by_cat.items() if v}

    def value(self, row, low, high):
        """{"price", "method", "confidence", "basis_id", "basis_name"} for a withheld row; never None."""
        qty, pack = row.get("base_qty"), row.get("pack") or 1
        pt = name_tokens(row["name"], row.get("brand"))
        cands = set()
        for w in sorted(pt, key=lambda w: self.df.get((row["cat"], w), 0))[:4]:
            n = self.df.get((row["cat"], w), 0)
            if 0 < n < 20000:
                cands.update(self.index[(row["cat"], w)])
        best, best_score = None, 0.0
        for i in cands:
            r = self.trusted[i]
            if r["id"] == row["id"]:
                continue
            if qty and r.get("base_unit") and r["base_unit"] != row.get("base_unit"):
                continue
            j = len(pt & self.toks[i]) / max(1, len(pt | self.toks[i]))
            rb, b = (r.get("brand") or "").lower(), (row.get("brand") or "").lower()
            if b and rb == b:
                j += 0.2
            elif rb in WALMART_STORE_BRANDS and b in WALMART_STORE_BRANDS:
                j += 0.1
            if qty and r.get("base_qty"):
                j += 0.1 * min(qty, r["base_qty"]) / max(qty, r["base_qty"])
            if j > best_score:
                best, best_score = r, j
        if best is not None and best_score >= MATCH_MIN:
            est = best["unit_price"] * qty * pack if qty and best.get("unit_price") else best["price"]
            if low <= est <= high:
                return {"price": round(est, 2), "method": "comparable item", "confidence": _confidence(best_score),
                        "basis_id": best["id"], "basis_name": best["name"]}
        if qty:
            med = self.median_lookup(row)[0]
            if med:
                est = med * qty * pack
                if low <= est <= high:
                    return {"price": round(est, 2), "method": "median per-unit price of comparable items",
                            "confidence": "low", "basis_id": None, "basis_name": None}
        med = self.cat_median.get((row["dept"], row["cat"]))
        if med is None:
            pool = [p for (d, _), p in self.cat_median.items() if d == row["dept"]]
            med = statistics.median(pool) if pool else low
        return {"price": round(min(max(med, low), high), 2), "method": "median price of its category",
                "confidence": "rough", "basis_id": None, "basis_name": None}


def apply(rows, cfg, group_min=50):
    """Withhold implausible prices and attach equivalent values. rows is a dict id -> row and is changed in place.
    Returns (withheld list for the report, bounds, dropped placeholder ids)."""
    b, dropped = withhold(rows, cfg)
    return attach_values(rows, b, group_min), {d: {"low": lo, "high": hi, "p99": p99} for d, (lo, hi, p99) in b.items()}, dropped


POS_NAME_MAX = 20          # Walmart's register names are cut at 20 characters


def withhold(rows, cfg):
    """Flag every price outside its department's plausible range (price_withheld, no per-unit price) and drop
    placeholder listings with such a price. Runs before the per-unit outlier check so an absurd price is not counted
    as a parsing problem. Returns (bounds, dropped placeholder (id, department) pairs)."""
    b = bounds(rows.values(), cfg)
    dropped = []
    for iid, r in list(rows.items()):
        lo, hi, _ = b.get(r["dept"], (0.10, 5000, None))
        p = r.get("price")
        if isinstance(p, (int, float)) and lo <= p <= hi:
            continue
        if "placeholder" in r.get("flags", []) or (isinstance(p, (int, float)) and p > hi and len(r.get("name") or "") <= POS_NAME_MAX):
            # a placeholder with an implausible price fails rule 2 and is not kept even for barcode lookup; so is a
            # register-length name priced far above anything in its department ("Old El Paso Bold/Pri" at $1,042,
            # "Premier Protein 6pk" at $1,783): a pre-packed display or pallet listed under its truncated POS name
            dropped.append((iid, r["dept"]))
            del rows[iid]
            continue
        r["price_withheld"] = True
        r["unit_price"] = None
        if "price_withheld" not in r["flags"]:
            r["flags"].append("price_withheld")
    return b, dropped


def attach_values(rows, b, group_min=50):
    """Value every withheld row at an equivalent (Valuer), once per-unit prices are final. Returns the withheld list
    for the report, sorted by department and raw price."""
    withheld = []
    valuer = Valuer(rows.values(), group_min)
    for r in rows.values():
        if not r.get("price_withheld"):
            continue
        lo, hi, _ = b.get(r["dept"], (0.10, 5000, None))
        r["equiv"] = valuer.value(r, lo, hi)
        withheld.append({"id": r["id"], "upc": r.get("upc"), "name": r["name"], "dept": r["dept"], "raw_price": r["price"],
                         "range": [lo, hi], "value": r["equiv"]["price"], "method": r["equiv"]["method"],
                         "basis": r["equiv"]["basis_name"]})
    withheld.sort(key=lambda w: (w["dept"], -(w["raw_price"] or 0)))
    return withheld
