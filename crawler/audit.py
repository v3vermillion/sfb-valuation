"""Weekly live audit of the published snapshot.

  python -m crawler.audit            # sample published rows, re-check them live, write audit/<date>.json + latest.json

due(store_root, cfg, now) -> bool    audit/latest.json missing or older than cfg["audit_every_days"] (default 7)
run(wm=None) -> dict                 {"status", "match_rate", "within_5pct", "outlier_share", "alert", ...}
                                     alert = match_rate < data/gates.json audit_match_min (0.95); null = never alert
The sample uses the same selection rule as the live_match gate (qa.live_sample_rows: primary, UPC, in stock,
no promo price) but keeps carried-over rows, since stale prices on rows the weekly core crawl did not refresh
are what the audit is for. The seed changes daily, so successive audits look at different rows. Nothing is
written when the audit could not run ({"status": "skipped"|"error"}), so the next scheduled run tries again.
"""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import store, qa

AUDIT = store.ROOT / "audit"
PUB = store.ROOT / "build" / "published"


def _now():
    return datetime.now(timezone.utc)


def _parse(ts):
    if not isinstance(ts, str) or not ts:
        return None
    try:
        d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def due(store_root, cfg, now=None) -> bool:
    """True when no audit was recorded or the last one is older than audit_every_days. Unreadable input -> True."""
    now = now or _now()
    every = (cfg or {}).get("audit_every_days", 7)
    try:
        every = float(every)
    except (TypeError, ValueError):
        every = 7.0
    latest = store.read_json(Path(store_root) / "audit" / "latest.json")
    if not isinstance(latest, dict):
        return True
    checked = _parse(latest.get("checked"))
    if checked is None:
        return True
    return now - checked >= timedelta(days=every)


def run(wm=None, n=None) -> dict:
    manifest = store.read_json(PUB / "manifest.json")
    items = PUB / "items.jsonl.gz"
    if not manifest or not items.exists():
        res = {"status": "skipped", "reason": "no published snapshot", "alert": False}
        print(res["reason"])
        return res
    cfg = qa.gates_config()
    n = int(n or cfg.get("audit_sample") or 500)
    min_rate = cfg.get("audit_match_min")
    wm = wm or qa.walmart_client()
    if wm is None:
        res = {"status": "skipped", "reason": "no Walmart credentials in the environment", "alert": False}
        print(res["reason"])
        return res
    now = _now()
    date = now.strftime("%Y-%m-%d")
    rows = list(store.iter_jsonl_gz(items))
    sample = qa.live_sample_rows(rows, n, seed=f"audit-{manifest.get('version')}-{date}", include_carried=True)
    if not sample:
        res = {"status": "skipped", "reason": "no eligible rows in the published snapshot", "alert": False}
        print(res["reason"])
        return res
    live = qa.live_check(wm, sample)
    if live["checked"] < max(1, len(sample) / 2):
        res = {"status": "error", "alert": False, "checked_rows": live["checked"], "sample": len(sample),
               "reason": f"live check unavailable after {live['checked']}/{len(sample)} rows: {live['error']}"}
        print(f"audit not recorded: {res['reason']}")
        return res
    share, total, outliers = qa.unit_outlier_stats(rows, int(cfg.get("unit_outlier_group_min") or 50))
    res = {
        "status": "ok", "checked": now.isoformat(timespec="seconds"), "date": date, "version": manifest.get("version"),
        "published": manifest.get("published"), "sample": len(sample), "checked_rows": live["checked"],
        "calls": live["calls"], "exact": live["exact"], "missing": live["missing"],
        "match_rate": live["match_rate"], "within_5pct": live["within_5pct_rate"],
        "drift_examples": live["examples"], "live_error": live["error"],
        "outlier_share": share, "outlier_rows": len(outliers), "unit_priced_rows": total, "outlier_examples": outliers[:25],
        "audit_match_min": min_rate,
        "alert": bool(min_rate is not None and live["match_rate"] is not None and live["match_rate"] < min_rate),
    }
    store.write_json(AUDIT / f"{date}.json", res)
    store.write_json(AUDIT / "latest.json", res)
    print(f"audit {date} of {res['version']}: exact {res['match_rate']:.1%}, within 5% {res['within_5pct']:.1%}, "
          f"missing {res['missing']}, unit outliers {share:.2%}" + (" -> ALERT" if res["alert"] else ""))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None)
    a = ap.parse_args(argv)
    run(n=a.sample)


if __name__ == "__main__":
    main()
