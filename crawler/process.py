"""Build a candidate snapshot from the latest crawled run.

  python -m crawler.process

- Normalizes every raw item (crawler/normalize.py) and counts rejects by reason.
- Merges with the published snapshot for departments not in this run (weekly core refresh
  keeps last month's non-core items) so the snapshot is always complete.
- Promo prices (clearance/flash/limited deals) keep the last normal price when one is known.
- Picks one primary row per UPC for barcode lookups.
Output: store/build/candidate/{items.jsonl.gz, stats.json}
"""
import json, math, statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone

from . import classify, store, valuation
from .normalize import normalize, parse_quantity, to_base

BUILD = store.ROOT / "build"


def latest_run():
    state = store.read_json(store.ROOT / "state" / "run.json")
    if not state or state["status"] not in ("crawled", "built", "published", "awaiting_approval", "needs_review"):
        raise SystemExit("no completed crawl to process")
    return state


def build():
    cfg = store.config()
    state = latest_run()
    depts = {d["id"]: d for d in cfg["departments"]}
    run_dir = store.ROOT / "raw" / state["run_id"]
    crawled_depts = {d["id"] for d in state["departments"] if d["status"] == "done"}

    prev_rows = {}
    prev_path = BUILD / "published" / "items.jsonl.gz"
    if store.jsonl_exists(prev_path):
        for r in store.iter_jsonl_gz(prev_path):
            prev_rows[r["id"]] = r

    rows, seen = {}, set()
    rejects = defaultdict(Counter)
    raw_counts = Counter()
    for dept_id in crawled_depts:
        dept = depts.get(dept_id)
        if not dept:
            continue
        for part in sorted((run_dir / dept_id).glob("part-*.jsonl.gz")):
            for item in store.iter_jsonl_gz(part):
                raw_counts[dept["name"]] += 1
                iid = item.get("itemId")
                if iid in seen:
                    rejects[dept["name"]]["duplicate"] += 1
                    continue
                seen.add(iid)
                row, why = normalize(item, dept, cfg)
                if why:
                    rejects[dept["name"]][why] += 1
                    continue
                prev = prev_rows.get(iid)
                if "promo_price" in row["flags"] and prev and "promo_price" not in prev.get("flags", []):
                    row["promo"] = row["price"]
                    row["price"] = prev["price"]
                    row["unit_price"] = prev.get("unit_price")
                    row["flags"].append("kept_normal_price")
                if prev and prev.get("price"):
                    row["prev_price"] = prev["price"]
                rows[iid] = row

    carried = 0
    crawled_names = {depts[d]["name"] for d in crawled_depts if d in depts}
    for iid, r in prev_rows.items():
        if iid not in rows and r.get("dept") not in crawled_names:
            r = dict(r); r.setdefault("flags", []).append("carried_over")
            rows[iid] = r; carried += 1

    names_filled = fill_placeholder_names(rows)

    # categories: the name's noun decided against how coherent each Walmart path is across the whole snapshot
    # (classify.PathStats); rows carried over from an earlier snapshot are classified again with today's rules
    cfg_depts = {d["name"]: d for d in cfg["departments"]}
    stats_paths = classify.PathStats()
    for r in rows.values():
        if "noun" not in r:
            d = cfg_depts.get(r.get("dept"))
            nn = classify.noun(r["name"], r.get("path"), d, cfg) if d else None
            r["noun"] = list(nn) if nn else None
        if "placeholder" not in r.get("flags", []):
            stats_paths.add(r.get("path"), r["noun"])
    for r in rows.values():
        nn, d = r.pop("noun", None), cfg_depts.get(r.get("dept"))
        r["_kind"] = nn[2] if nn else None             # the product noun, used by price sanity; never written
        if d:
            r["cat"] = str(classify.decide(tuple(nn) if nn else None, r.get("path"), d, cfg, stats_paths, r["name"]))

    # price sanity before anything that depends on a listing being kept (crawler/valuation.py): an implausible price is
    # withheld, and a placeholder with one is dropped, before primaries are chosen and per-unit prices are judged (a
    # $3e21 listing is not a parsing problem); the equivalent value is attached once per-unit prices are final
    from .qa import unit_outlier_stats, gates_config
    group_min = int(gates_config().get("unit_outlier_group_min") or 50)
    bounds, dropped_placeholders = valuation.withhold(rows, gates_config(), group_min)
    for _, dept_name, why in dropped_placeholders:
        rejects[dept_name][why] += 1

    # one primary row per UPC (barcode lookups): prefer current, in stock, normal price, newest listing
    by_upc = defaultdict(list)
    for r in rows.values():
        r.pop("primary", None)
        if r.get("upc"):
            by_upc[r["upc"]].append(r)
    conflicts = []
    for upc, group in by_upc.items():
        group.sort(key=lambda r: ("retired_upc" in r["flags"], r.get("stock") != "Available",
                                  "promo_price" in r["flags"], -int(r["id"])))
        group[0]["primary"] = True
        prices = [g["price"] for g in group]
        if len(group) > 1 and max(prices) > 1.5 * min(prices):
            conflicts.append({"upc": upc, "items": [(g["id"], g["name"], g["price"]) for g in group][:5]})

    # per-unit prices that are more than 10x off their category+unit median are almost always a parsing
    # artefact (a packet size taken for the carton, a count read as a weight): keep the item price, drop the
    # per-unit price and flag the row so the app shows nothing misleading and identify.py never uses it as a basis
    before_share, _, before = unit_outlier_stats(rows.values(), group_min)
    resolved = resolve_packs(rows.values(), group_min)
    raw_share, unit_priced, outliers = unit_outlier_stats(rows.values(), group_min)
    for o in outliers:
        r = rows[o["id"]]
        r["unit_price"] = None
        r["flags"].append("unit_price_suspect")
    unit_outliers_raw = {"share": raw_share, "unit_priced_rows": unit_priced, "count": len(outliers),
                         "examples": outliers[:25], "before_pack_resolution": {"share": before_share, "count": len(before)},
                         "pack_resolved": resolved, "scope": "consumable departments (no per-unit price elsewhere)"}

    withheld = valuation.attach_values(rows, bounds, group_min)
    for r in rows.values():
        r.pop("_kind", None)
    price_bounds = {d: {"low": lo, "high": hi, "p99": p99} for d, (lo, hi, p99) in bounds.items()}

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = BUILD / "candidate"
    n = store.write_jsonl_gz(out / "items.jsonl.gz", sorted(rows.values(), key=lambda r: r["id"]))
    stats = {
        "built": stamp, "run_id": state["run_id"], "plan": state["plan"], "items": n,
        "upcs": len(by_upc), "carried_over": carried,
        "raw_by_department": dict(raw_counts),
        "kept_by_category": dict(Counter(r["cat"] for r in rows.values())),
        "kept_by_department": dict(Counter(r["dept"] for r in rows.values())),
        "rejects_by_department": {k: dict(v) for k, v in rejects.items()},
        "flags": dict(Counter(f for r in rows.values() for f in r["flags"])),
        "upc_price_conflicts": len(conflicts), "upc_price_conflict_examples": conflicts[:25],
        "unit_outliers_raw": unit_outliers_raw,
        "price_bounds": price_bounds, "price_withheld": withheld,
        "placeholders": {"count": sum(1 for r in rows.values() if "placeholder" in r["flags"]), "names_filled": names_filled,
                         "examples": [{"id": r["id"], "upc": r.get("upc"), "name": r["name"], "listed_name": r.get("listed_name"),
                                       "name_src": r.get("name_src"), "dept": r["dept"],
                                       "price": r["price"]} for r in rows.values() if "placeholder" in r["flags"]][:50]},
    }
    store.write_json(out / "stats.json", stats)
    state["status"] = "built"
    store.write_json(store.ROOT / "state" / "run.json", state)
    print(f"candidate: {n} items, {len(by_upc)} UPCs, {carried} carried over")
    return stats


NAME_NOT_PROVIDED = "(name not provided)"


def fill_placeholder_names(rows):
    """Give barcode-only (placeholder) rows a real name, so a scan shows what the item is: the name of another Walmart
    listing with the same UPC, else the Open Food/Beauty/Products Facts name for the UPC (identify/products_us), else
    NAME_NOT_PROVIDED (the app shows it after the brand); never the feed's placeholder text, which stays in
    `listed_name`. A size is taken from the new name, or the Open Facts quantity, when the row has none. Returns counts by
    source."""
    todo = [r for r in rows.values() if "placeholder" in r.get("flags", []) and "listed_name" not in r]
    counts = Counter()
    if not todo:
        return dict(counts)
    need = {r["upc"] for r in todo if r.get("upc")}
    walmart = {}
    for r in rows.values():
        if r.get("upc") in need and "placeholder" not in r.get("flags", []) and r["upc"] not in walmart:
            walmart[r["upc"]] = (r["name"], r.get("brand"), None)
    facts = {}
    src = store.ROOT / "identify" / "products_us.jsonl.gz"
    if store.jsonl_exists(src):
        for p in store.iter_jsonl_gz(src):
            if p.get("upc") in need and p.get("name"):
                facts[p["upc"]] = (p["name"], p.get("brand"), p.get("quantity"))
    for r in todo:
        hit, how = walmart.get(r.get("upc")), "walmart_listing"
        if not hit:
            hit, how = facts.get(r.get("upc")), "open_facts"
        r["listed_name"] = r["name"]
        if not hit:
            r["name"], r["name_src"] = NAME_NOT_PROVIDED, "none"
            counts["none"] += 1
            continue
        name, brand, qty = hit
        r["name"], r["name_src"] = name, how
        if brand and (not r.get("brand") or r["brand"].strip().lower() in ("unbranded", "online", "generic")):
            r["brand"] = brand
        r["flags"].append("name_filled")
        r.pop("noun", None)                            # classified again from the real name
        if r.get("size") is None:
            size, unit, _ = parse_quantity(name)
            if size is None and qty:
                size, unit, _ = parse_quantity(qty)
            if size is not None:
                base, dim = to_base(size, unit)
                r.update(size=size, unit=unit, base_qty=base, base_unit=dim)
                if "no_size" in r["flags"]:
                    r["flags"].remove("no_size")
        counts[how] += 1
    return dict(counts)


def resolve_packs(rows, group_min=50, passes=2):
    """Rows whose name supports several pack counts (normalize.pack_options) keep the default reading unless its
    per-unit price is more than 10x off the median of comparable rows: qa.unit_price_medians, the same groups and
    basis the unit-outlier check uses (the most specific category path with at least group_min unit-priced rows in
    the same base unit). Then the reading closest to that median wins, if it lands inside the 10x band, and the row is
    flagged pack_resolved. A second pass re-reads the medians once the first pass has corrected the worst readings.
    pack_options never reaches the snapshot. Returns how many rows changed."""
    from .qa import unit_price_medians
    rows = list(rows)
    changed = 0
    for _ in range(passes):
        lookup = unit_price_medians(rows, group_min)
        moved = 0
        for r in rows:
            opts, up, base = r.get("pack_options"), r.get("unit_price"), r.get("base_qty")
            if not opts or not base or not isinstance(up, (int, float)) or up <= 0:
                continue
            m = lookup(r)[0]
            if not m or m / 10 <= up <= m * 10:
                continue
            best = min(opts, key=lambda p: abs(math.log(r["price"] / (base * p) / m)))
            best_up = round(r["price"] / (base * best), 4)
            if best != r["pack"] and m / 10 <= best_up <= m * 10:
                r["pack"], r["unit_price"] = best, best_up
                if "pack_resolved" not in r["flags"]:
                    r["flags"].append("pack_resolved")
                    changed += 1
                moved += 1
        if not moved:
            break
    for r in rows:
        r.pop("pack_options", None)
    return changed


if __name__ == "__main__":
    build()
