"""Store-level prices: what Walmart charges at one store (Strongsville, OH), not Walmart.com.

  python -m crawler.storeprice probe --zip 44136 [--store-id N] [--sample raw-part.jsonl.gz]
  python -m crawler.storeprice refresh --budget-min 300     # (ci.py runs this as the `store` job)

The store is data/store.json. `refresh` asks Walmart for the store's price and stock of the snapshot's barcode
rows, 20 per call, consumable departments first and the oldest check first, and keeps them in
store_prices/<store_id>.jsonl.gz (one record per Walmart item id: p price, s stock, t date checked, g gone).
store_prices/latest.json says how many rows are still due; ci.decide() runs `store` while any are.
process.build() then shows the store price of every row checked within max_age_days (apply()).

Walmart's Product Lookup (`/items`) takes `storeId` and `zipCode` ("price and availability is also dependent on
zipCode and storeId", walmart.io affiliate docs). Most core rows in the crawl say "Not available" online (87% on
2026-10-09): those are items sold in stores, not shipped. A store price is the shelf price a donor paid, so it is
the price this app should show when Walmart returns one.

`probe` is read-only and costs about a dozen calls: it lists the stores near the zip code, then asks for the same
items three ways (no location, zipCode, storeId) and for one category page with and without storeId, and prints how
many prices and stock values differ. It answers, before anything is built on it: does this key get store prices,
for which store id, and from which endpoints. Nothing is written to the data-store.
"""
import argparse, json, os, random, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from . import store

CONFIG = Path(__file__).resolve().parent.parent / "data" / "store.json"
DIR = store.ROOT / "store_prices"
CHUNK = 20                    # /items takes up to 20 ids per call
SAVE_EVERY_S = 15 * 60

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


# ----------------------------------------------------------------------------- refresh (the `store` job)

def config():
    try:
        c = json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return None
    return c if c.get("store_id") else None


def _now():
    return datetime.now(timezone.utc)


def _day(dt):
    return dt.date().isoformat()


def _age_days(day, now):
    try:
        return (now.date() - datetime.fromisoformat(str(day)[:10]).date()).days
    except ValueError:
        return None


def path(store_id):
    return DIR / f"{store_id}.jsonl.gz"


def load(store_id):
    """{item id: {"p": price | None, "s": stock, "t": "YYYY-MM-DD", "g": True when Walmart no longer returns it}}"""
    p = path(store_id)
    if not store.jsonl_exists(p):
        return {}
    return {r["id"]: r for r in store.iter_jsonl_gz(p) if "id" in r}


def save(store_id, recs):
    store.write_jsonl_gz(path(store_id), sorted(recs.values(), key=lambda r: str(r["id"])))


def source_rows():
    """The rows to price: the published snapshot, else the latest candidate."""
    for p in (store.ROOT / "build" / "published" / "items.jsonl.gz", store.ROOT / "build" / "candidate" / "items.jsonl.gz"):
        if store.jsonl_exists(p):
            return store.iter_jsonl_gz(p)
    return iter(())


def _consumable_depts():
    try:
        return {d["name"] for d in store.config()["departments"] if d.get("consumable")}
    except (OSError, ValueError, KeyError):
        return set()


def due_ids(rows, recs, now, every_days, consumable=None):
    """Barcode rows (primary listing, not a placeholder) whose store price is missing or older than every_days:
    consumable departments first, never checked before checked long ago, then by id (stable)."""
    consumable = consumable if consumable is not None else _consumable_depts()
    due = []
    for r in rows:
        if not r.get("primary") or not r.get("upc") or "placeholder" in (r.get("flags") or []):
            continue
        rec = recs.get(r["id"])
        age = _age_days(rec["t"], now) if rec else None
        if age is not None and age < every_days:
            continue
        due.append((r.get("dept") not in consumable, rec is not None, -(age or 0), str(r["id"]), r["id"]))
    due.sort()
    return [d[-1] for d in due]


def refresh(wm, budget_min, now=None, cfg=None):
    """Price due rows at the configured store until done, the budget ends or Walmart throttles (Throttled propagates
    after the records fetched so far are saved). Returns a summary; writes store_prices/latest.json."""
    from .wm import Throttled
    cfg = cfg or config()
    if not cfg:
        return {"status": "skipped", "reason": "no data/store.json store_id"}
    now = now or _now()
    sid, every = str(cfg["store_id"]), int(cfg.get("refresh_every_days") or 7)
    recs = load(sid)
    ids = due_ids(source_rows(), recs, now, every)
    deadline = time.time() + budget_min * 60
    last_save = time.time()
    done = calls = got = gone = 0
    outcome = "done"
    try:
        for i in range(0, len(ids), CHUNK):
            if time.time() > deadline:
                outcome = "budget"; break
            chunk = ids[i:i + CHUNK]
            page = wm.get(f"/items?ids={','.join(str(x) for x in chunk)}&storeId={quote(sid)}")
            calls += 1
            items = {it.get("itemId"): it for it in _items(page)}
            day = _day(now)
            for iid in chunk:
                it = items.get(iid) or items.get(str(iid))
                if it is None:
                    recs[iid] = {"id": iid, "p": None, "s": None, "t": day, "g": True}; gone += 1
                else:
                    p = it.get("salePrice")
                    recs[iid] = {"id": iid, "p": float(p) if isinstance(p, (int, float)) and not isinstance(p, bool) else None,
                                 "s": it.get("stock"), "t": day}
                    got += 1
            done += len(chunk)
            if time.time() - last_save > SAVE_EVERY_S:
                save(sid, recs); _marker(sid, len(ids) - done, now, recs, every)
                store.checkpoint(f"store prices {sid}: {done}/{len(ids)}")
                last_save = time.time()
    except Throttled:
        outcome = "throttled"
        raise
    finally:
        save(sid, recs)
        latest = _marker(sid, len(ids) - done, now, recs, every)
        store.checkpoint(f"store prices {sid}: {done}/{len(ids)} ({outcome})")
    return {"status": outcome, "store_id": sid, "due": len(ids), "checked": done, "priced": got, "gone": gone,
            "calls": calls, "remaining": latest["due"]}


def _marker(sid, remaining, now, recs, every):
    oldest = min((r["t"] for r in recs.values() if r.get("t")), default=None)
    next_due = (datetime.fromisoformat(oldest) + timedelta(days=every)).date().isoformat() if oldest else _day(now)
    latest = {"store_id": sid, "checked": now.isoformat(timespec="seconds"), "due": max(0, remaining),
              "records": len(recs), "next_due": next_due}
    store.write_json(DIR / "latest.json", latest)
    return latest


def due(latest, now):
    """For ci.decide(): store work is due when nothing was recorded yet, rows remain from the last pass, or the oldest
    record has aged past refresh_every_days (next_due)."""
    if not config():
        return False
    if not isinstance(latest, dict):
        return True
    if (latest.get("due") or 0) > 0:
        return True
    nd = latest.get("next_due")
    return not nd or str(nd)[:10] <= _day(now)


def apply(rows, now=None, cfg=None):
    """process.build(): every row with a store price checked within max_age_days shows it. Walmart.com's price stays in
    online_price; the per-unit price scales with it; an online promo or kept normal price no longer applies (the store
    price is what the shelf says). Returns how many rows took a store price."""
    for r in rows.values():
        # a row carried over from the last snapshot may already show a store price: start again from Walmart.com's
        if "store_price" in r.get("flags", []):
            online = r.pop("online_price", None)
            if isinstance(online, (int, float)) and online > 0:
                if r.get("unit_price") and r.get("price"):
                    r["unit_price"] = round(r["unit_price"] * online / r["price"], 4)
                r["price"] = online
            r["flags"] = [f for f in r["flags"] if f != "store_price"]
            r.pop("store_checked", None); r.pop("store_stock", None)
    cfg = cfg or config()
    if not cfg:
        return 0
    now = now or _now()
    recs = load(str(cfg["store_id"]))
    if not recs:
        return 0
    max_age, n = int(cfg.get("max_age_days") or 21), 0
    for r in rows.values():
        rec = recs.get(r["id"])
        if not rec or rec.get("g") or not isinstance(rec.get("p"), (int, float)) or rec["p"] <= 0:
            continue
        age = _age_days(rec.get("t"), now)
        if age is None or age > max_age:
            continue
        old = r.get("price")
        r["online_price"] = old
        r["price"] = round(float(rec["p"]), 2)
        if r.get("unit_price") and isinstance(old, (int, float)) and old > 0:
            r["unit_price"] = round(r["unit_price"] * r["price"] / old, 4)
        r.pop("promo", None)
        r["flags"] = [f for f in r.get("flags", []) if f not in ("kept_normal_price", "promo_price")] + ["store_price"]
        r["store_checked"] = rec["t"]
        if rec.get("s"):
            r["store_stock"] = rec["s"]
        n += 1
    return n


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
    rf = sub.add_parser("refresh")
    rf.add_argument("--budget-min", type=float, default=60)
    a = ap.parse_args(argv)
    from .wm import Walmart
    if a.cmd == "refresh":
        print(json.dumps(refresh(Walmart(), a.budget_min), indent=1))
        return 0
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
