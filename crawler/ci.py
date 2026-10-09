"""Single entry point for GitHub Actions (and for Claude Code): one Walmart budget, one queue.

  python -m crawler.ci --plan continue|full|core|approve|identify|audit|size|status|peek|finish [--budget-min N]

continue  (default) do the one thing the data-store asks for, chosen by decide(): size, crawl, build,
          recheck, start-full, start-core, audit, identify or none. Safe to run at any time.
full/core start a crawl of every / the core departments (resumes instead when one is in progress)
approve   publish the current candidate although the gates hold (manual override)
identify  refresh the Open Food Facts identification data and the equivalent prices
audit     live re-check of a sample of published prices (crawler/audit.py)
size      one call per department to record Walmart's page counts (crawler/sizing.py)
status    print progress and what the next `continue` would do
peek      no side effects: print `work=<kind>` from whatever small files exist under $SFB_STORE
          (the workflow fetches them through the API before checking the branch out); also raises the
          stale-prices alert. A kind of `inspect` means state/run.json is unreadable: run the full job so
          it fails loudly instead of guessing.
finish    after `python -m crawler.review run`: qa.finalize() then publish or hold

Decision order, thresholds from data/schedule.json: see decide().

Outputs written to $GITHUB_OUTPUT (every run writes all of them):
  work            the kind of work chosen (decide() result, or the plan name)
  next            `continue` when another run should be chained right away (crawl paused on budget or
                  by Walmart rate limiting, crawl finished, snapshot published); `full`/`core` when that manual plan found a finished
                  crawl waiting to be built and built it first; else empty
  review          `pending` when a sample review + `--plan finish` must follow, else `none`
  alert           alert key to open/update, or `none`
  alert_title     issue title (after the "[key]" prefix)
  alert_body_file absolute path of a markdown file holding the body (outside the store)
  resolve         comma-separated alert keys whose condition cleared this run (may be empty)

Alert keys (one GitHub issue per key, label pipeline-alert, see .github/actions/alert):
  pipeline-failed     the workflow failed (raised by the workflow's `if: failure()` step, resolved by the
                      next successful run)
  gates-hold          the candidate snapshot is held by the gates; body = build/candidate/report.md
  review-key-invalid  the sample review's API call was rejected: invalid/revoked key (401) or no permission (403)
  review-credits      the sample review's API call failed because the Anthropic account is out of credits
  review-key-missing  the sample review was skipped because ANTHROPIC_API_KEY is not set, so the
                      snapshot is held
  audit-regression    the weekly live audit found the published prices drifting (audit.run alert flag)
  data-store-size     the files on the data-store branch passed 1 GB (store.STORE_ALERT_BYTES)
  snapshot-archive    a published snapshot could not be kept as a GitHub Release for rollback
  audit-failed        the live audit could not reach Walmart (an HTTP 4xx at once, else AUDIT_ERRORS_ALERT attempts)
  stale-prices        the published snapshot is older than schedule.stale_days and no crawl is running
  throttled           three or more consecutive crawl runs ended rate limited (state.throttled_runs)
  deploy-failed / deploy-mismatch   raised by deploy-app.yml
  tests-failed        raised by tests.yml on main
Resolution: published -> gates-hold, review-key-missing, review-key-invalid, review-credits, stale-prices; crawl progress -> throttled;
audit ok -> audit-regression, audit-failed; a successful run -> pipeline-failed (done by the workflow).

Local use: WM_CONSUMER_ID / WM_PRIVATE_KEY set and SFB_STORE pointing at a data-store checkout.
"""
import argparse, shutil, hashlib, inspect, json, os, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import crawl, process, qa, identify, store

DATA = Path(__file__).resolve().parent.parent / "data"
SCHEDULE = DATA / "schedule.json"
CONFIG_FILES = (DATA / "gates.json", DATA / "sentinels.json", DATA / "categories.json")
SCHEDULE_DEFAULTS = {"full_every_days": 30, "core_every_days": 7, "audit_every_days": 7, "identify_every_days": 30,
                     "sizing_every_days": 30, "stale_days": 14, "budget_min": 300}
KINDS = ("size", "crawl", "build", "recheck", "start-full", "start-core", "audit", "identify", "none")
PLANS = ("continue", "full", "core", "approve", "identify", "audit", "size", "status", "peek", "finish", "rollback")
# gates.json statuses that mean "held, waiting for a decision" (new qa: hold; old qa: needs_review / awaiting_approval)
HOLD_STATUSES = ("hold", "needs_review", "awaiting_approval")
CANDIDATE_STATES = ("built", "needs_review", "awaiting_approval")
THROTTLED_ALERT_AFTER = 3
SIZING_ERROR_RETRY_DAYS = 1
# a hold that qa marked transient (live check or review could not run) is re-checked this often, not every 30 min
TRANSIENT_RETRY_HOURS = 6
AUDIT_ERRORS_ALERT = 3          # consecutive failed audit attempts (one per TRANSIENT_RETRY_HOURS) before audit-failed
PUBLISH_RESOLVES = ("gates-hold", "review-key-missing", "review-key-invalid", "review-credits", "stale-prices")

# store paths (functions, so a reloaded store.ROOT is honoured)
_state_path = lambda: store.ROOT / "state" / "run.json"
_manifest_path = lambda: store.ROOT / "build" / "published" / "manifest.json"
_gates_path = lambda: store.ROOT / "build" / "candidate" / "gates.json"
_report_path = lambda: store.ROOT / "build" / "candidate" / "report.md"
_verdict_path = lambda: store.ROOT / "build" / "candidate" / "review-verdict.json"
_sizing_path = lambda: store.ROOT / "sizing.json"
_audit_path = lambda: store.ROOT / "audit" / "latest.json"
_identify_path = lambda: store.ROOT / "identify" / "latest.json"


# ----------------------------------------------------------------------------- outputs

OUTPUT_KEYS = ("work", "next", "review", "alert", "alert_title", "alert_body_file", "resolve")
_outputs = {}


def _reset_outputs(work):
    _outputs.clear()
    _outputs.update({"work": work, "next": "", "review": "none", "alert": "none", "alert_title": "", "alert_body_file": "",
                     "resolve": []})


def out(key, val):
    """Append one key to $GITHUB_OUTPUT (kept for callers; the plan paths use set_out/flush_outputs)."""
    p = os.environ.get("GITHUB_OUTPUT")
    if p:
        with open(p, "a") as f:
            f.write(f"{key}={val}\n")


def set_out(key, val):
    _outputs[key] = val


def resolve(*keys):
    for k in keys:
        if k not in _outputs["resolve"]:
            _outputs["resolve"].append(k)


def alert(key, title, body):
    """Raise one alert for this run (the first one wins; a later call is logged, not lost silently)."""
    if _outputs.get("alert") not in (None, "none"):
        print(f"alert {key} not raised: {_outputs['alert']} already raised this run")
        return
    tmp = Path(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir())
    tmp.mkdir(parents=True, exist_ok=True)
    p = tmp / f"sfb-alert-{key}.md"
    p.write_text(body if body.endswith("\n") else body + "\n")
    _outputs.update({"alert": key, "alert_title": title, "alert_body_file": str(p)})
    print(f"alert: [{key}] {title}")


def flush_outputs():
    for k in OUTPUT_KEYS:
        v = _outputs.get(k, "")
        if k == "resolve":
            v = ",".join(v or [])
        out(k, v)


def summary(text):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a") as f:
            f.write(text + "\n")
    print(text)


# ----------------------------------------------------------------------------- inputs

def schedule():
    """data/schedule.json over the defaults; an unreadable file falls back to the defaults."""
    cfg = dict(SCHEDULE_DEFAULTS)
    try:
        raw = json.loads(SCHEDULE.read_text()) if SCHEDULE.exists() else {}
    except (OSError, ValueError) as e:
        print(f"warning: {SCHEDULE} unreadable ({e}); using defaults")
        raw = {}
    for k in SCHEDULE_DEFAULTS:
        v = raw.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
            cfg[k] = v
    return cfg


def _local_hash(files=None):
    """sha256 over the bytes of the gate config files in order (gates, sentinels, categories; a missing file
    hashes as empty), each followed by NUL. This is qa.config_hash()'s formula, kept identical on purpose."""
    h = hashlib.sha256()
    for p in (CONFIG_FILES if files is None else files):
        p = Path(p)
        h.update(p.read_bytes() if p.exists() else b"")
        h.update(b"\0")
    return h.hexdigest()


def config_hash():
    """Hash of data/gates.json + data/sentinels.json + data/categories.json. qa.check() stores it in
    gates.json; decide() re-evaluates a held candidate when it no longer matches the current files.
    qa's own function is used when it exists (one formula, one truth); otherwise the identical local one."""
    fn = getattr(qa, "config_hash", None)
    if callable(fn):
        try:
            return fn()
        except Exception as e:  # a hashing problem must never stop the pipeline; a mismatch only causes a recheck
            print(f"warning: qa.config_hash failed ({e}); using the local formula")
    return _local_hash()


def _load(path):
    """-> (obj or None, 'ok' | 'missing' | 'unreadable: ...')."""
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text()), "ok"
    except (OSError, ValueError) as e:
        return None, f"unreadable: {e}"


def _departments():
    """Ids sizing.json must cover: every department, and every child node of a split one."""
    try:
        out = []
        for d in store.config()["departments"]:
            out.append(str(d["id"]))
            out.extend(str(u["id"]) for u in d.get("split") or [])
        return out
    except (OSError, ValueError, KeyError, TypeError):
        return None


def inputs():
    """Everything decide() needs, read from the store (missing or unreadable files become None)."""
    files = {"state": _state_path(), "manifest": _manifest_path(), "sizing": _sizing_path(), "audit": _audit_path(),
             "gates": _gates_path(), "identify": _identify_path()}
    objs, status = {}, {}
    for k, p in files.items():
        objs[k], status[k] = _load(p)
    objs["status"] = status
    objs["cfg"] = schedule()
    objs["config_hash"] = config_hash()
    objs["departments"] = _departments()
    return objs


# ----------------------------------------------------------------------------- time helpers

def utcnow():
    return datetime.now(timezone.utc)


def _parse_ts(s):
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def age_days(stamp, now):
    """Days between an ISO timestamp and now; None when the stamp is missing or unparseable."""
    dt = _parse_ts(stamp)
    if dt is None:
        return None
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 86400


def _first_stamp(obj, keys):
    if not isinstance(obj, dict):
        return None
    for k in keys:
        if isinstance(obj.get(k), str):
            return obj[k]
    return None


def _stale(obj, keys, every_days, now):
    """True when obj is missing, carries no parseable timestamp under keys, or is older than every_days."""
    age = age_days(_first_stamp(obj, keys), now)
    return age is None or age > every_days


def sizing_entries(sizing):
    if not isinstance(sizing, dict):
        return {}
    inner = sizing.get("departments")
    if isinstance(inner, dict):
        sizing = inner
    return {str(k): v for k, v in sizing.items() if isinstance(v, dict)}


def sizing_stale(sizing, cfg, now, departments=None):
    """Sizing is due when the file is missing, a department has no entry, an entry is older than
    sizing_every_days (or unparseable), or an errored entry is older than a day."""
    entries = sizing_entries(sizing)
    if not entries:
        return True
    if departments and any(str(d) not in entries for d in departments):
        return True
    for e in entries.values():
        age = age_days(e.get("checked"), now)
        if age is None or age > cfg["sizing_every_days"]:
            return True
        if e.get("error") and age > SIZING_ERROR_RETRY_DAYS:
            return True
    return False


# ----------------------------------------------------------------------------- the decision

def decide(state, manifest, sizing, audit_latest, gates, cfg, now, *, current_hash=None, identify_latest=None,
           departments=None):
    """Pure: pick the one kind of work the next run should do.

    Inputs are the parsed JSON files (or None when missing/unreadable): state/run.json, build/published/manifest.json,
    sizing.json, audit/latest.json, build/candidate/gates.json; cfg is data/schedule.json; now is tz-aware.
    Keyword extras: current_hash (hash of the gate config, see config_hash(); computed from the repo files when None),
    identify_latest (identify/latest.json, written by the identify plan), departments (ids that sizing must cover).
    Missing or unreadable inputs bias towards doing work, never towards "none".

    Returns one of: size, crawl, build, recheck, start-full, start-core, audit, identify, none.
     1. crawling: "size" when sizing is missing/stale, else "crawl"
     2. crawled: "build"
     3. a candidate exists (built / needs_review / legacy awaiting_approval) and was not published for this run_id:
        "recheck" when gates.json is missing, has no config_hash, its config_hash differs from the current one,
        or it does not record a hold (an unfinished review/publish); a hold that qa marked `transient` (the live
        check or the sample review could not run) is rechecked once its stamp is TRANSIENT_RETRY_HOURS old;
        otherwise "none" (the hold stands until the config changes or the candidate is approved)
     4. no crawl in progress: "start-full" when there is no manifest or the last full publish (manifest
        full_published, else published) is older than full_every_days (or a date is unreadable); "start-core" when
        the last publish of any kind is older than core_every_days
     5. "audit" when a manifest exists and audit/latest.json is missing or older than audit_every_days
        (TRANSIENT_RETRY_HOURS after a failed attempt)
     6. "identify" when a manifest exists and identify/latest.json is missing or older than identify_every_days
     7. "none"
    """
    cfg = {**SCHEDULE_DEFAULTS, **(cfg or {})}
    state = state if isinstance(state, dict) else None
    manifest = manifest if isinstance(manifest, dict) else None
    status = state.get("status") if state else None

    if status == "crawling":
        return "size" if sizing_stale(sizing, cfg, now, departments) else "crawl"
    if status == "crawled":
        return "build"
    if status in CANDIDATE_STATES:
        published_this_run = bool(manifest and state.get("run_id") and manifest.get("version") == state.get("run_id"))
        if not published_this_run:
            if not isinstance(gates, dict):
                return "recheck"
            current = current_hash if current_hash is not None else config_hash()
            if not gates.get("config_hash") or gates.get("config_hash") != current:
                return "recheck"
            if gates.get("status") not in HOLD_STATUSES:
                return "recheck"
            if gates.get("transient") is True and _stale(gates, ("finalized", "checked"), TRANSIENT_RETRY_HOURS / 24, now):
                return "recheck"
            return "none"

    # no crawl in progress
    age = age_days(manifest.get("published"), now) if manifest else None
    # weekly core publishes keep `published` young, so the monthly full crawl keys off the last full publish
    full_age = age_days(manifest.get("full_published") or manifest.get("published"), now) if manifest else None
    # a rollback holds new crawl starts for one core period, so the restored prices stay live while the cause is fixed
    since_rollback = age_days(manifest.get("rolled_back_at"), now) if manifest else None
    paused = since_rollback is not None and since_rollback <= cfg["core_every_days"]
    if not paused and (manifest is None or age is None or full_age is None or full_age > cfg["full_every_days"]):
        return "start-full"
    if not paused and age > cfg["core_every_days"]:
        return "start-core"
    audit_every = cfg["audit_every_days"]
    if isinstance(audit_latest, dict) and audit_latest.get("status") == "error":
        audit_every = TRANSIENT_RETRY_HOURS / 24      # a failed audit is retried every few hours, not every 30 minutes
    if _stale(audit_latest, ("checked", "date", "finished", "run_at", "timestamp", "time", "created", "updated"),
              audit_every, now):
        return "audit"
    if _stale(identify_latest, ("refreshed", "checked", "date", "updated"), cfg["identify_every_days"], now):
        return "identify"
    return "none"


def decide_from(inp, now=None):
    return decide(inp["state"], inp["manifest"], inp["sizing"], inp["audit"], inp["gates"], inp["cfg"], now or utcnow(),
                  current_hash=inp["config_hash"], identify_latest=inp["identify"], departments=inp["departments"])


def _describe(inp, now):
    st = inp["state"] or {}
    man = inp["manifest"] or {}
    man_age = age_days(man.get("published"), now)
    gates = inp["gates"] or {}
    L = [f"- state: {st.get('status') or inp['status']['state']} run_id={st.get('run_id') or '-'}",
         f"- manifest: {man.get('version') or inp['status']['manifest']}"
         + (f", published {man_age:.1f} d ago" if man_age is not None else ""),
         f"- sizing: {inp['status']['sizing']}" + ("" if sizing_stale(inp['sizing'], inp['cfg'], now, inp['departments']) else " (fresh)"),
         f"- audit: {inp['status']['audit']}",
         f"- gates: {gates.get('status') or inp['status']['gates']}"
         + (" (config unchanged)" if gates.get("config_hash") == inp["config_hash"] else " (config changed or no hash)" if gates else "")
         + (" (transient hold: retried every %d h)" % TRANSIENT_RETRY_HOURS if gates.get("transient") is True else ""),
         f"- identify: {inp['status']['identify']}"]
    return "\n".join(L)


# ----------------------------------------------------------------------------- store helpers

def compact_store():
    """Replace data-store history with a single commit so the branch never grows."""
    if os.environ.get("SFB_NO_COMMIT") or not (store.ROOT / ".git").exists():
        return
    g = lambda *a: subprocess.run(["git", "-C", str(store.ROOT), *a], check=True, capture_output=True, text=True)
    g("checkout", "-q", "--orphan", "compact")
    g("add", "-A")
    g("commit", "-q", "-m", "compacted snapshot")
    g("push", "-q", "-f", "origin", "HEAD:data-store")


def _wm():
    """One Walmart client per run, paced by the per-minute cap the last crawl inferred (state.pace.per_min),
    so sizing, crawling, the live gate and the audit all share the same budget and the same cap."""
    from .wm import Walmart
    cap = ((store.read_json(_state_path()) or {}).get("pace") or {}).get("per_min")
    return Walmart(max_per_min=cap)


def _read_state(strict=True):
    state, status = _load(_state_path())
    if status.startswith("unreadable") and strict:
        raise SystemExit(f"state/run.json is {status}; fix or remove it on the data-store branch")
    return state


def _write_state(state):
    store.write_json(_state_path(), state)


def _read_text(path, default=""):
    try:
        return path.read_text()
    except OSError:
        return default


# ----------------------------------------------------------------------------- work: crawl

def _ensure_sizing(wm, inp, now):
    if sizing_stale(inp["sizing"], inp["cfg"], now, inp["departments"]):
        from . import sizing
        summary("Sizing departments (one call each) before crawling.")
        sizing.run(wm, now=now)
        store.checkpoint("sizing refreshed")
        return True
    return False


def _crawl(budget_min, inp, start_plan=None, wm=None):
    """Optionally start a run, size departments when due, then crawl within the budget; chain and alert."""
    from .wm import Throttled
    state = _read_state()
    if start_plan and state and state.get("status") == "crawled":
        # A finished crawl is waiting to be built; crawl.start() would delete its raw pages. Build it instead and
        # chain the requested crawl (the workflow keeps a named plan over a plain `continue`).
        summary(f"**{start_plan} crawl not started yet:** the finished crawl `{state.get('run_id')}` is waiting to be built. "
                f"Building it now; the {start_plan} crawl starts in the next run.")
        _build()
        set_out("next", start_plan)
        return "built"
    if start_plan and not (state and state.get("status") == "crawling"):
        crawl.start(start_plan)
        state = _read_state()
    if not (state and state.get("status") == "crawling"):
        summary("No crawl in progress.")
        return "idle"
    wm = wm or _wm()
    now = utcnow()
    try:
        _ensure_sizing(wm, inp, now)
        outcome = crawl.run(budget_min, wm=wm)
        pace = (store.read_json(_state_path()) or {}).get("pace") or {}
        if pace.get("per_min") or pace.get("inferred"):
            inf = pace.get("inferred") or {}
            summary(f"- pace: {pace.get('per_min') or 'no'}/min cap for the next run; this run: "
                    f"{inf.get('status_429', '?')} x 429, {inf.get('pattern', '?')} pattern, {inf.get('reason', '')}")
    except Throttled as e:
        print(f"paused during sizing: {e}")
        outcome = "throttled"
    state = _read_state() or state
    cut = crawl.truncated(state)
    if cut:
        alert("crawl-truncated", f"{len(cut)} department crawl(s) ended early or were refused",
              f"The crawl `{state.get('run_id')}` could not complete these: Walmart ended them well short of the page count "
              "it reports itself (even after retrying from the next cursor), or refused the category id:\n\n"
              + "\n".join(f"- {c}" for c in cut) + "\n\n"
              "They are marked `truncated` or `failed`, so the snapshot holds at the departments_complete gate instead of "
              "publishing a gap. Fix in data/categories.json: give a cut-short department a `split` (child nodes, each "
              "crawled on its own), or correct or remove a refused child node id; the running crawl picks the edit up and "
              "re-crawls just that department.")
    else:
        resolve("crawl-truncated")
    before = int(state.get("throttled_runs") or 0)
    if outcome == "throttled":
        state["throttled_runs"] = before + 1
        _write_state(state)
        # chain like a budget pause: the run already sat out up to Walmart's 45-minute back-off cap before giving up,
        # so the next run starts well spaced; the 30-minute schedule stays the backstop if the chain is lost
        set_out("next", "continue")
        summary(f"Paused by Walmart rate limiting ({state['throttled_runs']} run(s) in a row) after the back-off cap; "
                "chaining the next run.")
        if state["throttled_runs"] >= THROTTLED_ALERT_AFTER:
            alert("throttled", f"Walmart rate limiting for {state['throttled_runs']} consecutive runs",
                  f"The crawl `{state.get('run_id')}` ended rate limited (HTTP 429 beyond the per-run wait cap) in "
                  f"{state['throttled_runs']} consecutive runs.\n\n- calls so far: {state.get('calls')}\n"
                  f"- time spent waiting on 429s: {state.get('throttle_wait_s')} s\n\n"
                  "Each run waits out Walmart's back-off before the next one is chained; nothing is lost. If this persists for a day, the key "
                  "may be limited on Walmart's side (walmart.io dashboard) or the pacing in crawler/wm.py needs to slow down.")
    else:
        if before:
            state["throttled_runs"] = 0
            _write_state(state)
        resolve("throttled")
        if outcome in ("budget", "done"):
            set_out("next", "continue")
            summary("Crawl paused on budget; chaining the next run." if outcome == "budget"
                    else "Crawl complete; chaining the next run to build and check the snapshot.")
    store.checkpoint(f"{state.get('run_id')} {outcome}")
    return outcome


# ----------------------------------------------------------------------------- work: build / check / publish

def _qa_check(wm):
    """qa.check(wm) with the new qa, qa.check() with the old one; statuses normalised to ready|review|hold."""
    fn = qa.check
    try:
        takes_wm = bool(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        takes_wm = True
    status = fn(wm) if takes_wm else fn()
    if status in ("ready", "review"):
        return status
    if status not in HOLD_STATUSES:
        print(f"warning: qa.check returned {status!r}; treating it as hold")
    return "hold"


def _candidate_complete():
    cand = store.ROOT / "build" / "candidate"
    return store.jsonl_exists(cand / "items.jsonl.gz") and (cand / "stats.json").exists()


def _ensure_identify_data():
    """The build names barcode-only listings from the Open Facts product list (process.fill_placeholder_names): fetch it
    once if it is missing (no Walmart calls). A failed download only means fewer names; the build goes on."""
    if store.jsonl_exists(store.ROOT / "identify" / "products_us.jsonl.gz"):
        return
    try:
        identify.fetch()
    except Exception as e:                          # network or source format: names come from Walmart listings only
        print(f"identification data not fetched ({type(e).__name__}: {e}); placeholder names from Walmart listings only")


def _build(recheck=False):
    state = _read_state()
    if not state:
        raise SystemExit("no run to build")
    raw_dir = store.ROOT / "raw" / str(state.get("run_id") or "")
    if not recheck or not _candidate_complete() or raw_dir.is_dir():
        # a recheck follows an edit of data/gates.json, sentinels.json or categories.json; scope and
        # rule edits only take effect through process.build(), so rebuild from the raw pages whenever
        # they still exist (deterministic, no Walmart calls); only a candidate whose raw pages are gone
        # is re-evaluated as it stands
        _ensure_identify_data()
        process.build()
    wm = _wm() if _has_wm_credentials() else None
    status = _qa_check(wm)
    store.checkpoint(f"{state['run_id']} {'rechecked' if recheck else 'built'}: {status}")
    summary(_read_text(_report_path(), "(no report written)"))
    _after_check(status, state)
    return status


def _has_wm_credentials():
    return bool(os.environ.get("WM_CONSUMER_ID") and os.environ.get("WM_PRIVATE_KEY"))


def _after_check(status, state):
    if status == "ready":
        _publish(state)
    elif status == "review":
        set_out("review", "pending")
        summary("**Deterministic gates passed; sample review pending** (the workflow runs it next, then `finish`).")
    else:
        _hold(state)


def _publish(state, approve=False):
    ok = qa.publish(approve=approve)
    if not ok:
        print("publish declined by qa.publish; treating the snapshot as held")
        _hold(state)
        return False
    store.checkpoint(f"{state.get('run_id')} published" + (" (approved manually)" if approve else ""))
    compact_store()
    resolve(*PUBLISH_RESOLVES)
    _archive_published()
    set_out("next", "continue")
    man = store.read_json(_manifest_path()) or {}
    summary(f"**Published {man.get('version', state.get('run_id'))}**: {man.get('items', '?')} items. "
            "deploy-app follows; the next run refreshes identification data if due.")
    return True


def _archive_published():
    """Keep the published snapshot as a GitHub Release for rollback (newest three kept). A failure never undoes the
    publish: it opens [snapshot-archive] and the next publish tries again."""
    from . import releases
    pub = store.ROOT / "build" / "published"
    man = store.read_json(pub / "manifest.json") or {}
    if not releases.available():
        print("snapshot archive skipped: gh / GH_TOKEN / GITHUB_REPOSITORY not available (local run)")
        return
    try:
        tag = releases.archive(pub, man)
        deleted = releases.prune()
    except releases.ReleaseError as e:
        alert("snapshot-archive", f"published snapshot {man.get('version')} not kept for rollback",
              f"The snapshot was published, but uploading it as a GitHub Release (for plan=rollback) failed:\n\n`{e}`\n\n"
              "Rollback to earlier kept snapshots still works. The next publish tries again; to retry now, re-run the "
              "workflow with plan=status after fixing the cause.")
        return
    resolve("snapshot-archive")
    summary(f"- kept for rollback as release `{tag}`" + (f"; removed {', '.join(deleted)}" if deleted else ""))


def _rollback(target):
    """Put a kept snapshot back as build/published; the pipeline's completion triggers deploy-app, which ships it.
    The crawl state and any candidate are left alone. New crawls pause for schedule.core_every_days after a rollback."""
    from . import releases
    if not releases.available():
        raise SystemExit("rollback needs the gh CLI with GH_TOKEN and GITHUB_REPOSITORY (run it from the pipeline workflow)")
    pub = store.ROOT / "build" / "published"
    cur = (store.read_json(pub / "manifest.json") or {}).get("version")
    try:
        snap = releases.pick(releases.list_snapshots(), target, cur)
        tmp = releases.download(snap)
    except releases.ReleaseError as e:
        raise SystemExit(f"rollback refused: {e}")
    staged = pub.with_name("published.rollback")   # copy beside it first, so a failed copy leaves the live snapshot whole
    shutil.rmtree(staged, ignore_errors=True)
    shutil.copytree(tmp, staged)
    shutil.rmtree(tmp, ignore_errors=True)
    if pub.exists():
        shutil.rmtree(pub)
    staged.rename(pub)
    man = store.read_json(pub / "manifest.json")
    now = utcnow().isoformat(timespec="seconds")
    man["rolled_back_at"] = now
    man["rolled_back"] = {"from": cur, "to": snap["version"], "at": now}
    store.write_json(pub / "manifest.json", man)
    store.checkpoint(f"rolled back to {snap['version']} (from {cur})")
    resolve("snapshot-archive")
    summary(f"**Rolled back** to snapshot `{snap['version']}` ({man.get('items')} items, prices of "
            f"{str(man.get('published'))[:10]}); was `{cur}`. deploy-app ships it to the app next. New crawls pause for "
            f"{schedule()['core_every_days']} days; run plan=core or full to start one sooner.")


def _hold(state):
    run_id = state.get("run_id", "?")
    report = _read_text(_report_path(), "(no report written)")
    verdict, _ = _load(_verdict_path())
    kind = verdict.get("error_kind") if isinstance(verdict, dict) and verdict.get("status") == "error" else None
    if kind in ("auth", "permission", "credits"):
        key = "review-credits" if kind == "credits" else "review-key-invalid"
        if kind == "credits":
            title = f"sample review: Anthropic credits exhausted, snapshot {run_id} held"
            fix = ("**Add credits** to the Anthropic account that owns `ANTHROPIC_API_KEY` (Anthropic Console > Billing; "
                   "auto-reload is off, so it does not top up by itself). The key itself is fine.")
        elif kind == "auth":
            title = f"sample review: Anthropic API key invalid, snapshot {run_id} held"
            fix = ("**Replace the key**: the Anthropic API rejected `ANTHROPIC_API_KEY` as invalid or revoked (HTTP 401). "
                   "Create a new key in the Anthropic Console and update the repository secret. Credits are not the problem.")
        else:
            title = f"sample review: Anthropic API key not permitted, snapshot {run_id} held"
            fix = ("**Check the key's access**: the Anthropic API refused `ANTHROPIC_API_KEY` permission (HTTP 403), e.g. a "
                   "workspace without access to the review model. Use a key from a workspace that has it.")
        body = (fix + f"\n\nAPI response: `{str(verdict.get('reason') or '')[:300]}`\n\n"
                "The held candidate is re-checked every few hours; once fixed, the next re-check runs the review and "
                "publishes if it passes (this issue then closes). To publish without the review, run the workflow with "
                "plan=approve.\n\n## Report\n\n" + report)
    elif isinstance(verdict, dict) and verdict.get("status") == "skipped":
        key = "review-key-missing"
        title = f"sample review skipped, snapshot {run_id} held"
        body = (f"The sample review did not run: {verdict.get('reason', 'ANTHROPIC_API_KEY missing')}.\n\n"
                "Add the repository secret `ANTHROPIC_API_KEY` (Settings > Secrets and variables > Actions); the next "
                "`continue` re-checks the candidate and publishes when the review passes. To publish without the review, "
                "run the workflow with plan=approve.\n\n## Report\n\n" + report)
    else:
        key = "gates-hold"
        title = f"snapshot {run_id} held by the gates"
        body = ("The candidate snapshot was not published; the previous snapshot stays live.\n\n"
                "Fix the cause (data/gates.json thresholds, data/sentinels.json, data/categories.json) and the next "
                "`continue` re-evaluates automatically; or run the workflow with plan=approve to publish as is.\n\n"
                "## Report\n\n" + report)
    alert(key, title, body)
    summary(f"**Held.** {title}. The previous snapshot stays live.")


def _finish():
    finalize = getattr(qa, "finalize", None)
    if finalize is None:
        raise SystemExit("qa.finalize is missing: the sample review step needs crawler/qa.py from the gates stream")
    state = _read_state()
    if not state:
        raise SystemExit("no run to finish")
    status = finalize()
    store.checkpoint(f"{state.get('run_id')} finalized: {status}")
    summary(_read_text(_report_path(), "(no report written)"))
    if status == "ready":
        _publish(state)
    else:
        _hold(state)
    return status


def _approve():
    state = _read_state() or {}
    if not state:
        print("no run state; publishing whatever candidate exists")
    elif state.get("status") in ("crawling", "crawled"):
        summary(f"Note: run {state.get('run_id')} is {state.get('status')}; it continues untouched, "
                "the candidate on disk is what gets published.")
    if qa.publish(approve=True):
        store.checkpoint("approved snapshot published")
        compact_store()
        resolve(*PUBLISH_RESOLVES)
        set_out("next", "continue")
        summary("**Published by manual approval.**")
        return True
    summary("Nothing published (no candidate or `check` not run).")
    return False


# ----------------------------------------------------------------------------- work: audit / identify / size

def _audit():
    try:
        from . import audit
    except ImportError as e:
        raise SystemExit(f"crawler/audit.py is missing: {e}")
    res = audit.run(_wm()) or {}
    status = res.get("status", "ok")
    now = utcnow().isoformat(timespec="seconds")
    if status == "skipped":
        # audit.run wrote nothing; remember the attempt so the next audit waits a full period instead of 30 minutes
        store.write_json(_audit_path(), {"status": "skipped", "checked": now, "reason": res.get("reason")})
    elif status == "error":
        # the live check could not run: remember the attempt so decide() retries in TRANSIENT_RETRY_HOURS, not 30 min
        prev = store.read_json(_audit_path())
        errors = (prev.get("errors") or 0) + 1 if isinstance(prev, dict) and prev.get("status") == "error" else 1
        store.write_json(_audit_path(), {"status": "error", "checked": now, "reason": res.get("reason"),
                                         "errors": errors})
        res["errors"] = errors
    store.checkpoint("audit")
    lines = [f"- {k}: {v}" for k, v in sorted(res.items()) if not isinstance(v, (list, dict))]
    body = "## Audit\n\n" + "\n".join(lines)
    summary(body)
    if status == "error":
        reason = str(res.get("reason") or "")
        # an HTTP 4xx other than 429 (key revoked or rotated, access removed) will not clear by itself: say so at once;
        # throttling or network trouble gets AUDIT_ERRORS_ALERT attempts first
        if "RuntimeError: HTTP 4" in reason or res["errors"] >= AUDIT_ERRORS_ALERT:
            alert("audit-failed", f"live audit could not run ({res['errors']} attempt(s))",
                  "The weekly live re-check of published prices could not reach Walmart. An HTTP 401/403 usually means "
                  "the WM_CONSUMER_ID / WM_PRIVATE_KEY secrets or WM_KEY_VERSION no longer match the Walmart I/O "
                  f"app; throttling or network errors clear by themselves. It is retried every {TRANSIENT_RETRY_HOURS} h "
                  "and this issue closes after the next successful audit.\n\n" + body)
        return res
    if status != "ok":
        return res          # skipped: waits a full period, no alert
    resolve("audit-failed")
    if res.get("alert"):
        rate = res.get("match_rate")
        shown = f"{rate} ({rate:.0%})" if isinstance(rate, (int, float)) and not isinstance(rate, bool) else "?"
        alert("audit-regression", f"live audit: only {shown} of sampled prices still match",
              "The weekly live re-check of published prices fell below the threshold in data/gates.json "
              "(audit_match_min). A core refresh is the usual fix; it starts by itself when due, or run the workflow "
              "with plan=core.\n\n" + body)
    else:
        resolve("audit-regression")
    return res


def _identify():
    identify.fetch()
    pub = store.ROOT / "build" / "published" / "items.jsonl.gz"
    cand = store.ROOT / "build" / "candidate" / "items.jsonl.gz"
    if store.jsonl_exists(pub) or store.jsonl_exists(cand):
        identify.match()
    else:
        print("no snapshot yet: identification data fetched, equivalents skipped")
    stats = store.read_json(store.ROOT / "identify" / "equivalents_stats.json") or {}
    store.write_json(_identify_path(), {"refreshed": utcnow().isoformat(timespec="seconds"), "equivalents_stats": stats})
    store.checkpoint("identification data refreshed")
    summary("Identification data refreshed.")


def _size():
    from . import sizing
    res = sizing.run(_wm())
    store.checkpoint("sizing refreshed")
    summary("```\n" + sizing.table(res) + "\n```")
    return res


# ----------------------------------------------------------------------------- plans

def _peek(inp, now):
    st = inp["status"]
    work = "inspect" if st["state"].startswith("unreadable") else decide_from(inp, now)
    print(_describe(inp, now))
    print(f"work={work}")
    set_out("work", work)
    man = inp["manifest"]
    state = inp["state"] or {}
    if isinstance(man, dict) and state.get("status") != "crawling":
        age = age_days(man.get("published"), now)
        if age is not None and age > inp["cfg"]["stale_days"]:
            alert("stale-prices", f"published prices are {age:.0f} days old",
                  f"The live snapshot `{man.get('version')}` was published on {man.get('published')} "
                  f"({age:.0f} days ago; the limit is {inp['cfg']['stale_days']} days) and no crawl is running.\n\n"
                  "The pipeline starts a refresh by itself when one is due; if this stays open, look at the latest "
                  "pipeline runs and the other open pipeline-alert issues (a hold or repeated failures).")
    if work == "none":
        summary("Nothing to do.")
    return work


def _continue(budget_min):
    inp = inputs()
    now = utcnow()
    _read_state()  # fail loudly on an unreadable state file
    work = decide_from(inp, now)
    set_out("work", work)
    summary(f"### continue: {work}\n{_describe(inp, now)}")
    if work in ("size", "crawl"):
        _crawl(budget_min, inp)
    elif work in ("start-full", "start-core"):
        _crawl(budget_min, inp, start_plan=work.split("-")[1])
    elif work == "build":
        _build()
    elif work == "recheck":
        _build(recheck=True)
    elif work == "audit":
        _audit()
    elif work == "identify":
        _identify()
    else:
        summary("Nothing to do.")
    return work


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="continue", choices=PLANS)
    ap.add_argument("--budget-min", type=float, default=None, help="crawl time per run (default: data/schedule.json)")
    ap.add_argument("--rollback-to", default="previous", help='plan=rollback: "previous" or a kept snapshot version')
    a = ap.parse_args(argv)
    budget = a.budget_min if a.budget_min is not None else schedule()["budget_min"]
    _reset_outputs(a.plan)
    try:
        if a.plan == "peek":
            _peek(inputs(), utcnow())
        elif a.plan == "status":
            crawl.status()
            inp = inputs()
            print(_describe(inp, utcnow()))
            print(f"next continue would: {decide_from(inp)}")
        elif a.plan == "continue":
            _continue(budget)
        elif a.plan in ("full", "core"):
            _crawl(budget, inputs(), start_plan=a.plan)
            crawl.status()
        elif a.plan == "approve":
            _approve()
        elif a.plan == "identify":
            _identify()
        elif a.plan == "audit":
            _audit()
        elif a.plan == "size":
            _size()
        elif a.plan == "finish":
            _finish()
        elif a.plan == "rollback":
            _rollback(a.rollback_to)
        if a.plan not in ("peek", "status"):
            _size_watch()
    finally:
        flush_outputs()


def _size_watch():
    """[data-store-size] when the files on the data-store branch pass store.STORE_ALERT_BYTES (1 GB): every pipeline and
    deploy run checks the branch out, and GitHub recommends keeping a repository well under 5 GB. Files over GitHub's
    100 MB limit cannot occur: store.write_jsonl_gz shards large files and store.checkpoint refuses to push one."""
    if not store.ROOT.exists():
        return
    total = store.tree_bytes()
    by_dir = {}
    for p in store.ROOT.iterdir():
        if p.name == ".git":
            continue
        by_dir[p.name] = (sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size)
    top = ", ".join(f"{k} {v / 1048576:.0f} MB" for k, v in sorted(by_dir.items(), key=lambda x: -x[1])[:6])
    summary(f"- data-store branch: {total / 1048576:.0f} MB of files ({top})")
    if total <= store.STORE_ALERT_BYTES:
        resolve("data-store-size")
        return
    alert("data-store-size", f"data-store branch holds {total / 1024 ** 3:.2f} GB of files",
          f"The data-store branch passed {store.STORE_ALERT_BYTES / 1024 ** 3:.0f} GB ({top}). Every pipeline and deploy run "
          "downloads it, and GitHub recommends keeping repositories well under 5 GB.\n\n"
          "Proposed fix (needs your decision; it touches the Cloudflare account): move the raw crawl pages "
          "(`raw/<run>/`) to a Cloudflare R2 bucket (10 GB free, no egress fees). The crawler writes each part there "
          "instead of the branch and process.build reads them back; the branch keeps the state, snapshots, history "
          "and reports. It needs one R2 bucket and an API token limited to it, stored as repository secrets. Without new "
          "accounts, the fallback is to upload each finished run's raw pages as a GitHub Release asset (2 GB per file) "
          "and drop them from the branch once its snapshot is published.")


if __name__ == "__main__":
    main()
