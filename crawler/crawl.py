"""Resumable department crawler.

  python -m crawler.crawl start --plan full|core   # begin a new run (keeps old snapshot live)
  python -m crawler.crawl run --budget-min 330      # continue current run until done / budget / throttled
  python -m crawler.crawl status                    # print progress

Every department is crawled page by page (200 items/page, soldByWmt=true) until Walmart
reports no next page. The cursor is saved after every page, so nothing is ever skipped
or re-fetched after an interruption.
"""
import argparse, json, sys, time
from datetime import datetime, timezone
from urllib.parse import quote

from . import store
from .wm import Walmart, Throttled

STATE = store.ROOT / "state" / "run.json"
PART_SIZE = 25_000          # items per raw part file (~3-5 MB gz)
CHECKPOINT_EVERY_S = 15 * 60


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def start(plan: str):
    cfg = store.config()
    depts = [d for d in cfg["departments"] if plan == "full" or d.get("core")]
    state = store.read_json(STATE)
    if state and state.get("status") == "crawling":
        print(f"run {state['run_id']} still in progress; use `run` to continue it")
        return state
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + f"-{plan}"
    # raw pages are only needed until a run is processed; keep the store small
    raw = store.ROOT / "raw"
    if raw.exists():
        import shutil
        shutil.rmtree(raw)
    state = {
        "run_id": run_id, "plan": plan, "status": "crawling", "started": now(), "updated": now(),
        "departments": [{"id": d["id"], "name": d["name"], "status": "pending", "next": None,
                         "pages": 0, "items": 0, "parts": 0, "total_pages": None} for d in depts],
        "calls": 0, "throttle_wait_s": 0,
    }
    store.write_json(STATE, state)
    store.checkpoint(f"start run {run_id}")
    print(f"started {run_id} with {len(depts)} departments")
    return state


def run(budget_min: float, wm: Walmart = None):
    state = store.read_json(STATE)
    if not state or state.get("status") != "crawling":
        print("no crawl in progress"); return "idle"
    wm = wm or Walmart()
    state["calls_base"] = state.get("calls", 0)
    state["throttle_base"] = state.get("throttle_wait_s", 0)
    deadline = time.time() + budget_min * 60
    last_ckpt = time.time()
    outcome = "done"
    for d in state["departments"]:
        if d["status"] == "done":
            continue
        d["status"] = "crawling"
        path = d["next"] or f"/paginated/items?category={quote(d['id'])}&soldByWmt=true"
        buf = []
        try:
            while path:
                if time.time() > deadline:
                    outcome = "budget"; break
                page = wm.get(path)
                items = page.get("items") or []
                buf.extend(store.slim(i) for i in items)
                d["pages"] += 1
                d["items"] += len(items)
                d["total_pages"] = page.get("totalPages", d["total_pages"])
                path = (page.get("nextPage") if page.get("nextPageExist", True) else None) or None
                d["next"] = path
                if len(buf) >= PART_SIZE or time.time() - last_ckpt > CHECKPOINT_EVERY_S:
                    _flush(state, d, buf); buf = []
                    _save(state, wm)
                    store.checkpoint(f"{state['run_id']} {d['name']} page {d['pages']}")
                    last_ckpt = time.time()
        except Throttled as e:
            outcome = "throttled"; print(f"paused: {e}")
        finally:
            # Items already fetched are always written together with the cursor that follows them.
            _flush(state, d, buf)
            _save(state, wm)
        if outcome != "done":
            break
        d["status"] = "done"; d["next"] = None
        print(f"[{now()}] {d['name']}: done, {d['pages']} pages, {d['items']} items")
        _save(state, wm)
        store.checkpoint(f"{state['run_id']} {d['name']} complete")
    if outcome == "done" and all(x["status"] == "done" for x in state["departments"]):
        state["status"] = "crawled"; state["crawled"] = now()
    _save(state, wm)
    store.checkpoint(f"{state['run_id']} {outcome}")
    print(f"outcome: {outcome}")
    return outcome


def _flush(state, d, buf):
    if not buf:
        return
    d["parts"] += 1
    p = store.ROOT / "raw" / state["run_id"] / d["id"] / f"part-{d['parts']:04d}.jsonl.gz"
    store.write_jsonl_gz(p, buf)


def _save(state, wm):
    state["updated"] = now()
    if wm is not None:
        state["calls"] = state.get("calls_base", 0) + wm.calls
        state["throttle_wait_s"] = int(state.get("throttle_base", 0) + wm.throttle_waited)
    store.write_json(STATE, state)


def status():
    state = store.read_json(STATE)
    if not state:
        print("no run yet"); return
    print(f"run {state['run_id']} plan={state['plan']} status={state['status']} updated={state['updated']}")
    for d in state["departments"]:
        tp = d.get("total_pages")
        pct = f"{100*d['pages']/tp:.0f}%" if tp else "?"
        print(f"  {d['status']:9} {d['name']:22} pages {d['pages']}/{tp or '?'} ({pct})  items {d['items']}")
    build = store.read_json(store.ROOT / "build" / "manifest.json")
    if build:
        print(f"published snapshot: {build.get('version')} items={build.get('items')} gates={build.get('gates_passed')}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("--plan", choices=["full", "core"], default="full")
    r = sub.add_parser("run"); r.add_argument("--budget-min", type=float, default=330)
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "start":
        start(a.plan)
    elif a.cmd == "run":
        out = run(a.budget_min)
        # exit code 0 always; outcome written for the workflow to read
        (store.ROOT / "state").mkdir(parents=True, exist_ok=True)
        (store.ROOT / "state" / "last_outcome").write_text(out)
    else:
        status()


if __name__ == "__main__":
    main()
