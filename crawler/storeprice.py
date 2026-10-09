"""Store-level prices: what Walmart charges at one store (Strongsville, OH), not Walmart.com.

  python -m crawler.storeprice probe --zip 44136 [--store-id N] [--sample raw-part.jsonl.gz]

Walmart's Product Lookup (`/items`) takes `storeId` and `zipCode` ("price and availability is also dependent on
zipCode and storeId", walmart.io affiliate docs). Most core rows in the crawl say "Not available" online (87% on
2026-10-09): those are items sold in stores, not shipped. A store price is the shelf price a donor paid, so it is
the price this app should show when Walmart returns one.

`probe` is read-only and costs about a dozen calls: it lists the stores near the zip code, then asks for the same
items three ways (no location, zipCode, storeId) and for one category page with and without storeId, and prints how
many prices and stock values differ. It answers, before anything is built on it: does this key get store prices,
for which store id, and from which endpoints. Nothing is written to the data-store.
"""
import argparse, json, os, random, sys
from urllib.parse import quote

from . import store

FIELDS = ("salePrice", "stock", "availableOnline", "offerType")


def _items(page):
    items = page.get("items") if isinstance(page, dict) else page
    return [i for i in (items or []) if isinstance(i, dict)]


def _call(wm, path):
    try:
        return wm.get(path), None
    except Exception as e:  # noqa: BLE001 - the probe reports every failure instead of stopping
        return None, f"{type(e).__name__}: {str(e)[:200]}"


def stores_near(wm, zip_code):
    out = {}
    for path in (f"/stores?zip={quote(zip_code)}",):
        page, err = _call(wm, path)
        rows = page if isinstance(page, list) else (page or {}).get("stores") if isinstance(page, dict) else None
        out[path] = {"error": err} if err else {
            "stores": [{k: s.get(k) for k in ("no", "name", "city", "stateProvCode", "zip", "streetAddress")}
                       for s in (rows or []) if isinstance(s, dict)][:10],
            "raw_keys": sorted(page.keys())[:20] if isinstance(page, dict) else None}
    return out


def sample_ids(part, n=20, seed=7):
    """Up to n primary-listing item ids from a raw part: half 'Not available' online, half available."""
    rows = list(store.iter_jsonl_gz(part)) if part else []
    na = [r["itemId"] for r in rows if r.get("stock") == "Not available" and r.get("itemId")]
    av = [r["itemId"] for r in rows if r.get("stock") == "Available" and r.get("itemId")]
    rnd = random.Random(seed)
    return rnd.sample(na, min(len(na), n // 2)) + rnd.sample(av, min(len(av), n - min(len(na), n // 2)))


def compare(base, other):
    """Per field: how many of the items both answers carry differ."""
    b = {i.get("itemId"): i for i in base}
    o = {i.get("itemId"): i for i in other}
    both = [k for k in b if k in o]
    diff = {f: sum(1 for k in both if b[k].get(f) != o[k].get(f)) for f in FIELDS}
    examples = [{"itemId": k, "name": (b[k].get("name") or "")[:60],
                 **{f"{f}": [b[k].get(f), o[k].get(f)] for f in ("salePrice", "stock")}}
                for k in both if b[k].get("salePrice") != o[k].get("salePrice") or b[k].get("stock") != o[k].get("stock")][:8]
    return {"items_both": len(both), "only_base": len(set(b) - set(o)), "only_other": len(set(o) - set(b)),
            "differ": diff, "examples": examples}


def probe(wm, zip_code="44136", store_id=None, part=None, category="976759"):
    report = {"zip": zip_code, "stores": stores_near(wm, zip_code)}
    if not store_id:
        for v in report["stores"].values():
            for s in v.get("stores") or []:
                if s.get("no"):
                    store_id = str(s["no"]); break
            if store_id:
                break
    report["store_id"] = store_id
    ids = sample_ids(part) if part else []
    report["sample"] = len(ids)
    if ids:
        joined = ",".join(str(i) for i in ids)
        answers = {}
        for label, extra in (("plain", ""), ("zipCode", f"&zipCode={zip_code}"),
                             ("storeId", f"&storeId={store_id}" if store_id else None)):
            if extra is None:
                continue
            page, err = _call(wm, f"/items?ids={joined}{extra}")
            answers[label] = {"error": err} if err else _items(page)
        report["items"] = {label: (a if isinstance(a, dict) else {"returned": len(a)}) for label, a in answers.items()}
        for label in ("zipCode", "storeId"):
            if isinstance(answers.get(label), list) and isinstance(answers.get("plain"), list):
                report["items"][label]["vs_plain"] = compare(answers["plain"], answers[label])
    if store_id:
        base, err1 = _call(wm, f"/paginated/items?category={category}&soldByWmt=true")
        loc, err2 = _call(wm, f"/paginated/items?category={category}&soldByWmt=true&storeId={store_id}")
        report["paginated"] = {"error": err1 or err2} if (err1 or err2) else {
            "plain_items": len(_items(base)), "storeId_items": len(_items(loc)),
            "storeId_total_pages": loc.get("totalPages") if isinstance(loc, dict) else None,
            "plain_total_pages": base.get("totalPages") if isinstance(base, dict) else None,
            "vs_plain": compare(_items(base), _items(loc))}
    return report


def markdown(r):
    L = [f"### Store price probe (zip {r['zip']}, store id {r.get('store_id') or 'none found'})", ""]
    for path, v in r["stores"].items():
        if v.get("error"):
            L.append(f"- `{path}`: {v['error']}")
        else:
            L.append(f"- `{path}`: {len(v['stores'])} stores" + (f" (keys {v['raw_keys']})" if v.get("raw_keys") else ""))
            for s in v["stores"]:
                L.append(f"  - #{s.get('no')} {s.get('name')} — {s.get('streetAddress')}, {s.get('city')} {s.get('zip')}")
    L.append(f"\nSample: {r.get('sample', 0)} items (half 'Not available' online)\n")
    for label, v in (r.get("items") or {}).items():
        if v.get("error"):
            L.append(f"- `/items` {label}: {v['error']}")
            continue
        line = f"- `/items` {label}: {v.get('returned')} returned"
        if "vs_plain" in v:
            c = v["vs_plain"]
            line += f"; vs no location: {c['differ']['salePrice']} prices and {c['differ']['stock']} stock values differ of {c['items_both']}"
        L.append(line)
        for e in (v.get("vs_plain") or {}).get("examples", []):
            L.append(f"  - {e['itemId']} {e['name']}: price {e['salePrice'][0]} -> {e['salePrice'][1]}, stock {e['stock'][0]} -> {e['stock'][1]}")
    p = r.get("paginated")
    if p:
        if p.get("error"):
            L.append(f"- `/paginated` with storeId: {p['error']}")
        else:
            c = p["vs_plain"]
            L.append(f"- `/paginated` with storeId: {p['storeId_items']} items, {p['storeId_total_pages']} pages "
                     f"(plain {p['plain_items']}, {p['plain_total_pages']} pages); {c['differ']['salePrice']} prices and "
                     f"{c['differ']['stock']} stock values differ of {c['items_both']}")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--zip", default="44136")
    p.add_argument("--store-id", default=None)
    p.add_argument("--sample", default=None, help="a raw crawl part (jsonl.gz) to draw item ids from")
    a = ap.parse_args(argv)
    from .wm import Walmart
    from pathlib import Path
    r = probe(Walmart(), a.zip, a.store_id or None, Path(a.sample) if a.sample else None)
    text = markdown(r)
    print(text)
    print(json.dumps(r, indent=1, default=str)[:20000])
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    sys.exit(main())
