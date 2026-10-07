"""Department sizing: one cheap call per department records how many pages Walmart reports.

  python -m crawler.sizing          # WM_CONSUMER_ID / WM_PRIVATE_KEY set, SFB_STORE pointing at the store

Writes store/sizing.json (flat, keyed by department id):
  {"976759": {"name": "Food", "total_pages": 512, "first_page_items": 200, "est_items": 102400,
              "checked": "2026-10-07T18:00:00+00:00"}, ...}
A department whose call failed with anything but rate limiting keeps an entry with "error" set and
total_pages null, so the file is always complete; ci.decide() retries such entries after a day.
Rate limiting (wm.Throttled) propagates so the run ends the way a throttled crawl does.

Consumers: the departments_complete gate (crawled pages vs. total_pages) and ci.decide(), which asks
for a new sizing pass every schedule.sizing_every_days or when a department is missing from the file.
About 23 calls, paced by the shared Walmart client exactly like the crawl.
"""
from datetime import datetime, timezone
from urllib.parse import quote

from . import store
from .wm import Throttled

ITEMS_PER_PAGE = 200
FILE = "sizing.json"


def path():
    return store.ROOT / FILE


def run(wm, cfg=None, now=None) -> dict:
    """Size every department in data/categories.json with one call each and write store/sizing.json."""
    cfg = cfg or store.config()
    stamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    result = {}
    for d in cfg["departments"]:
        rec = {"name": d["name"], "total_pages": None, "first_page_items": 0, "est_items": None, "checked": stamp}
        try:
            page = wm.get(f"/paginated/items?category={quote(str(d['id']))}&soldByWmt=true")
        except Throttled:
            raise
        except Exception as e:  # one bad department must not hide the others
            rec["error"] = f"{type(e).__name__}: {e}"[:300]
        else:
            tp = page.get("totalPages") if isinstance(page, dict) else None
            items = (page.get("items") if isinstance(page, dict) else None) or []
            if isinstance(tp, int) and not isinstance(tp, bool) and tp >= 0:
                rec["total_pages"] = tp
                rec["est_items"] = tp * ITEMS_PER_PAGE
            rec["first_page_items"] = len(items)
        result[str(d["id"])] = rec
    store.write_json(path(), result)
    print(table(result))
    return result


def table(sizing: dict) -> str:
    L = [f"{'dept':>8}  {'name':<26} {'pages':>6} {'est items':>10}  {'page 1':>6}", "-" * 64]
    total = 0
    for did, r in sorted(sizing.items(), key=lambda kv: -(kv[1].get("est_items") or 0)):
        tp, est = r.get("total_pages"), r.get("est_items")
        total += est or 0
        note = f"  ERROR {r['error']}" if r.get("error") else ""
        L.append(f"{did:>8}  {r.get('name', ''):<26} {tp if tp is not None else '?':>6} "
                 f"{est if est is not None else '?':>10}  {r.get('first_page_items', 0):>6}{note}")
    L.append("-" * 64)
    L.append(f"{'':>8}  {'estimated total':<26} {'':>6} {total:>10}")
    return "\n".join(L)


if __name__ == "__main__":
    from .wm import Walmart
    run(Walmart())
