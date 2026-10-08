"""Acceptance gates, sample-review hand-off and publishing.

  python -m crawler.qa check             # evaluate the candidate: report.md, gates.json, review-sample.jsonl
  python -m crawler.qa finalize          # fold build/candidate/review-verdict.json (crawler/review.py) into the gates
  python -m crawler.qa publish           # promote the candidate when gates.json says "ready"
  python -m crawler.qa publish --approve # David's override: publish a held candidate after reading the report

check(wm) -> "ready" | "review" | "hold"      state.status: ready/review -> "built", hold -> "needs_review"
finalize() -> "ready" | "hold"
publish(approve=False) -> bool                 records price history (crawler/history.py) before replacing build/published

Thresholds live in data/gates.json (defaults below). A null threshold means measure-only: the gate is
measured and reported but never holds. gates.json records config_hash (sha256 of data/gates.json +
data/sentinels.json + data/categories.json) so the orchestrator can re-evaluate a hold after David edits
a threshold. A snapshot reaches the app only through `publish`; a hold keeps the previous snapshot live.
"""
import argparse, hashlib, json, os, random, shutil, statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import store, history, review
from .normalize import to_base
from .wm import Throttled

BUILD = store.ROOT / "build"
CAND, PUB = BUILD / "candidate", BUILD / "published"
STATE = store.ROOT / "state" / "run.json"
SIZING = store.ROOT / "sizing.json"
DATA = Path(__file__).resolve().parent.parent / "data"
SENTINELS = DATA / "sentinels.json"
GATES = DATA / "gates.json"

DEFAULTS = {
    "dept_size_tolerance": 0.30,        # pages crawled vs sizing total_pages; null = skip the comparison
    "sentinel_misses_max": 0,
    "live_sample": 500,                 # rows re-checked live against /items?ids=
    "live_match_min": 0.97,
    "size_parse_min": 0.85,             # share of Food rows with a parsed size (first real Food crawl measured 0.879)
    "unit_outliers_max": None,          # share of unit-priced rows outside [median/10, median*10]: measure-only until
                                        # size parsing improves (first real Food crawl measured 0.075); the rows are flagged
    "unit_outlier_group_min": 50,
    "price_drift_max": 0.02,            # share of rows whose price moved > 50% since the published snapshot
    "item_count_min_ratio": 0.90,
    "category_count_tolerance": 0.20,
    "category_count_min_rows": 200,
    "sample_review": {"required": True, "max_junk_rate": 0.05, "sample_size": 300},
    "audit_sample": 500,
    "audit_match_min": 0.95,
}
LIVE_CHUNK = 20
DETERMINISTIC = ("departments_complete", "sentinels", "live_match", "size_parse", "unit_outliers",
                 "price_drift", "item_count", "category_counts")
TRANSIENT_ERRORS = (Throttled, requests.RequestException, RuntimeError)
# candidate files that belong to one run's check; removed before a new check so nothing stale is read
CHECK_ARTIFACTS = ("gates.json", "report.md", "review-sample.jsonl", "review-verdict.json")


# ----------------------------------------------------------------------------- config

def gates_config() -> dict:
    """data/gates.json merged over DEFAULTS. Explicit nulls are kept (measure-only)."""
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    loaded = store.read_json(GATES, {}) or {}
    for k, v in loaded.items():
        if k == "note":
            continue
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


def config_hash() -> str:
    """sha256 over the bytes of data/gates.json, data/sentinels.json and data/categories.json (in that
    order; a missing file hashes as empty). Stored in gates.json; a changed hash means re-evaluate."""
    h = hashlib.sha256()
    for p in (GATES, SENTINELS, store.CONFIG):
        h.update(Path(p).read_bytes() if Path(p).exists() else b"")
        h.update(b"\0")
    return h.hexdigest()


def walmart_client():
    """A Walmart client when the environment has credentials, else None."""
    if os.environ.get("WM_CONSUMER_ID", "").strip() and os.environ.get("WM_PRIVATE_KEY", "").strip():
        from .wm import Walmart
        return Walmart()
    return None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _gate(passed, value, threshold, detail):
    return {"pass": passed, "value": value, "threshold": threshold, "detail": detail}


def _measured(ok, value, threshold, detail):
    """A gate with a numeric threshold: a null threshold measures only and never holds."""
    if threshold is None:
        return _gate(True, value, None, "measure-only: " + detail)
    return _gate(bool(ok), value, threshold, detail)


# ----------------------------------------------------------------------------- gates

def _text(r):
    return f"{r.get('brand') or ''} {r['name']}".lower()


def sentinel_check(rows):
    """Every sentinel must match a priced row: name+brand contain all tokens, size within 3% if given."""
    sents = json.loads(Path(SENTINELS).read_text())["sentinels"]
    results = []
    for s in sents:
        toks = [t.lower() for t in s["all"]]
        want = to_base(float(s["size"][0]), s["size"][1]) if s.get("size") else None
        hit = None
        for r in rows:
            if not isinstance(r.get("price"), (int, float)) or r["price"] <= 0:
                continue
            t = _text(r)
            if all(tok in t for tok in toks):
                if want and want[0]:
                    if r.get("base_unit") != want[1] or not r.get("base_qty") or abs(r["base_qty"] - want[0]) / want[0] > 0.03:
                        continue
                hit = r
                break
        results.append({"q": s["q"], "ok": hit is not None,
                        "match": f"{hit['name']} ${hit['price']}" if hit else None})
    return results


def gate_departments(state, stats, cfg_depts, sizing, tol):
    """Every department of the run finished and kept rows; pages within ±tol of sizing when sizing exists.
    Departments no longer in data/categories.json are ignored (process.build ignores them too)."""
    problems, checked = [], 0
    kept_by = stats.get("kept_by_department") or {}
    for d in state.get("departments") or []:
        dept = cfg_depts.get(d["id"])
        if not dept:
            continue
        checked += 1
        name = dept["name"]
        if d.get("status") != "done":
            problems.append(f"{name}: status {d.get('status')}")
        elif (kept_by.get(name) or 0) <= 0:
            problems.append(f"{name}: 0 items kept")
        tp = ((sizing or {}).get(d["id"]) or {}).get("total_pages")
        pages = d.get("pages")
        if tol is not None and isinstance(tp, (int, float)) and tp > 0 and isinstance(pages, (int, float)):
            dev = (pages - tp) / tp
            if abs(dev) > tol:
                problems.append(f"{name}: {pages} pages vs {tp} sized ({dev:+.0%})")
    detail = f"{checked} departments checked" + (f"; sizing {'used' if sizing else 'absent'}")
    if problems:
        detail += ": " + "; ".join(problems[:20])
    return _gate(not problems, len(problems), tol, detail)


def gate_sentinels(rows, max_misses):
    sres = sentinel_check(rows)
    misses = [s["q"] for s in sres if not s["ok"]]
    detail = f"{len(sres) - len(misses)}/{len(sres)} found and priced"
    if misses:
        detail += "; missing: " + ", ".join(misses[:20]) + (" ..." if len(misses) > 20 else "")
    return _measured(len(misses) <= (max_misses or 0), len(misses), max_misses, detail), misses


def live_sample_rows(rows, n, seed, include_carried=False):
    """The rows a live check may compare: primary listing for its UPC, in stock, not a promo price.
    The acceptance gate leaves out carried-over rows (not crawled in this run, so a price difference
    says nothing about the crawl); the weekly audit passes include_carried=True because stale
    carried-over prices are exactly what it looks for. Deterministic for a given seed."""
    pool = [r for r in rows if r.get("primary") and r.get("upc") and r.get("stock") == "Available"
            and "promo_price" not in (r.get("flags") or [])
            and (include_carried or "carried_over" not in (r.get("flags") or []))]
    pool.sort(key=lambda r: str(r["id"]))
    if len(pool) <= n:
        return pool
    return random.Random(str(seed)).sample(pool, n)


def live_check(wm, sample):
    """Compare snapshot prices with Walmart right now, LIVE_CHUNK ids per call. Stops at the first
    transport/throttle error and reports what it managed to check (error recorded, never raised)."""
    by_id = {str(r["id"]): r for r in sample}
    ids = list(by_id)
    res = {"sample": len(ids), "checked": 0, "exact": 0, "within_5pct": 0, "missing": 0, "calls": 0,
           "examples": [], "error": None}
    for i in range(0, len(ids), LIVE_CHUNK):
        chunk = ids[i:i + LIVE_CHUNK]
        try:
            items = wm.get_items(chunk)
        except TRANSIENT_ERRORS as e:
            res["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            break
        res["calls"] += 1
        live = {str(it.get("itemId")): it for it in items if isinstance(it, dict)}
        for iid in chunk:
            r, it = by_id[iid], live.get(iid)
            res["checked"] += 1
            if it is None or not isinstance(it.get("salePrice"), (int, float)):
                res["missing"] += 1
                res["examples"].append({"id": r["id"], "name": r["name"], "snapshot": r["price"], "live": None})
                continue
            diff = abs(float(r["price"]) - float(it["salePrice"]))
            if diff < 0.005:
                res["exact"] += 1
                res["within_5pct"] += 1
            else:
                if r["price"] and diff / float(r["price"]) <= 0.05:
                    res["within_5pct"] += 1
                res["examples"].append({"id": r["id"], "name": r["name"], "snapshot": r["price"],
                                        "live": float(it["salePrice"])})
    n = res["checked"]
    res["match_rate"] = round(res["exact"] / n, 4) if n else None
    res["within_5pct_rate"] = round(res["within_5pct"] / n, 4) if n else None
    res["examples"].sort(key=lambda e: -(abs(e["snapshot"] - e["live"]) / e["snapshot"] if e["live"] is not None and e["snapshot"] else 9e9))
    res["examples"] = res["examples"][:25]
    return res


def gate_live(rows, wm, cfg, seed):
    """Returns (gate, live_result, transient)."""
    n, min_rate = int(cfg.get("live_sample") or 0), cfg.get("live_match_min")
    if n <= 0:
        return _measured(False, None, min_rate, "not run: live_sample is 0"), None, False
    sample = live_sample_rows(rows, n, seed)
    if not sample:
        return _measured(False, None, min_rate, "no eligible rows (primary, UPC, in stock, no promo, crawled this run)"), None, False
    if wm is None:
        wm = walmart_client()
    if wm is None:
        return _measured(False, None, min_rate, "not run: no Walmart credentials in the environment (WM_CONSUMER_ID / WM_PRIVATE_KEY)"), None, False
    res = live_check(wm, sample)
    if res["checked"] < max(1, len(sample) / 2):
        detail = f"live check unavailable after {res['checked']}/{len(sample)} rows: {res['error']}"
        return _measured(False, None, min_rate, detail), res, True
    detail = (f"{res['exact']}/{res['checked']} exact ({res['match_rate']:.1%}), within 5%: {res['within_5pct_rate']:.1%}, "
              f"missing live: {res['missing']}, {res['calls']} calls")
    if res["error"]:
        detail += f"; stopped early: {res['error']}"
    ok = min_rate is None or res["match_rate"] >= min_rate
    return _measured(ok, res["match_rate"], min_rate, detail), res, False


def gate_size_parse(rows, min_rate):
    food = [r for r in rows if r.get("dept") == "Food"]
    if not food:
        return _gate(True, None, min_rate, "no Food rows to measure")
    parsed = sum(1 for r in food if isinstance(r.get("base_qty"), (int, float)) and r["base_qty"] > 0)
    rate = round(parsed / len(food), 4)
    return _measured(rate >= (min_rate or 0), rate, min_rate, f"{parsed}/{len(food)} Food rows with a parsed size ({rate:.1%})")


def unit_outlier_stats(rows, group_min=50):
    """Per (category, base_unit) group with >= group_min unit-priced rows: rows whose unit_price falls
    outside [median/10, median*10]. Returns (share of all unit-priced rows, total unit-priced rows, examples)."""
    groups = defaultdict(list)
    for r in rows:
        up = r.get("unit_price")
        if isinstance(up, (int, float)) and up > 0 and r.get("base_unit"):
            groups[(r.get("cat"), r["base_unit"])].append(r)
    total = sum(len(g) for g in groups.values())
    outliers = []
    for (cat, unit), g in groups.items():
        if len(g) < group_min:
            continue
        med = statistics.median(r["unit_price"] for r in g)
        if med <= 0:
            continue
        for r in g:
            if r["unit_price"] < med / 10 or r["unit_price"] > med * 10:
                outliers.append({"id": r["id"], "name": r.get("name"), "cat": cat, "unit": unit,
                                 "unit_price": r["unit_price"], "median": round(med, 4),
                                 "ratio": round(r["unit_price"] / med, 6)})
    # severity = how many times off the median in either direction; a ratio that rounds to 0 must not divide by zero
    outliers.sort(key=lambda o: -(o["ratio"] if o["ratio"] >= 1 else 1 / max(o["ratio"], 1e-9)))
    share = round(len(outliers) / total, 5) if total else 0.0
    return share, total, outliers


def gate_unit_outliers(rows, cfg, stats=None):
    """Share of unit-priced rows more than 10x off their category+unit median. process.build() already nulls and
    flags those rows (unit_price_suspect) so none reaches the app; it records the share it saw in
    stats["unit_outliers_raw"], which is what this gate measures. Without that record (older candidates) the
    rows are measured directly."""
    raw = (stats or {}).get("unit_outliers_raw")
    if raw and "share" in raw:
        share, total, outliers = raw["share"], raw.get("unit_priced_rows", 0), list(raw.get("examples") or [])
        count = raw.get("count", len(outliers))
    else:
        share, total, outliers = unit_outlier_stats(rows, int(cfg.get("unit_outlier_group_min") or 50))
        count = len(outliers)
    mx = cfg.get("unit_outliers_max")
    detail = (f"{count} of {total} unit-priced rows outside [median/10, median*10] of their category+unit group "
              f"({share:.2%}); their per-unit prices are dropped and the rows flagged unit_price_suspect")
    return _measured(share <= (mx if mx is not None else 1), share, mx, detail), outliers[:25]


def gates_vs_previous(rows, stats, prev, prev_stats, cfg):
    """price_drift, item_count, category_counts against the published snapshot (measure nothing without one)."""
    out, drift, unstable = {}, [], []
    if not prev:
        for name in ("price_drift", "item_count", "category_counts"):
            out[name] = _gate(True, None, cfg.get({"price_drift": "price_drift_max", "item_count": "item_count_min_ratio",
                                                   "category_counts": "category_count_tolerance"}[name]),
                              "no previous snapshot")
        return out, drift, unstable
    for r in rows:
        p = prev.get(r["id"])
        if p and isinstance(p.get("price"), (int, float)) and p["price"] > 0 and abs(r["price"] - p["price"]) / p["price"] > 0.5:
            drift.append({"id": r["id"], "name": r["name"], "old": p["price"], "new": r["price"]})
    share = round(len(drift) / len(rows), 5) if rows else 0.0
    mx = cfg.get("price_drift_max")
    out["price_drift"] = _measured(share <= (mx if mx is not None else 1), share, mx,
                                   f"{len(drift)} of {len(rows)} prices moved more than 50% ({share:.2%})")
    ratio = round(len(rows) / len(prev), 4)
    mn = cfg.get("item_count_min_ratio")
    out["item_count"] = _measured(ratio >= (mn or 0), ratio, mn, f"{len(rows)} items vs {len(prev)} published ({ratio:.1%})")
    tol, min_rows = cfg.get("category_count_tolerance"), int(cfg.get("category_count_min_rows") or 0)
    worst = 0.0
    for cat, n_prev in (prev_stats.get("kept_by_category") or {}).items():
        n = (stats.get("kept_by_category") or {}).get(cat, 0)
        if n_prev >= min_rows and n_prev > 0:
            dev = abs(n - n_prev) / n_prev
            worst = max(worst, dev)
            if tol is not None and dev > tol:
                unstable.append({"cat": cat, "old": n_prev, "new": n})
    detail = f"largest category change {worst:.1%} (categories with >= {min_rows} published rows)"
    if unstable:
        detail += "; over tolerance: " + ", ".join(f"cat {u['cat']} {u['old']}->{u['new']}" for u in unstable[:15])
    out["category_counts"] = _measured(not unstable, round(worst, 4), tol, detail)
    return out, drift, unstable


def gate_review_pending(sr):
    if not sr or not sr.get("required", True):
        return _gate(True, None, (sr or {}).get("max_junk_rate"), "not required (sample_review.required is false)")
    return _gate(None, None, sr.get("max_junk_rate"), "pending: `python -m crawler.review run`, then `qa finalize`")


def evaluate_review(verdict, run_id, sr):
    """The sample_review gate from build/candidate/review-verdict.json. Returns (gate, transient)."""
    required = bool(sr.get("required", True)) if sr else False
    max_junk = (sr or {}).get("max_junk_rate")
    status = (verdict or {}).get("status")
    if verdict and verdict.get("run_id") not in (None, run_id):
        verdict, status = None, None
    if not verdict:
        if required:
            return _gate(False, None, max_junk, "no review verdict for this run (run `python -m crawler.review run`)"), False
        return _gate(True, None, max_junk, "not required; no verdict for this run"), False
    reason = str(verdict.get("reason") or "")[:300]
    if status == "skipped":
        if required:
            return _gate(False, None, max_junk, f"review skipped: {reason or 'ANTHROPIC_API_KEY missing'} "
                                                "-> add the ANTHROPIC_API_KEY repository secret (or set sample_review.required false)"), False
        return _gate(True, None, max_junk, f"not required; review skipped: {reason}"), False
    if status in ("pass", "fail"):
        rate = verdict.get("junk_rate")
        rate = float(rate) if isinstance(rate, (int, float)) else None
        systematic = bool(verdict.get("systematic_junk"))
        ok = status == "pass" and not systematic and (max_junk is None or (rate is not None and rate <= max_junk))
        ex = verdict.get("junk_examples") or []
        detail = (f"junk rate {rate:.1%}" if rate is not None else "junk rate unknown") + \
                 f", systematic junk: {'yes' if systematic else 'no'}, {len(ex)} examples, model {verdict.get('model')}"
        notes = str(verdict.get("notes") or "").strip()
        if notes:
            detail += f"; notes: {notes[:400]}"
        return _gate(ok, rate, max_junk, detail), False
    # "error" or anything unknown: no usable verdict
    if required:
        return _gate(False, None, max_junk, f"review {status or 'unknown'}: {reason} (transient; re-run review and finalize)"), True
    return _gate(True, None, max_junk, f"not required; review {status or 'unknown'}: {reason}"), False


# ----------------------------------------------------------------------------- check / finalize / publish

def check(wm=None):
    state = store.read_json(STATE)
    if not state:
        raise SystemExit("no run state (state/run.json)")
    stats = store.read_json(CAND / "stats.json")
    if not stats or not (CAND / "items.jsonl.gz").exists():
        raise SystemExit("no candidate: run `python -m crawler.process` first")
    for f in CHECK_ARTIFACTS:
        p = CAND / f
        if p.exists():
            p.unlink()
    cfg = gates_config()
    run_id = state["run_id"]
    config = store.config()
    cfg_depts = {d["id"]: d for d in config["departments"]}
    rows = list(store.iter_jsonl_gz(CAND / "items.jsonl.gz"))
    prev = {r["id"]: r for r in store.iter_jsonl_gz(PUB / "items.jsonl.gz")} if (PUB / "items.jsonl.gz").exists() else {}
    prev_stats = store.read_json(PUB / "stats.json") or {}
    sizing = store.read_json(SIZING)

    gates, extras, transient = {}, {}, False
    gates["departments_complete"] = gate_departments(state, stats, cfg_depts, sizing, cfg.get("dept_size_tolerance"))
    gates["sentinels"], extras["sentinel_misses"] = gate_sentinels(rows, cfg.get("sentinel_misses_max"))
    gates["live_match"], live, t = gate_live(rows, wm, cfg, run_id)
    transient |= t
    extras["live"] = live
    gates["size_parse"] = gate_size_parse(rows, cfg.get("size_parse_min"))
    gates["unit_outliers"], extras["unit_outliers"] = gate_unit_outliers(rows, cfg, stats)
    vs, extras["drift"], extras["unstable"] = gates_vs_previous(rows, stats, prev, prev_stats, cfg)
    gates.update(vs)
    extras["drift"] = extras["drift"][:50]
    sr = cfg.get("sample_review")
    gates["sample_review"] = gate_review_pending(sr)

    passed = all(gates[n]["pass"] for n in DETERMINISTIC)
    if not passed:
        status = "hold"
    elif gates["sample_review"]["pass"] is None:
        status = "review"
    else:
        status = "ready"
    # only a hold caused solely by an unavailable live check is transient (a retry may clear it)
    transient = transient and status == "hold" and all(gates[n]["pass"] for n in DETERMINISTIC if n != "live_match")

    review.write_sample(rows, run_id, n=int((sr or {}).get("sample_size") or 300))
    g = {"run_id": run_id, "gates": gates, "passed_deterministic": passed, "status": status,
         "config_hash": config_hash(), "checked": _now(), "transient": transient, "thresholds": cfg, "extras": extras}
    store.write_json(CAND / "gates.json", g)
    report = _report(state, stats, g)
    (CAND / "report.md").write_text(report)
    state["status"] = "needs_review" if status == "hold" else "built"
    store.write_json(STATE, state)
    print(report)
    return status


def finalize():
    g = store.read_json(CAND / "gates.json")
    if not g:
        raise SystemExit("run `check` first")
    sr = (g.get("thresholds") or gates_config()).get("sample_review")
    verdict = store.read_json(CAND / "review-verdict.json")
    gate, transient = evaluate_review(verdict, g["run_id"], sr)
    g["gates"]["sample_review"] = gate
    status = "ready" if g.get("passed_deterministic") and gate["pass"] else "hold"
    g["status"], g["finalized"] = status, _now()
    # a hold is transient when a retry may clear it: the review errored while every deterministic gate
    # passed, or the check itself was already held only by an unavailable live check
    review_only_blocker = transient and bool(g.get("passed_deterministic"))
    g["transient"] = status == "hold" and (review_only_blocker or bool(g.get("transient")))
    store.write_json(CAND / "gates.json", g)
    state = store.read_json(STATE) or {"run_id": g["run_id"]}
    stats = store.read_json(CAND / "stats.json") or {}
    report = _report(state, stats, g)
    (CAND / "report.md").write_text(report)
    state["status"] = "needs_review" if status == "hold" else "built"
    store.write_json(STATE, state)
    print(report)
    return status


def publish(approve=False):
    g = store.read_json(CAND / "gates.json")
    if not g:
        raise SystemExit("run `check` first")
    if g["status"] != "ready" and not approve:
        what = "sample review pending: run `python -m crawler.review run` then `qa finalize`" if g["status"] == "review" \
            else "gates hold; previous snapshot stays live. Review build/candidate/report.md (or `publish --approve`)"
        print(what)
        return False
    stats = store.read_json(CAND / "stats.json")
    if not stats or not (CAND / "items.jsonl.gz").exists():
        raise SystemExit("no candidate snapshot to publish")
    run_id = stats["run_id"]
    if g.get("run_id") not in (None, run_id):
        raise SystemExit(f"gates.json is for run {g.get('run_id')} but the candidate is {run_id}: run `check` first")
    prev_manifest = store.read_json(PUB / "manifest.json") or {}
    prev_path = PUB / "items.jsonl.gz"
    today = _now()[:10]
    hist = history.record(store.iter_jsonl_gz(prev_path) if prev_path.exists() else None,
                          store.iter_jsonl_gz(CAND / "items.jsonl.gz"), run_id, today,
                          prev_run_id=prev_manifest.get("version"))
    if PUB.exists():
        shutil.rmtree(PUB)
    shutil.copytree(CAND, PUB)
    failed = [n for n, x in g["gates"].items() if x.get("pass") is False]
    now = _now()
    # full_published: when every department was last refreshed (a core publish carries the rest over from the
    # previous snapshot), so ci.decide() can start the monthly full crawl even while weekly core publishes continue
    full_published = now if str(run_id).endswith("-full") else (prev_manifest.get("full_published")
                                                                or prev_manifest.get("published"))
    manifest = {"version": run_id, "published": now, "full_published": full_published,
                "items": stats["items"], "upcs": stats["upcs"],
                "gates_passed": g["status"] == "ready", "approved_manually": bool(approve), "file": "items.jsonl.gz",
                "gates": {"status": g["status"], "passed_deterministic": g.get("passed_deterministic"), "failed": failed,
                          "config_hash": g.get("config_hash"), "checked": g.get("checked"),
                          "sample_review": g["gates"].get("sample_review")},
                "history": hist}
    store.write_json(PUB / "manifest.json", manifest)
    state = store.read_json(STATE) or {}
    if state.get("run_id") in (None, run_id):
        state["status"] = "published"
        store.write_json(STATE, state)
    else:
        # the state belongs to a newer run (a crawl in progress or finished and not yet built): leave it
        # untouched so that run keeps resuming; the published snapshot is this candidate's
        print(f"state belongs to run {state.get('run_id')} ({state.get('status')}); left untouched")
    print(f"published {manifest['version']}: {manifest['items']} items; history {hist['kind']} {hist['file']} ({hist['rows']} rows)")
    return True


# ----------------------------------------------------------------------------- report

def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _report(state, stats, g):
    status = g["status"]
    headline = {"ready": "all gates passed", "review": "deterministic gates passed; sample review pending",
                "hold": "HOLD - previous snapshot stays live"}.get(status, status)
    L = [f"# Snapshot report — {state.get('run_id', g.get('run_id'))}", "", f"Status: **{status}** ({headline})",
         f"Checked: {g.get('checked')}  |  config hash: {str(g.get('config_hash'))[:12]}" + ("  |  transient hold (retry may clear it)" if g.get("transient") else ""),
         "", "## Gates"]
    for name, x in g["gates"].items():
        mark = {True: "PASS", False: "FAIL", None: "PENDING"}[x.get("pass")]
        L.append(f"- {mark} {name} — value {_fmt(x.get('value'))}, threshold {_fmt(x.get('threshold'))}: {x.get('detail')}")
    if stats:
        L += ["", "## Totals",
              f"- items kept: {stats.get('items')}  |  UPCs: {stats.get('upcs')}  |  carried over: {stats.get('carried_over')}",
              f"- UPCs with conflicting prices (>1.5x): {stats.get('upc_price_conflicts')}", "", "## Kept by department"]
        for k, v in sorted((stats.get("kept_by_department") or {}).items(), key=lambda x: -x[1]):
            raw = (stats.get("raw_by_department") or {}).get(k)
            L.append(f"- {k}: {v} kept of {raw if raw is not None else 'carried'} raw")
        L += ["", "## Rejects by reason"]
        tot = Counter()
        for d in (stats.get("rejects_by_department") or {}).values():
            tot.update(d)
        L += [f"- {k}: {v}" for k, v in tot.most_common()]
        L += ["", "## Flags"] + [f"- {k}: {v}" for k, v in sorted((stats.get("flags") or {}).items(), key=lambda x: -x[1])]
    ex = g.get("extras") or {}
    if ex.get("sentinel_misses"):
        L += ["", "## Sentinels missing"] + [f"- MISSING: {m}" for m in ex["sentinel_misses"]]
    live = ex.get("live")
    if live and live.get("examples"):
        L += ["", f"## Live price differences (worst {len(live['examples'])} of {live.get('checked')} checked)"]
        L += [f"- {e['id']} {e['name']}: snapshot {e['snapshot']} -> live {e['live'] if e['live'] is not None else 'not found'}" for e in live["examples"]]
    if ex.get("unit_outliers"):
        L += ["", "## Unit-price outliers (worst 25)"]
        L += [f"- {o['id']} {o['name']}: {o['unit_price']}/{o['unit']} vs median {o['median']} (x{o['ratio']}), cat {o['cat']}" for o in ex["unit_outliers"]]
    if ex.get("unstable"):
        L += ["", "## Category count changes over tolerance"] + [f"- cat {u['cat']}: {u['old']} -> {u['new']}" for u in ex["unstable"]]
    if ex.get("drift"):
        L += ["", f"## Price changes > 50% (first {len(ex['drift'])})"] + [f"- {d['id']} {d['name']}: {d['old']} -> {d['new']}" for d in ex["drift"]]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("finalize")
    p = sub.add_parser("publish"); p.add_argument("--approve", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        check()
    elif a.cmd == "finalize":
        finalize()
    else:
        publish(a.approve)


if __name__ == "__main__":
    main()
