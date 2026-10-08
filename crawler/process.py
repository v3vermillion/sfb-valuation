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

from . import store
from .normalize import normalize

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
    if prev_path.exists():
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
    from .qa import unit_outlier_stats, gates_config
    group_min = int(gates_config().get("unit_outlier_group_min") or 50)
    before_share, _, before = unit_outlier_stats(rows.values(), group_min)
    resolved = resolve_packs(rows.values(), group_min)
    raw_share, unit_priced, outliers = unit_outlier_stats(rows.values(), group_min)
    for o in outliers:
        r = rows[o["id"]]
        r["unit_price"] = None
        r["flags"].append("unit_price_suspect")
    unit_outliers_raw = {"share": raw_share, "unit_priced_rows": unit_priced, "count": len(outliers),
                         "examples": outliers[:25], "before_pack_resolution": {"share": before_share, "count": len(before)},
                         "pack_resolved": resolved}

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
    }
    store.write_json(out / "stats.json", stats)
    state["status"] = "built"
    store.write_json(store.ROOT / "state" / "run.json", state)
    print(f"candidate: {n} items, {len(by_upc)} UPCs, {carried} carried over")
    return stats


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
