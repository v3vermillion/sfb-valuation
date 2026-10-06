"""Offline identification + equivalent pricing for barcodes Walmart doesn't sell
(Aldi, Giant Eagle, Meijer, Target, Dollar General, Marc's, Costco store brands, regional brands).

  python -m crawler.identify fetch     # Open Food/Beauty/Products Facts -> US subset (UPC, name, brand, quantity)
  python -m crawler.identify match     # pre-compute an equivalent Walmart price for each identified UPC

Equivalent price = the closest Walmart-sold product of the same type, priced per unit and scaled to the
donated item's size. Other chains' store brands are matched to Walmart's store brands (same price tier);
national brands are matched to the same brand first. Every row carries a confidence and the basis item,
and the app labels these as "equivalent value", never as an exact price.
Data: Open Food Facts contributors, ODbL (attribution required in the app's About screen).
"""
import argparse, csv, gzip, io, re, sys
from collections import Counter, defaultdict

import requests

from . import store
from .normalize import gtin14, parse_quantity, to_base

SOURCES = [
    "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz",
    "https://static.openbeautyfacts.org/data/en.openbeautyfacts.org.products.csv.gz",
    "https://static.openproductsfacts.org/data/en.openproductsfacts.org.products.csv.gz",
]
OUT = store.ROOT / "identify"

OTHER_STORE_BRANDS = {
    # Aldi
    "happy harvest", "clancy's", "millville", "simply nature", "specially selected", "season's choice", "friendly farms",
    "burman's", "casa mamita", "bake house creations", "benton's", "fit & active", "l'oven fresh", "stonemill",
    "sweet harvest", "southern grove", "chef's cupboard", "savoritz", "fusia", "reggano", "carlini", "tuscan garden",
    "countryside creamery", "appleton farms", "kirkwood", "fremont fish market", "never any!", "little journey",
    "radiance", "barissimo", "elevation", "choceur", "earth grown", "lunch mate", "deutsche kuche", "mama cozzi's",
    # Giant Eagle / Market District / Marc's / Save-A-Lot
    "giant eagle", "market district", "marc's", "coburn farms",
    # Meijer / Kroger / Target / Dollar General / Costco / Sam's / Amazon
    "meijer", "true goodness", "frederik's", "kroger", "private selection", "simple truth", "heritage farm",
    "good & gather", "market pantry", "up & up", "favorite day", "clover valley", "kirkland signature",
    "member's mark", "happy belly", "amazon basics", "food club", "best choice", "shurfine",
}
WALMART_STORE_BRANDS = {"great value", "equate", "mainstays", "parent's choice", "marketside", "freshness guaranteed",
                        "sam's choice", "bettergoods", "ol' roy", "special kitty", "pen+gear", "hyper tough", "onn."}
STOP = {"the", "and", "with", "of", "in", "a", "an", "for", "to", "oz", "fl", "lb", "lbs", "g", "ml", "l", "ct", "count",
        "pack", "pk", "can", "cans", "jar", "bottle", "bottles", "box", "bag", "each", "size", "value", "family",
        "net", "wt", "x", "&", "-", "original", "brand"}


def tokens(text, brand=None):
    t = re.sub(r"\d+(\.\d+)?", " ", (text or "").lower())
    words = re.findall(r"[a-z][a-z'+]*", t)
    btoks = set(re.findall(r"[a-z][a-z'+]*", (brand or "").lower()))
    return {w for w in words if w not in STOP and w not in btoks and len(w) > 1}


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(sys.maxsize)
    rows, seen = [], set()
    for url in SOURCES:
        n = 0
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            gz = gzip.GzipFile(fileobj=r.raw)
            reader = csv.reader(io.TextIOWrapper(gz, encoding="utf-8", errors="replace"), delimiter="\t", quoting=csv.QUOTE_NONE)
            header = next(reader)
            ix = {h: i for i, h in enumerate(header)}
            for rec in reader:
                try:
                    countries = rec[ix["countries_tags"]]
                    if "en:united-states" not in countries:
                        continue
                    key, _, ok = gtin14(rec[ix["code"]])
                    name = rec[ix["product_name"]].strip()
                    if not key or not ok or not name or key in seen:
                        continue
                    seen.add(key)
                    rows.append({"upc": key, "name": name, "brand": rec[ix["brands"]].split(",")[0].strip(),
                                 "quantity": rec[ix["quantity"]].strip()})
                    n += 1
                except (IndexError, KeyError):
                    continue
        print(f"{url.split('/')[2]}: {n} US products")
    store.write_jsonl_gz(OUT / "products_us.jsonl.gz", rows)
    print(f"total {len(rows)}")


def match():
    pub = store.ROOT / "build" / "published" / "items.jsonl.gz"
    cand = store.ROOT / "build" / "candidate" / "items.jsonl.gz"
    src = pub if pub.exists() else cand
    wm = [r for r in store.iter_jsonl_gz(src) if r.get("unit_price") and r.get("base_unit")]
    wm_upcs = {r["upc"] for r in store.iter_jsonl_gz(src) if r.get("upc")}
    index = defaultdict(list)
    tok_of = {}
    for i, r in enumerate(wm):
        tk = tokens(r["name"], r.get("brand"))
        tok_of[i] = tk
        for t in tk:
            index[t].append(i)
    df = Counter({t: len(v) for t, v in index.items()})

    out, stats = [], Counter()
    for p in store.iter_jsonl_gz(OUT / "products_us.jsonl.gz"):
        if p["upc"] in wm_upcs:
            stats["exact_in_walmart"] += 1; continue
        size, unit, pack = parse_quantity(p["quantity"] or p["name"])
        base, dim = to_base(size, unit)
        pt = tokens(p["name"], p["brand"])
        if not pt or not base:
            stats["unparseable"] += 1; continue
        brand = (p["brand"] or "").lower()
        other_store = brand in OTHER_STORE_BRANDS
        cands = set()
        for t in sorted(pt, key=lambda t: df.get(t, 0))[:3]:
            if df.get(t, 0) and df[t] < 20000:
                cands.update(index[t])
        best, best_score = None, 0.0
        for i in cands:
            r = wm[i]
            if r["base_unit"] != dim:
                continue
            j = len(pt & tok_of[i]) / len(pt | tok_of[i])
            rb = (r.get("brand") or "").lower()
            if other_store and rb in WALMART_STORE_BRANDS:
                j += 0.15
            elif not other_store and rb and rb == brand:
                j += 0.25
            ratio = min(base, r["base_qty"]) / max(base, r["base_qty"])
            j += 0.1 * ratio
            if j > best_score:
                best, best_score = r, j
        if not best or best_score < 0.45:
            stats["no_equivalent"] += 1; continue
        price = round(best["unit_price"] * base * (pack or 1), 2)
        conf = "high" if best_score >= 0.7 else "medium" if best_score >= 0.55 else "low"
        stats[f"matched_{conf}"] += 1
        out.append({"upc": p["upc"], "name": p["name"], "brand": p["brand"], "quantity": p["quantity"],
                    "base_qty": base, "base_unit": dim, "pack": pack or 1, "est_price": price,
                    "basis_id": best["id"], "basis_name": best["name"], "basis_price": best["price"],
                    "confidence": conf, "score": round(best_score, 3)})
    n = store.write_jsonl_gz(OUT / "equivalents.jsonl.gz", out)
    store.write_json(OUT / "equivalents_stats.json", dict(stats))
    print(f"equivalents: {n}  {dict(stats)}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "match"])
    a = ap.parse_args(argv)
    fetch() if a.cmd == "fetch" else match()


if __name__ == "__main__":
    main()
