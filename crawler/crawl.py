"""Resumable department crawler.

  python -m crawler.crawl start --plan full|core   # begin a new run (keeps old snapshot live)
  python -m crawler.crawl run --budget-min 330      # continue current run until done / budget / throttled
  python -m crawler.crawl status                    # print progress

Every department is crawled page by page (200 items/page, soldByWmt=true) until Walmart
reports no next page. The cursor is saved after every page, so nothing is ever skipped
or re-fetched after an interruption.

Pacing: `run` starts the Walmart client with the per-minute cap in state.pace.per_min (none on the
first run). The client's HTTP/sleep events are appended to store/throttle/<run_id>.events.jsonl at
every checkpoint; at the end of each invocation crawler/throttle.py analyses this invocation's
events, writes store/throttle/<run_id>.analysis.json and updates state.pace for the next one.
"""
import argparse, json, sys, time
from datetime import datetime, timezone
from urllib.parse import quote

from . import store, throttle
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
    # throttle logs and analyses of earlier runs go the same way; what they taught is in state.pace
    throttle_dir = store.ROOT / "throttle"
    if throttle_dir.exists():
        for p in throttle_dir.iterdir():
            if p.is_file() and not p.name.startswith(run_id):
                p.unlink()
    pace = (state or {}).get("pace")
    state = {
        "run_id": run_id, "plan": plan, "status": "crawling", "started": now(), "updated": now(),
        "departments": [{"id": d["id"], "name": d["name"], "status": "pending", "next": None,
                         "pages": 0, "items": 0, "parts": 0, "total_pages": None} for d in depts],
        "calls": 0, "throttle_wait_s": 0,
    }
    if pace:
        state["pace"] = pace
    store.write_json(STATE, state)
    store.checkpoint(f"start run {run_id}")
    print(f"started {run_id} with {len(depts)} departments")
    return state


def run(budget_min: float, wm: Walmart = None):
    state = store.read_json(STATE)
    if not state or state.get("status") != "crawling":
        print("no crawl in progress"); return "idle"
    cap = (state.get("pace") or {}).get("per_min")
    wm = wm or Walmart(max_per_min=cap)
    events = []                      # this invocation's throttle events (the file keeps the whole run's)
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
                    _save(state, wm, events)
                    store.checkpoint(f"{state['run_id']} {d['name']} page {d['pages']}")
                    last_ckpt = time.time()
        except Throttled as e:
            outcome = "throttled"; print(f"paused: {e}")
        finally:
            # Items already fetched are always written together with the cursor that follows them.
            _flush(state, d, buf)
            _save(state, wm, events)
        if outcome != "done":
            break
        d["status"] = "done"; d["next"] = None
        print(f"[{now()}] {d['name']}: done, {d['pages']} pages, {d['items']} items")
        _save(state, wm, events)
        store.checkpoint(f"{state['run_id']} {d['name']} complete")
    if outcome == "done" and all(x["status"] == "done" for x in state["departments"]):
        state["status"] = "crawled"; state["crawled"] = now()
    _pace(state, wm, events, cap)
    _save(state, wm, events)
    store.checkpoint(f"{state['run_id']} {outcome}")
    print(f"outcome: {outcome}")
    return outcome


def _flush(state, d, buf):
    if not buf:
        return
    d["parts"] += 1
    p = store.ROOT / "raw" / state["run_id"] / d["id"] / f"part-{d['parts']:04d}.jsonl.gz"
    store.write_jsonl_gz(p, buf)


def _save(state, wm, events=None):
    state["updated"] = now()
    if wm is not None:
        state["calls"] = state.get("calls_base", 0) + wm.calls
        state["throttle_wait_s"] = int(state.get("throttle_base", 0) + wm.throttle_waited)
        if events is not None:
            _drain(state, wm, events)
    store.write_json(STATE, state)


def _events_path(run_id):
    return store.ROOT / "throttle" / f"{run_id}.events.jsonl"


def _drain(state, wm, events):
    """Move the client's new events into this invocation's list and append them to the run's log."""
    drain = getattr(wm, "drain_events", None)
    if drain is None:
        return
    new = drain()
    if not new:
        return
    events.extend(new)
    p = _events_path(state["run_id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write("".join(json.dumps(list(e), separators=(",", ":")) + "\n" for e in new))


def _pace(state, wm, events, cap):
    """Judge this invocation's 429s and set the cap the next invocation starts with.
    The analysis is advice, never a dependency: whatever goes wrong in it is printed and the crawl's
    state is saved as usual with the previous pace."""
    if getattr(wm, "drain_events", None) is None:
        return
    _drain(state, wm, events)
    try:
        a = throttle.analyze(events, cap=cap)
        stats = getattr(wm, "stats", None)
        a.update(run_id=state["run_id"], analyzed=now(), client=stats() if stats else None)
        path = store.ROOT / "throttle" / f"{state['run_id']}.analysis.json"
        doc = store.read_json(path) or {"run_id": state["run_id"], "invocations": []}
        doc["invocations"].append(a)
        doc["totals"] = _totals(doc["invocations"])
        store.write_json(path, doc)
        keep = ("requests", "ok", "status_429", "sleep_s", "span_s", "ok_per_min", "pattern",
                "limit_per_min", "limit_from_429s", "limit_per_min_median", "safe_per_min", "consistent", "reason")
        state["pace"] = {"per_min": cap if a["per_min"] is None else a["per_min"],
                         "inferred": {k: a.get(k) for k in keep}, "updated": now(), "run_id": state["run_id"]}
        print(throttle.report(a))
    except Exception as e:  # noqa: BLE001 - the crawl must finish and save even when the analysis cannot
        print(f"pace: analysis failed ({e!r}); keeping {cap or 'no'} cap")


def _totals(invocations):
    """Whole-run sums over the invocations analysed so far (span_s = active crawl time, not wall time)."""
    keys = ("requests", "ok", "status_429", "status_5xx", "network_errors", "sleep_s", "span_s")
    t = {k: sum(a.get(k) or 0 for a in invocations) for k in keys}
    t["sleep_s"] = round(t["sleep_s"], 1); t["span_s"] = round(t["span_s"], 1)
    t["ok_per_min"] = round(t["ok"] / (t["span_s"] / 60), 2) if t["span_s"] > 0 else None
    t["invocations"] = len(invocations)
    return t


def status():
    state = store.read_json(STATE)
    if not state:
        print("no run yet"); return
    print(f"run {state['run_id']} plan={state['plan']} status={state['status']} updated={state['updated']}")
    for d in state["departments"]:
        tp = d.get("total_pages")
        pct = f"{100*d['pages']/tp:.0f}%" if tp else "?"
        print(f"  {d['status']:9} {d['name']:22} pages {d['pages']}/{tp or '?'} ({pct})  items {d['items']}")
    pace = state.get("pace")
    if pace:
        inf = pace.get("inferred") or {}
        cap = f"{pace['per_min']}/min cap" if pace.get("per_min") else "no cap"
        print(f"pace: {cap} (set {pace.get('updated')} after run {pace.get('run_id')}: "
              f"{inf.get('status_429', '?')} x 429, pattern {inf.get('pattern') or '-'}, "
              f"inferred limit {inf.get('limit_per_min') or '-'}/min)")
    else:
        print("pace: no cap yet (1.25 s request interval only)")
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
