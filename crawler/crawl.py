"""Resumable department crawler.

  python -m crawler.crawl start --plan full|core   # begin a new run (keeps old snapshot live)
  python -m crawler.crawl run --budget-min 330      # continue current run until done / budget / throttled
  python -m crawler.crawl status                    # print progress

Every department is crawled page by page (200 items/page, soldByWmt=true) until Walmart
reports no next page; a department with `split` in data/categories.json is crawled as those child
nodes, one cursor each. The cursor is saved after every page, so nothing is ever skipped
or re-fetched after an interruption. An edit of data/categories.json applies to the run in progress
(sync()). A crawl that Walmart ends well short of its own page count is `truncated`, never `done`.

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
EARLY_END_HITS = 1000       # an "end" with more hits than this still to come is retried from the next cursor
MAX_FORGED = 3              # ... at most this many continuation pages in a row before the end is accepted
DEFAULT_TOLERANCE = 0.3     # when data/gates.json has no dept_size_tolerance
FINAL = ("done", "truncated", "failed", "dropped")


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
        "departments": [_new_dept(d) for d in depts],
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
    changes = sync(state)
    for c in changes:
        print(f"[{now()}] scope: {c}")
    if changes:
        store.write_json(STATE, state)
        store.checkpoint(f"{state['run_id']} scope: " + "; ".join(changes)[:200])
    cap = (state.get("pace") or {}).get("per_min")
    wm = wm or Walmart(max_per_min=cap)
    events = []                      # this invocation's throttle events (the file keeps the whole run's)
    state["calls_base"] = state.get("calls", 0)
    state["throttle_base"] = state.get("throttle_wait_s", 0)
    deadline = time.time() + budget_min * 60
    last_ckpt = time.time()
    tol = _tolerance()
    outcome = "done"
    # the department with a saved cursor first, so a scope edit that restarts another one never delays it
    order = sorted(state["departments"], key=lambda x: x["status"] != "crawling")
    for d in order:
        if d["status"] in FINAL:
            continue
        for unit in d.get("units") or [None]:
            t = unit if unit is not None else d
            if t["status"] in FINAL:
                continue
            outcome, last_ckpt = _crawl_target(state, d, t, unit, wm, deadline, events, tol, last_ckpt)
            if outcome not in ("done", "truncated", "failed"):
                break
            t["status"] = outcome; t["next"] = None
            label = f"{d['name']} / {t['name']}" if unit is not None else d["name"]
            tp = t.get("total_pages")
            print(f"[{now()}] {label}: {outcome}, {t['pages']} pages of {tp if tp is not None else '?'}, {t['items']} items")
            _rollup(d)
            _save(state, wm, events)
            store.checkpoint(f"{state['run_id']} {label} {'complete' if outcome == 'done' else outcome}")
            outcome = "done"
        if outcome != "done":
            break

    if outcome == "done" and all(x["status"] in FINAL for x in state["departments"]):
        state["status"] = "crawled"; state["crawled"] = now()
    _pace(state, wm, events, cap)
    _save(state, wm, events)
    store.checkpoint(f"{state['run_id']} {outcome}")
    print(f"outcome: {outcome}")
    return outcome


def truncated(state):
    """Departments (or child nodes) whose crawl ended well short of Walmart's own page count, or that Walmart refused."""
    out = []
    for d in (state or {}).get("departments") or []:
        for t in d.get("units") or [d]:
            label = f"{d['name']} / {t['name']}" if d.get("units") else d["name"]
            if t.get("status") == "truncated":
                out.append(f"{label}: {t.get('pages')} of {t.get('total_pages')} pages")
            elif t.get("status") == "failed":
                out.append(f"{label}: refused by Walmart ({t.get('error')})")
    return out


def _new_unit(u):
    return {"id": str(u["id"]), "name": u["name"], "status": "pending", "next": None,
            "pages": 0, "items": 0, "parts": 0, "total_pages": None}


def _new_dept(d):
    """State entry for a department; one with `split` in data/categories.json is crawled as those child nodes."""
    entry = {"id": d["id"], "name": d["name"], "status": "pending", "next": None,
             "pages": 0, "items": 0, "parts": 0, "total_pages": None}
    if d.get("split"):
        entry["units"] = [_new_unit(u) for u in d["split"]]
    return entry


def _raw_dir(state, d, unit=None):
    base = store.ROOT / "raw" / state["run_id"] / d["id"]
    return base / unit["id"] if unit is not None else base


def _rollup(d):
    """A split department's counters are the sums of its units; it is done when every unit is."""
    units = d.get("units")
    if not units:
        return
    d["pages"] = sum(u["pages"] for u in units)
    d["items"] = sum(u["items"] for u in units)
    d["parts"] = sum(u["parts"] for u in units)
    tps = [u.get("total_pages") for u in units]
    d["total_pages"] = sum(tps) if all(isinstance(t, int) for t in tps) else None
    d["next"] = None
    st = {u["status"] for u in units}
    if st <= {"done"}:
        d["status"] = "done"
    elif st <= {"done", "truncated", "failed"}:
        d["status"] = "failed" if "failed" in st else "truncated"
    elif st == {"pending"}:
        d["status"] = "pending"
    else:
        d["status"] = "crawling"


def sync(state, cfg=None):
    """Bring a run in progress in line with data/categories.json (a scope edit applies to the crawl already running):
      - a department no longer configured and not finished is `dropped` (never crawled further, never built);
      - a department that gained, lost or changed `split` restarts as its child nodes (its raw pages are discarded);
      - a split department keeps finished units; a new unit is added pending, a removed one and its pages go.
    Departments already finished and unchanged are untouched. Returns a list of what changed (printed by run())."""
    cfg = cfg or store.config()
    want = {d["id"]: d for d in cfg["departments"]}
    changes = []
    for d in state["departments"]:
        c = want.get(d["id"])
        if c is None:
            if d["status"] not in ("done", "dropped"):
                d["status"] = "dropped"; d["next"] = None
                changes.append(f"{d['name']}: dropped (no longer in data/categories.json)")
            continue
        split = [str(u["id"]) for u in c.get("split") or []]
        have = [u["id"] for u in d.get("units") or []]
        if split == have:
            continue
        if split and have:
            keep = [u for u in d["units"] if u["id"] in split]
            for u in d["units"]:
                if u["id"] not in split:
                    import shutil
                    shutil.rmtree(_raw_dir(state, d, u), ignore_errors=True)
            known = {u["id"] for u in keep}
            d["units"] = keep + [_new_unit(u) for u in c["split"] if str(u["id"]) not in known]
            d["units"].sort(key=lambda u: split.index(u["id"]))
            _rollup(d)
            changes.append(f"{d['name']}: child nodes now {', '.join(u['name'] for u in d['units'])}")
            continue
        import shutil
        shutil.rmtree(_raw_dir(state, d), ignore_errors=True)
        fresh = _new_dept(c)
        d.clear(); d.update(fresh)
        changes.append(f"{d['name']}: restarted " + ("as child nodes " + ", ".join(u["name"] for u in d["units"])
                                                     if d.get("units") else "as one department"))
    if state.get("plan") == "full":
        have = {d["id"] for d in state["departments"]}
        for c in cfg["departments"]:
            if c["id"] not in have:
                state["departments"].append(_new_dept(c))
                changes.append(f"{c['name']}: added")
    return changes


def _tolerance():
    """data/gates.json dept_size_tolerance: how far short of Walmart's own page count a crawl may end and still be done."""
    try:
        tol = json.loads((store.CONFIG.parent / "gates.json").read_text()).get("dept_size_tolerance")
    except (OSError, ValueError):
        tol = None
    return tol if isinstance(tol, (int, float)) and 0 < tol < 1 else DEFAULT_TOLERANCE


def _query(path):
    from urllib.parse import parse_qs, urlsplit
    return {k: v[-1] for k, v in parse_qs(urlsplit(path).query).items()}


def _continuation(path, items):
    """The cursor Walmart would have returned after this page: same query, lastDoc = the last item id fetched,
    remainingHits reduced by the page. None when the request carried no lastDoc cursor to continue from."""
    from urllib.parse import urlencode, urlsplit, urlunsplit
    q = _query(path)
    if "lastDoc" not in q:
        return None
    ids = [i.get("itemId") for i in items if isinstance(i, dict) and isinstance(i.get("itemId"), int)]
    if ids:
        q["lastDoc"] = str(max(ids))
    try:
        q["remainingHits"] = str(max(int(q.get("remainingHits", 0)) - len(items), 0))
    except ValueError:
        q.pop("remainingHits", None)
    parts = urlsplit(path)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q, safe=","), parts.fragment))


def _hits_left(path, items):
    try:
        return int(_query(path).get("remainingHits")) - len(items)
    except (TypeError, ValueError):
        return None


def _crawl_target(state, d, t, unit, wm, deadline, events, tol, last_ckpt):
    """Crawl one cursor (a department, or one child node of a split department) until Walmart reports the end, the
    budget runs out or Walmart throttles. Returns (outcome, last_ckpt); outcome is done | truncated | failed (Walmart
    answered the first page with 400/404: no such category) | budget | throttled.

    Walmart's paginated listing has been seen to stop early: Home (2026-10-08) got nextPageExist=false on page 1830
    of 31,781 with 6M hits still to come. An end that comes with many hits left is retried once from the cursor
    Walmart would have given (lastDoc = the last item id); an end short of (1 - dept_size_tolerance) x Walmart's page
    count is recorded as `truncated` instead of `done`, so the build gate and an alert say so instead of a silent gap."""
    t["status"] = "crawling"
    path = t["next"] or f"/paginated/items?category={quote(t['id'])}&soldByWmt=true"
    buf = []
    outcome = "done"
    forges = 0                       # continuation pages in a row without a cursor from Walmart
    try:
        while path:
            if time.time() > deadline:
                outcome = "budget"; break
            forged = path == t.get("resume")
            try:
                page = wm.get(path)
            except RuntimeError as e:
                if forged:
                    print(f"[{now()}] {t['name']}: continuation cursor refused ({e}); ending here")
                    page = {"items": [], "nextPageExist": False}
                elif t["pages"] == 0 and str(e).startswith(("HTTP 400 ", "HTTP 404 ")):
                    # Walmart refuses the category itself (a child node id that does not exist): this department or
                    # node fails on its own, the rest of the crawl goes on, and the gate and an alert say so
                    t["error"] = str(e)[:300]
                    outcome = "failed"; break
                else:
                    raise
            if not isinstance(page, dict):
                # a 200 whose JSON body is null or a list: never a crash mid-department, retried by the next run
                raise RuntimeError(f"unexpected Walmart answer for {path}: {type(page).__name__}")
            items = page.get("items") or []
            buf.extend(store.slim(i) for i in items)
            if items or not forged:     # an empty answer to a continuation is no page, and its page count no measure
                t["pages"] += 1
                t["items"] += len(items)
                if isinstance(page.get("totalPages"), int) and not isinstance(page.get("totalPages"), bool):
                    t["total_pages"] = page["totalPages"]
            nxt = (page.get("nextPage") if page.get("nextPageExist", True) else None) or None
            left = _hits_left(path, items)
            forges = forges + 1 if forged else 0
            if nxt is None and items and left is not None and left > EARLY_END_HITS and forges < MAX_FORGED:
                nxt = _continuation(path, items)
                if nxt:
                    print(f"[{now()}] {t['name']}: Walmart reported the end with {left} hits left; retrying from {nxt}")
                    t["resume"] = nxt
            path = nxt
            t["next"] = path
            if len(buf) >= PART_SIZE or time.time() - last_ckpt > CHECKPOINT_EVERY_S:
                _flush(state, d, buf, unit); buf = []
                _rollup(d)
                _save(state, wm, events)
                store.checkpoint(f"{state['run_id']} {t['name']} page {t['pages']}")
                last_ckpt = time.time()
    except Throttled as e:
        outcome = "throttled"; print(f"paused: {e}")
    finally:
        # Items already fetched are always written together with the cursor that follows them.
        _flush(state, d, buf, unit)
        _rollup(d)
        _save(state, wm, events)
    if outcome == "done":
        t.pop("resume", None)
        tp = t.get("total_pages")
        if isinstance(tp, int) and tp > 0 and t["pages"] < (1 - tol) * tp:
            outcome = "truncated"
    return outcome, last_ckpt


def _flush(state, d, buf, unit=None):
    if not buf:
        return
    t = unit if unit is not None else d
    t["parts"] += 1
    p = _raw_dir(state, d, unit) / f"part-{t['parts']:04d}.jsonl.gz"
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
        for t, ind in [(d, "")] + [(u, "  - ") for u in d.get("units") or []]:
            tp = t.get("total_pages")
            pct = f"{100*t['pages']/tp:.0f}%" if tp else "?"
            print(f"  {t['status']:9} {ind}{t['name']:22} pages {t['pages']}/{tp or '?'} ({pct})  items {t['items']}")
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
