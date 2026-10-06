"""Quality gates and publishing.

  python -m crawler.qa check            # evaluate candidate, write report, set state status
  python -m crawler.qa publish          # promote candidate if gates passed (and a snapshot exists)
  python -m crawler.qa publish --approve   # first snapshot (or a reviewed one): promote after human review

A snapshot reaches the app only through `publish`. Failed gates keep the previous snapshot live.
"""
import argparse, json, re, shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import store
from .normalize import to_base, parse_quantity

BUILD = store.ROOT / "build"
CAND, PUB = BUILD / "candidate", BUILD / "published"
SENTINELS = Path(__file__).resolve().parent.parent / "data" / "sentinels.json"


def _text(r):
    return f"{r.get('brand') or ''} {r['name']}".lower()


def sentinel_check(rows):
    sents = json.loads(SENTINELS.read_text())["sentinels"]
    results = []
    for s in sents:
        toks = [t.lower() for t in s["all"]]
        want = None
        if s.get("size"):
            want = to_base(float(s["size"][0]), s["size"][1])
        hit = None
        for r in rows:
            t = _text(r)
            if all(tok in t for tok in toks):
                if want and want[0]:
                    if r.get("base_unit") != want[1] or not r.get("base_qty") or abs(r["base_qty"] - want[0]) / want[0] > 0.03:
                        continue
                hit = r; break
        results.append({"q": s["q"], "ok": hit is not None,
                        "match": f"{hit['name']} ${hit['price']}" if hit else None})
    return results


def check():
    state = store.read_json(store.ROOT / "state" / "run.json")
    rows = list(store.iter_jsonl_gz(CAND / "items.jsonl.gz"))
    stats = store.read_json(CAND / "stats.json")
    prev = {r["id"]: r for r in store.iter_jsonl_gz(PUB / "items.jsonl.gz")} if (PUB / "items.jsonl.gz").exists() else {}
    prev_stats = store.read_json(PUB / "stats.json") or {}

    gates = {}
    gates["crawl_complete"] = all(d["status"] == "done" for d in state["departments"])
    sres = sentinel_check(rows)
    misses = [s for s in sres if not s["ok"]]
    gates["sentinels_all_found"] = not misses

    drift = []
    if prev:
        for r in rows:
            p = prev.get(r["id"])
            if p and p.get("price") and abs(r["price"] - p["price"]) / p["price"] > 0.5:
                drift.append((r["id"], r["name"], p["price"], r["price"]))
        gates["price_drift_under_2pct"] = len(drift) <= 0.02 * len(rows)
        gates["item_count_not_dropped"] = len(rows) >= 0.9 * len(prev)
        unstable = []
        for cat, n_prev in (prev_stats.get("kept_by_category") or {}).items():
            n = stats["kept_by_category"].get(cat, 0)
            if n_prev >= 200 and abs(n - n_prev) / n_prev > 0.2:
                unstable.append((cat, n_prev, n))
        gates["category_counts_within_20pct"] = not unstable
    else:
        unstable = []

    passed = all(gates.values())
    first = not prev
    status = "needs_review" if not passed else ("awaiting_approval" if first else "ready")
    report = _report(state, stats, gates, sres, misses, drift, unstable, status)
    (CAND / "report.md").write_text(report)
    store.write_json(CAND / "gates.json", {"gates": gates, "passed": passed, "status": status,
                                          "sentinel_misses": misses, "checked": _now()})
    state["status"] = status if status != "ready" else "built"
    store.write_json(store.ROOT / "state" / "run.json", state)
    print(report)
    return status


def publish(approve=False):
    g = store.read_json(CAND / "gates.json")
    if not g:
        raise SystemExit("run `check` first")
    if g["status"] == "needs_review" and not approve:
        print("gates failed; previous snapshot stays live. Review store/build/candidate/report.md"); return False
    if g["status"] == "awaiting_approval" and not approve:
        print("first snapshot: review report.md, then run `publish --approve`"); return False
    if PUB.exists():
        shutil.rmtree(PUB)
    shutil.copytree(CAND, PUB)
    stats = store.read_json(PUB / "stats.json")
    manifest = {"version": stats["run_id"], "published": _now(), "items": stats["items"], "upcs": stats["upcs"],
                "gates_passed": g["passed"], "approved_manually": approve, "file": "items.jsonl.gz"}
    store.write_json(PUB / "manifest.json", manifest)
    state = store.read_json(store.ROOT / "state" / "run.json")
    state["status"] = "published"
    store.write_json(store.ROOT / "state" / "run.json", state)
    print(f"published {manifest['version']}: {manifest['items']} items")
    return True


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _report(state, stats, gates, sres, misses, drift, unstable, status):
    L = [f"# Snapshot report — {state['run_id']}", "", f"Status: **{status}**", "", "## Gates"]
    L += [f"- {'PASS' if v else 'FAIL'} {k}" for k, v in gates.items()]
    L += ["", f"## Totals", f"- items kept: {stats['items']}  |  UPCs: {stats['upcs']}  |  carried over: {stats['carried_over']}",
          f"- UPCs with conflicting prices (>1.5x): {stats['upc_price_conflicts']}", "", "## Kept by department"]
    for k, v in sorted(stats["kept_by_department"].items(), key=lambda x: -x[1]):
        raw = stats["raw_by_department"].get(k)
        L.append(f"- {k}: {v} kept of {raw if raw is not None else 'carried'} raw")
    L += ["", "## Rejects by reason"]
    tot = Counter()
    for d in stats["rejects_by_department"].values():
        tot.update(d)
    L += [f"- {k}: {v}" for k, v in tot.most_common()]
    L += ["", "## Flags"] + [f"- {k}: {v}" for k, v in sorted(stats["flags"].items(), key=lambda x: -x[1])]
    L += ["", f"## Sentinels: {len(sres) - len(misses)}/{len(sres)} found"]
    L += [f"- MISSING: {m['q']}" for m in misses]
    if unstable:
        L += ["", "## Category count changes > 20%"] + [f"- cat {c}: {a} -> {b}" for c, a, b in unstable]
    if drift:
        L += ["", f"## Price changes > 50% ({len(drift)})"] + [f"- {i} {n}: {a} -> {b}" for i, n, a, b in drift[:50]]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    p = sub.add_parser("publish"); p.add_argument("--approve", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        check()
    else:
        publish(a.approve)


if __name__ == "__main__":
    main()
