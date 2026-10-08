"""crawler/ci.py: the decide() priority queue, peek, the plans' outputs and alerts, and the alert action's bash."""
import contextlib, hashlib, importlib, io, json, os, re, shutil, stat, subprocess, sys, tempfile, types, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import crawler.ci as ci

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
CFG = {"full_every_days": 30, "core_every_days": 7, "audit_every_days": 7, "identify_every_days": 30,
       "sizing_every_days": 30, "stale_days": 14, "budget_min": 300}
HASH = "hash-of-current-config"
DEPTS = ["1", "2"]
REPO = Path(__file__).resolve().parent.parent


def iso(days_ago):
    return (NOW - timedelta(days=days_ago)).isoformat(timespec="seconds")


def sizing(days_ago=1, depts=DEPTS, error_on=(), checked=None):
    return {d: {"name": f"D{d}", "total_pages": 10, "first_page_items": 200, "est_items": 2000,
                "checked": checked if checked is not None else iso(days_ago),
                **({"error": "RuntimeError: HTTP 400"} if d in error_on else {})} for d in depts}


def manifest(days_ago=1, version="run-1", published=None):
    return {"version": version, "published": published if published is not None else iso(days_ago), "items": 10}


def gates(status="hold", h=HASH):
    g = {"status": status, "gates": {}, "checked": iso(0)}
    if h is not None:
        g["config_hash"] = h
    return g


def state(status, run_id="run-1", **extra):
    return {"run_id": run_id, "plan": "full", "status": status, "departments": [], "started": iso(1), "updated": iso(0),
            "calls": 0, "throttle_wait_s": 0, **extra}


def live_state():
    """A copy of the real data-store state taken mid-crawl on 2026-10-07 (Food at page 649 with a saved cursor,
    22 departments pending, no pace or sizing fields): what a merge must resume from."""
    return json.loads((REPO / "tests" / "fixtures" / "run-live.json").read_text())


def dec(st=None, man=None, siz=None, audit=None, g=None, cfg=CFG, identify=None, depts=DEPTS, h=HASH, now=NOW):
    return ci.decide(st, man, siz, audit, g, cfg, now, current_hash=h, identify_latest=identify, departments=depts)


class Decide(unittest.TestCase):
    # 1. crawling
    def test_crawling_sizes_first_when_sizing_is_missing(self):
        self.assertEqual(dec(state("crawling")), "size")

    def test_crawling_with_fresh_sizing_crawls(self):
        self.assertEqual(dec(state("crawling"), siz=sizing(1)), "crawl")

    def test_crawling_with_stale_sizing_sizes_again(self):
        self.assertEqual(dec(state("crawling"), siz=sizing(31)), "size")
        self.assertEqual(dec(state("crawling"), siz=sizing(29)), "crawl")

    def test_sizing_missing_a_department_is_redone(self):
        self.assertEqual(dec(state("crawling"), siz=sizing(1, depts=["1"])), "size")
        self.assertEqual(dec(state("crawling"), siz=sizing(1, depts=["1"]), depts=None), "crawl")   # no list: no check

    def test_sizing_with_an_error_is_retried_after_a_day(self):
        self.assertEqual(dec(state("crawling"), siz=sizing(0.5, error_on=["2"])), "crawl")
        self.assertEqual(dec(state("crawling"), siz=sizing(1.5, error_on=["2"])), "size")

    def test_sizing_with_unparseable_or_missing_stamp_is_redone(self):
        self.assertEqual(dec(state("crawling"), siz=sizing(checked="yesterday")), "size")
        s = sizing(1); del s["1"]["checked"]
        self.assertEqual(dec(state("crawling"), siz=s), "size")
        self.assertEqual(dec(state("crawling"), siz={}), "size")
        self.assertEqual(dec(state("crawling"), siz=["not", "a", "dict"]), "size")

    def test_sizing_nested_under_departments_is_accepted(self):
        self.assertEqual(dec(state("crawling"), siz={"departments": sizing(1)}), "crawl")

    # 2. crawled
    def test_crawled_builds(self):
        self.assertEqual(dec(state("crawled"), man=manifest(100)), "build")

    # 3. candidate held / unfinished
    def test_candidate_without_gates_file_is_rechecked(self):
        for st in ("built", "needs_review", "awaiting_approval"):
            self.assertEqual(dec(state(st)), "recheck", st)

    def test_candidate_rechecked_when_config_hash_changed_or_missing(self):
        self.assertEqual(dec(state("needs_review"), g=gates("hold", "old-hash")), "recheck")
        self.assertEqual(dec(state("needs_review"), g=gates("hold", None)), "recheck")
        self.assertEqual(dec(state("needs_review"), g=gates("hold", "")), "recheck")

    def test_hold_with_unchanged_config_stands(self):
        for st in ("built", "needs_review"):
            for gs in ("hold", "needs_review", "awaiting_approval"):
                self.assertEqual(dec(state(st), g=gates(gs)), "none", (st, gs))

    def test_hold_stands_even_when_the_manifest_is_old(self):
        self.assertEqual(dec(state("needs_review"), man=manifest(100, version="run-0"), g=gates("hold")), "none")

    def test_transient_hold_is_rechecked_after_six_hours(self):
        g = gates("hold"); g["transient"] = True
        g["checked"] = (NOW - timedelta(hours=1)).isoformat(timespec="seconds")
        self.assertEqual(dec(state("needs_review"), g=g), "none")                 # too soon
        g["checked"] = (NOW - timedelta(hours=7)).isoformat(timespec="seconds")
        self.assertEqual(dec(state("needs_review"), g=g), "recheck")
        g["finalized"] = (NOW - timedelta(hours=2)).isoformat(timespec="seconds")   # finalize stamp is the newer one
        self.assertEqual(dec(state("needs_review"), g=g), "none")
        del g["finalized"]; del g["checked"]
        self.assertEqual(dec(state("needs_review"), g=g), "recheck")              # no stamp: retry
        g["transient"] = "yes"                                                    # only a real true counts
        self.assertEqual(dec(state("needs_review"), g=g), "none")
        g2 = gates("hold"); g2["transient"] = False; g2["checked"] = iso(5)
        self.assertEqual(dec(state("needs_review"), g=g2), "none")

    def test_unfinished_review_or_publish_is_rechecked(self):
        self.assertEqual(dec(state("built"), g=gates("review")), "recheck")
        self.assertEqual(dec(state("built"), g=gates("ready")), "recheck")
        self.assertEqual(dec(state("built"), g=["garbage"]), "recheck")

    def test_candidate_already_published_for_this_run_falls_through(self):
        # manifest.version == run_id: the hold is history; the fresh manifest means audit is next
        self.assertEqual(dec(state("built", run_id="run-1"), man=manifest(1, version="run-1"), g=gates("hold")), "audit")
        self.assertEqual(dec(state("built", run_id="run-2"), man=manifest(1, version="run-1"), g=gates("hold")), "none")

    def test_current_hash_computed_from_repo_files_when_not_given(self):
        g = gates("hold", ci.config_hash())
        self.assertEqual(ci.decide(state("needs_review"), None, None, None, g, CFG, NOW), "none")
        g["config_hash"] = "x"
        self.assertEqual(ci.decide(state("needs_review"), None, None, None, g, CFG, NOW), "recheck")

    # 4. no crawl in progress
    def test_no_state_and_no_manifest_starts_full(self):
        self.assertEqual(dec(), "start-full")
        self.assertEqual(dec(st=["weird"]), "start-full")
        self.assertEqual(dec(man="not a dict"), "start-full")

    def test_old_manifest_starts_full_and_medium_age_starts_core(self):
        self.assertEqual(dec(state("published"), man=manifest(31)), "start-full")
        self.assertEqual(dec(state("published"), man=manifest(8)), "start-core")
        self.assertEqual(dec(state("published"), man=manifest(7)), "audit")        # not strictly older than 7 days
        self.assertEqual(dec(state("published"), man=manifest(30)), "start-core")

    def test_monthly_full_follows_the_last_full_publish_not_the_last_core(self):
        # weekly core publishes keep `published` young; the full crawl keys off full_published
        core = {**manifest(3), "full_published": iso(31)}
        self.assertEqual(dec(state("published"), man=core), "start-full")
        core["full_published"] = iso(20)
        self.assertEqual(dec(state("published"), man=core, audit={"checked": iso(1)}, identify={"refreshed": iso(1)}), "none")
        core["full_published"] = "garbage"
        self.assertEqual(dec(state("published"), man=core), "start-full")
        # a manifest from before full_published existed falls back to `published`
        self.assertEqual(dec(state("published"), man=manifest(3), audit={"checked": iso(1)}, identify={"refreshed": iso(1)}), "none")

    def test_monthly_full_is_reached_over_a_simulated_season(self):
        # 120 days, each started crawl publishes the same day: full crawls must recur about monthly
        man, fulls, day = None, [], 0
        for day in range(120):
            now = NOW + timedelta(days=day)
            work = ci.decide(state("published"), man, None, {"checked": now.isoformat()}, None, CFG, now,
                             current_hash=HASH, identify_latest={"refreshed": now.isoformat()})
            if work in ("start-full", "start-core"):
                prev = man or {}
                full = work == "start-full"
                man = {"version": f"d{day}", "published": now.isoformat(), "items": 1,
                       "full_published": now.isoformat() if full else (prev.get("full_published") or prev.get("published"))}
                if full:
                    fulls.append(day)
        self.assertGreaterEqual(len(fulls), 4, fulls)
        self.assertTrue(all(b - a <= 32 for a, b in zip(fulls, fulls[1:])), fulls)

    def test_failed_audit_is_retried_after_hours_not_every_run(self):
        fresh = dict(st=state("published"), man=manifest(1), identify={"refreshed": iso(1)})
        self.assertEqual(dec(**fresh, audit={"status": "error", "checked": iso(0.1)}), "none")
        self.assertEqual(dec(**fresh, audit={"status": "error", "checked": iso(0.3)}), "audit")   # > 6 h
        self.assertEqual(dec(**fresh, audit={"status": "skipped", "checked": iso(0.3)}), "none")  # a full period

    def test_unreadable_manifest_date_biases_towards_a_full_crawl(self):
        self.assertEqual(dec(state("published"), man=manifest(published="soon")), "start-full")
        self.assertEqual(dec(state("published"), man={"version": "x"}), "start-full")

    def test_unknown_state_status_is_treated_as_no_crawl(self):
        self.assertEqual(dec(state("whatever"), man=manifest(31)), "start-full")
        self.assertEqual(dec({"status": None}, man=manifest(1), audit={"checked": iso(1)}, identify={"refreshed": iso(1)}), "none")

    # 5./6./7. audit, identify, none
    def test_audit_when_missing_or_stale(self):
        fresh = dict(st=state("published"), man=manifest(1))
        self.assertEqual(dec(**fresh), "audit")
        self.assertEqual(dec(**fresh, audit={"checked": iso(8)}), "audit")
        self.assertEqual(dec(**fresh, audit={"date": "not a date"}), "audit")
        self.assertEqual(dec(**fresh, audit={"match_rate": 0.99}), "audit")
        self.assertEqual(dec(**fresh, audit={"checked": iso(6)}), "identify")
        self.assertEqual(dec(**fresh, audit={"date": iso(6)}), "identify")        # alternate stamp key
        self.assertEqual(dec(**fresh, audit={"checked": iso(6) .replace("+00:00", "Z")}), "identify")

    def test_identify_when_missing_or_stale_then_none(self):
        fresh = dict(st=state("published"), man=manifest(1), audit={"checked": iso(1)})
        self.assertEqual(dec(**fresh), "identify")
        self.assertEqual(dec(**fresh, identify={"refreshed": iso(31)}), "identify")
        self.assertEqual(dec(**fresh, identify={"refreshed": iso(29)}), "none")
        self.assertEqual(dec(**fresh, identify={"refreshed": "nope"}), "identify")

    def test_schedule_defaults_apply_when_cfg_missing_or_partial(self):
        self.assertEqual(dec(state("published"), man=manifest(8), cfg=None), "start-core")
        self.assertEqual(dec(state("published"), man=manifest(8), cfg={"core_every_days": 10}), "audit")

    def test_naive_now_is_treated_as_utc(self):
        self.assertEqual(dec(state("published"), man=manifest(8), now=NOW.replace(tzinfo=None)), "start-core")

    def test_the_live_mid_crawl_state_sizes_first_then_crawls(self):
        live = live_state()
        depts = [d["id"] for d in live["departments"]]
        self.assertEqual(live["status"], "crawling"); self.assertNotIn("throttled_runs", live)
        self.assertEqual(ci.decide(live, None, None, None, None, CFG, NOW), "size")                 # no sizing.json
        self.assertEqual(ci.decide(live, None, None, None, None, None, NOW), "size")                # not even a schedule
        self.assertEqual(dec(live, siz=sizing(1, depts=depts), depts=depts), "crawl")              # with it
        self.assertEqual(dec(live, siz=sizing(1, depts=depts), depts=None), "crawl")
        self.assertEqual(dec(live, siz=sizing(1, depts=depts[1:]), depts=depts), "size")           # Food not sized

    def test_results_are_always_known_kinds(self):
        cases = [dict(), dict(st=state("crawling")), dict(st=state("crawling"), siz=sizing()), dict(st=state("crawled")),
                 dict(st=state("built")), dict(st=state("needs_review"), g=gates()), dict(st=state("published"), man=manifest(8)),
                 dict(st=state("published"), man=manifest(1)), dict(st=state("published"), man=manifest(1), audit={"checked": iso(1)}),
                 dict(st=state("published"), man=manifest(1), audit={"checked": iso(1)}, identify={"refreshed": iso(1)})]
        for c in cases:
            self.assertIn(dec(**c), ci.KINDS)


class Helpers(unittest.TestCase):
    def test_age_days(self):
        self.assertAlmostEqual(ci.age_days(iso(2), NOW), 2.0)
        self.assertAlmostEqual(ci.age_days("2026-10-05T12:00:00Z", NOW), 2.0)
        self.assertAlmostEqual(ci.age_days("2026-10-05T12:00:00", NOW), 2.0)    # naive stamp = UTC
        for bad in (None, "", "   ", "tomorrow", 5, {}):
            self.assertIsNone(ci.age_days(bad, NOW), bad)

    def test_schedule_file_handling(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "schedule.json"
            with mock.patch.object(ci, "SCHEDULE", p):
                self.assertEqual(ci.schedule(), ci.SCHEDULE_DEFAULTS)                     # missing
                p.write_text("{not json")
                self.assertEqual(ci.schedule(), ci.SCHEDULE_DEFAULTS)                     # unreadable
                p.write_text(json.dumps({"core_every_days": 3, "stale_days": -1, "budget_min": "x", "extra": 1}))
                cfg = ci.schedule()
                self.assertEqual(cfg["core_every_days"], 3)
                self.assertEqual(cfg["stale_days"], 14); self.assertEqual(cfg["budget_min"], 300)
                self.assertNotIn("extra", cfg)
        real = ci.schedule()   # the repo file carries the documented defaults
        self.assertEqual({k: real[k] for k in ci.SCHEDULE_DEFAULTS}, ci.SCHEDULE_DEFAULTS)

    def test_config_hash_tracks_the_three_config_files(self):
        with tempfile.TemporaryDirectory() as d:
            files = tuple(Path(d) / n for n in ("gates.json", "sentinels.json", "categories.json"))
            h0 = ci._local_hash(files)                      # all missing is still a hash
            files[1].write_text("{}"); h1 = ci._local_hash(files)
            files[0].write_text("{}"); h2 = ci._local_hash(files)
            files[0].write_text('{"a": 1}'); h3 = ci._local_hash(files)
            self.assertEqual(len({h0, h1, h2, h3}), 4)
            self.assertEqual(h3, ci._local_hash(files))     # deterministic
            # the formula qa.config_hash() uses: bytes of each file (missing = empty) followed by NUL, in order
            ref = hashlib.sha256(b'{"a": 1}\0{}\0\0').hexdigest()
            self.assertEqual(h3, ref)
        self.assertEqual(ci.config_hash(), ci.config_hash())
        self.assertEqual(ci._local_hash(), ci._local_hash(ci.CONFIG_FILES))

    def test_config_hash_prefers_qa_when_it_has_one(self):
        with mock.patch.object(ci.qa, "config_hash", lambda: "qa-hash", create=True):
            self.assertEqual(ci.config_hash(), "qa-hash")
        def boom():
            raise OSError("disk")
        with mock.patch.object(ci.qa, "config_hash", boom, create=True):
            self.assertEqual(ci.config_hash(), ci._local_hash())      # falls back, never raises
        if hasattr(ci.qa, "config_hash"):                              # with the gates stream merged: one truth
            self.assertEqual(ci.config_hash(), ci.qa.config_hash())
            self.assertEqual(ci._local_hash(), ci.qa.config_hash())


class FakeWM:
    def __init__(self):
        self.calls = 0; self.throttle_waited = 0; self.paths = []

    def get(self, path):
        self.calls += 1; self.paths.append(path)
        return {"items": [{"itemId": 1}], "totalPages": 4, "nextPage": None, "nextPageExist": False}


class PlanBase(unittest.TestCase):
    """A temp store, outputs captured from $GITHUB_OUTPUT, modules reloaded so store.ROOT points at it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"SFB_STORE": str(self.tmp / "store"), "SFB_NO_COMMIT": "1",
                                                "GITHUB_OUTPUT": str(self.tmp / "out.txt"), "RUNNER_TEMP": str(self.tmp / "rt"),
                                                "GITHUB_STEP_SUMMARY": str(self.tmp / "summary.md"),
                                                "WM_CONSUMER_ID": "cid", "WM_PRIVATE_KEY": "key"})
        self.env.start()
        import crawler.store, crawler.crawl, crawler.process, crawler.qa, crawler.sizing
        for m in (crawler.store, crawler.crawl, crawler.process, crawler.qa, crawler.sizing, ci):
            importlib.reload(m)
        self.store, self.crawl, self.process, self.qa, self.sizing = crawler.store, crawler.crawl, crawler.process, crawler.qa, crawler.sizing
        self.root = self.store.ROOT
        self.wm = FakeWM()
        p = mock.patch.object(ci, "_wm", lambda: self.wm); p.start(); self.addCleanup(p.stop)
        self.depts = [str(d["id"]) for d in self.store.config()["departments"]]

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp)
        sys.modules.pop("crawler.audit", None)
        if hasattr(sys.modules["crawler"], "audit"):
            delattr(sys.modules["crawler"], "audit")

    def write(self, rel, obj):
        self.store.write_json(self.root / rel, obj)

    def read(self, rel):
        return self.store.read_json(self.root / rel)

    def outputs(self):
        res = {}
        p = Path(os.environ["GITHUB_OUTPUT"])
        if p.exists():
            for line in p.read_text().splitlines():
                k, _, v = line.partition("=")
                res[k] = v
            p.unlink()
        return res

    def run_plan(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ci.main(list(argv))
        return self.outputs(), buf.getvalue()

    def body(self, outputs):
        return Path(outputs["alert_body_file"]).read_text()

    def candidate(self, report="# report\n\nStatus: hold\n"):
        cand = self.root / "build" / "candidate"
        self.store.write_jsonl_gz(cand / "items.jsonl.gz", [{"id": 1}])
        self.write("build/candidate/stats.json", {"run_id": "run-1", "items": 1})
        (cand / "report.md").write_text(report)


class Peek(PlanBase):
    def test_empty_store_means_start_full_and_all_outputs_present(self):
        o, text = self.run_plan("--plan", "peek")
        self.assertEqual(o["work"], "start-full"); self.assertEqual(o["alert"], "none")
        self.assertIn("work=start-full", text)
        self.assertEqual(set(o), set(ci.OUTPUT_KEYS))
        self.assertEqual(o["review"], "none"); self.assertEqual(o["resolve"], ""); self.assertEqual(o["next"], "")

    def test_crawling_with_fresh_sizing_peeks_crawl(self):
        self.write("state/run.json", state("crawling"))
        self.write("sizing.json", sizing(1, depts=self.depts))
        self.assertEqual(self.run_plan("--plan", "peek")[0]["work"], "crawl")
        self.write("sizing.json", sizing(1, depts=self.depts[1:]))      # a department missing
        self.assertEqual(self.run_plan("--plan", "peek")[0]["work"], "size")

    def test_stale_prices_alert(self):
        self.write("state/run.json", state("published"))
        self.write("build/published/manifest.json", manifest(20))
        with mock.patch.object(ci, "utcnow", lambda: NOW):
            o, _ = self.run_plan("--plan", "peek")
        self.assertEqual(o["work"], "start-core")
        self.assertEqual(o["alert"], "stale-prices")
        self.assertIn("20 days", o["alert_title"])
        self.assertIn("run-1", self.body(o)); self.assertIn("14 days", self.body(o))
        self.assertTrue(o["alert_body_file"].startswith(os.environ["RUNNER_TEMP"]))

    def test_no_stale_alert_while_a_crawl_runs_or_when_fresh(self):
        self.write("build/published/manifest.json", manifest(20))
        self.write("state/run.json", state("crawling"))
        self.write("sizing.json", sizing(1, depts=self.depts))
        with mock.patch.object(ci, "utcnow", lambda: NOW):
            self.assertEqual(self.run_plan("--plan", "peek")[0]["alert"], "none")
            self.write("state/run.json", state("published"))
            self.write("build/published/manifest.json", manifest(13))
            self.assertEqual(self.run_plan("--plan", "peek")[0]["alert"], "none")

    def test_unreadable_state_asks_for_a_full_run(self):
        (self.root / "state").mkdir(parents=True)
        (self.root / "state" / "run.json").write_text("{broken")
        self.write("build/published/manifest.json", manifest(1))
        o, _ = self.run_plan("--plan", "peek")
        self.assertEqual(o["work"], "inspect")

    def test_unreadable_other_files_bias_towards_work(self):
        self.write("state/run.json", state("needs_review"))
        (self.root / "build" / "candidate").mkdir(parents=True)
        (self.root / "build" / "candidate" / "gates.json").write_text("<html>")
        self.assertEqual(self.run_plan("--plan", "peek")[0]["work"], "recheck")
        self.write("state/run.json", state("crawling"))
        (self.root / "sizing.json").write_text("")
        self.assertEqual(self.run_plan("--plan", "peek")[0]["work"], "size")

    def test_peek_has_no_side_effects(self):
        self.write("state/run.json", state("crawled"))
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(self.run_plan("--plan", "peek")[0]["work"], "build")
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(before, after)
        self.assertEqual(self.wm.calls, 0)

    def test_nothing_to_do(self):
        self.write("state/run.json", state("published"))
        self.write("build/published/manifest.json", manifest(1))
        self.write("audit/latest.json", {"checked": iso(1)})
        self.write("identify/latest.json", {"refreshed": iso(1)})
        with mock.patch.object(ci, "utcnow", lambda: NOW):
            o, _ = self.run_plan("--plan", "peek")
        self.assertEqual(o["work"], "none")
        self.assertIn("Nothing to do", Path(os.environ["GITHUB_STEP_SUMMARY"]).read_text())


class Continue(PlanBase):
    def test_unreadable_state_fails_loudly(self):
        (self.root / "state").mkdir(parents=True)
        (self.root / "state" / "run.json").write_text("{broken")
        with self.assertRaises(SystemExit) as cm:
            self.run_plan("--plan", "continue")
        self.assertIn("unreadable", str(cm.exception))

    def test_throttled_counter_alerts_on_the_third_run_and_clears_on_progress(self):
        self.write("state/run.json", state("crawling", calls=12, throttle_wait_s=2700))
        self.write("sizing.json", sizing(1, depts=self.depts))
        with mock.patch.object(self.crawl, "run", lambda budget, wm=None: "throttled"):
            for n in (1, 2):
                o, _ = self.run_plan("--plan", "continue")
                self.assertEqual(o["work"], "crawl"); self.assertEqual(o["alert"], "none")
                self.assertEqual(o["next"], "continue", "a throttled run chains the next one like a budget pause")
                self.assertEqual(self.read("state/run.json")["throttled_runs"], n)
            o, _ = self.run_plan("--plan", "continue")
            self.assertEqual(o["alert"], "throttled"); self.assertEqual(o["next"], "continue")
            self.assertIn("3 consecutive runs", o["alert_title"])
            self.assertIn("2700 s", self.body(o))
            self.assertEqual(self.read("state/run.json")["throttled_runs"], 3)
            self.assertNotIn("throttled", o["resolve"])
        with mock.patch.object(self.crawl, "run", lambda budget, wm=None: "budget"):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["next"], "continue"); self.assertEqual(o["alert"], "none")
        self.assertIn("throttled", o["resolve"].split(","))
        self.assertEqual(self.read("state/run.json")["throttled_runs"], 0)

    def test_finished_crawl_chains_a_build_run(self):
        self.write("state/run.json", state("crawling"))
        self.write("sizing.json", sizing(1, depts=self.depts))
        with mock.patch.object(self.crawl, "run", lambda budget, wm=None: "done"):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["next"], "continue")

    def test_size_runs_before_the_crawl_with_the_same_client_and_budget(self):
        self.write("state/run.json", state("crawling"))
        seen = {}
        def fake_run(budget, wm=None):
            seen["budget"], seen["wm"] = budget, wm; return "budget"
        with mock.patch.object(self.crawl, "run", fake_run):
            o, _ = self.run_plan("--plan", "continue", "--budget-min", "42")
        self.assertEqual(o["work"], "size")
        self.assertEqual(seen["budget"], 42.0); self.assertIs(seen["wm"], self.wm)
        self.assertEqual(self.wm.calls, len(self.depts))
        siz = self.read("sizing.json")
        self.assertEqual(set(siz), set(self.depts)); self.assertEqual(siz[self.depts[0]]["est_items"], 800)
        self.assertEqual(o["next"], "continue")
        # the next run has fresh sizing and goes straight to the crawl
        with mock.patch.object(self.crawl, "run", fake_run):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["work"], "crawl"); self.assertEqual(self.wm.calls, len(self.depts))

    def test_budget_defaults_to_the_schedule(self):
        self.write("state/run.json", state("crawling"))
        self.write("sizing.json", sizing(1, depts=self.depts))
        seen = {}
        def fake_run(budget, wm=None):
            seen["budget"] = budget; return "budget"
        with mock.patch.object(self.crawl, "run", fake_run):
            self.run_plan("--plan", "continue")
        self.assertEqual(seen["budget"], ci.schedule()["budget_min"])

    def test_start_full_then_start_core(self):
        seen = []
        def fake_run(budget, wm=None):
            seen.append(self.read("state/run.json")["plan"]); return "budget"
        with mock.patch.object(self.crawl, "run", fake_run):
            o, _ = self.run_plan("--plan", "continue")
            self.assertEqual(o["work"], "start-full"); self.assertEqual(o["next"], "continue")
            st = self.read("state/run.json")
            self.assertEqual(st["plan"], "full"); self.assertEqual(st["status"], "crawling")
            self.assertEqual(len(st["departments"]), len(self.depts))
            self.assertTrue((self.root / "sizing.json").exists())            # sized before the first page
            # a published snapshot 8 days old -> core refresh
            self.write("state/run.json", state("published"))
            self.write("build/published/manifest.json", manifest(8))
            with mock.patch.object(ci, "utcnow", lambda: NOW):
                o, _ = self.run_plan("--plan", "continue")
            self.assertEqual(o["work"], "start-core")
            self.assertEqual(self.read("state/run.json")["plan"], "core")
        self.assertEqual(seen, ["full", "core"])

    def test_sizing_throttled_counts_as_a_throttled_run(self):
        from crawler.wm import Throttled
        self.write("state/run.json", state("crawling", throttled_runs=2))
        def boom(path):
            raise Throttled("429")
        self.wm.get = boom
        with mock.patch.object(self.crawl, "run", side_effect=AssertionError("crawl must not run")):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["work"], "size"); self.assertEqual(o["alert"], "throttled"); self.assertEqual(o["next"], "continue")
        self.assertEqual(self.read("state/run.json")["throttled_runs"], 3)

    def test_build_with_review_pending(self):
        self.write("state/run.json", state("crawled"))
        self.candidate()
        got = {}
        def check(wm=None):
            got["wm"] = wm; return "review"
        with mock.patch.object(self.process, "build", lambda: got.setdefault("built", True)), \
             mock.patch.object(self.qa, "check", check):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["work"], "build"); self.assertEqual(o["review"], "pending")
        self.assertEqual(o["alert"], "none"); self.assertEqual(o["next"], "")
        self.assertTrue(got["built"]); self.assertIs(got["wm"], self.wm)

    def test_build_without_credentials_passes_no_client(self):
        self.write("state/run.json", state("crawled"))
        self.candidate()
        got = {}
        def check(wm=None):
            got["wm"] = wm; return "review"
        with mock.patch.dict(os.environ, {"WM_CONSUMER_ID": "", "WM_PRIVATE_KEY": ""}), \
             mock.patch.object(self.process, "build", lambda: None), mock.patch.object(self.qa, "check", check):
            self.run_plan("--plan", "continue")
        self.assertIsNone(got["wm"])

    def test_build_hold_raises_gates_hold_with_the_report(self):
        self.write("state/run.json", state("crawled", run_id="20261007-full"))
        self.candidate("# Snapshot report\n\n- FAIL sentinels\n")
        with mock.patch.object(self.process, "build", lambda: None), mock.patch.object(self.qa, "check", lambda wm=None: "hold"):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["alert"], "gates-hold")
        self.assertIn("20261007-full", o["alert_title"])
        self.assertIn("- FAIL sentinels", self.body(o)); self.assertIn("plan=approve", self.body(o))
        self.assertEqual(o["review"], "none"); self.assertEqual(o["resolve"], "")

    def test_hold_after_a_skipped_review_names_the_missing_secret(self):
        self.write("state/run.json", state("crawled"))
        self.candidate()
        self.write("build/candidate/review-verdict.json", {"status": "skipped", "reason": "ANTHROPIC_API_KEY missing"})
        with mock.patch.object(self.process, "build", lambda: None), mock.patch.object(self.qa, "check", lambda wm=None: "hold"):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["alert"], "review-key-missing")
        self.assertIn("ANTHROPIC_API_KEY", self.body(o))

    def test_build_ready_publishes_and_resolves(self):
        self.write("state/run.json", state("crawled"))
        self.candidate()
        def publish(approve=False):
            self.write("build/published/manifest.json", {"version": "run-1", "items": 1, "published": iso(0)})
            self.write("state/run.json", state("published")); return True
        with mock.patch.object(self.process, "build", lambda: None), mock.patch.object(self.qa, "check", lambda wm=None: "ready"), \
             mock.patch.object(self.qa, "publish", publish):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["alert"], "none"); self.assertEqual(o["next"], "continue")
        self.assertEqual(set(o["resolve"].split(",")), set(ci.PUBLISH_RESOLVES))

    def test_publish_declined_is_a_hold(self):
        self.write("state/run.json", state("crawled"))
        self.candidate()
        with mock.patch.object(self.process, "build", lambda: None), mock.patch.object(self.qa, "check", lambda wm=None: "ready"), \
             mock.patch.object(self.qa, "publish", lambda approve=False: False):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["alert"], "gates-hold"); self.assertEqual(o["next"], "")

    def test_old_qa_check_signature_and_statuses_are_tolerated(self):
        self.write("state/run.json", state("crawled"))
        self.candidate()
        def old_check():
            return "awaiting_approval"
        with mock.patch.object(self.process, "build", lambda: None), mock.patch.object(self.qa, "check", old_check):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["alert"], "gates-hold")
        with mock.patch.object(self.process, "build", lambda: None), mock.patch.object(self.qa, "check", lambda wm=None: "banana"):
            self.write("state/run.json", state("crawled"))
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["alert"], "gates-hold")

    def test_recheck_reuses_the_candidate_and_rebuilds_only_when_it_is_missing(self):
        self.write("state/run.json", state("needs_review"))
        self.write("build/candidate/gates.json", gates("hold", "stale-hash"))
        self.candidate()
        with mock.patch.object(self.process, "build", side_effect=AssertionError("no rebuild")), \
             mock.patch.object(self.qa, "check", lambda wm=None: "review"):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["work"], "recheck"); self.assertEqual(o["review"], "pending")
        # candidate gone (only gates.json left): rebuild first
        (self.root / "build" / "candidate" / "items.jsonl.gz").unlink()
        self.write("state/run.json", state("needs_review"))
        built = []
        with mock.patch.object(self.process, "build", lambda: built.append(1)), mock.patch.object(self.qa, "check", lambda wm=None: "hold"):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["work"], "recheck"); self.assertEqual(built, [1]); self.assertEqual(o["alert"], "gates-hold")

    def test_recheck_rebuilds_when_raw_pages_exist(self):
        # a scope or rule edit only takes effect through process.build(): with raw pages on disk, recheck rebuilds
        self.write("state/run.json", state("needs_review"))
        self.write("build/candidate/gates.json", gates("hold", "stale-hash"))
        self.candidate()
        (self.root / "raw" / state("needs_review")["run_id"] / "976759").mkdir(parents=True, exist_ok=True)
        built = []
        with mock.patch.object(self.process, "build", lambda: built.append(1)), mock.patch.object(self.qa, "check", lambda wm=None: "hold"):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["work"], "recheck"); self.assertEqual(built, [1])

    def test_approve_during_a_crawl_leaves_it_running(self):
        self.write("state/run.json", state("crawling"))
        calls = []
        with mock.patch.object(self.qa, "publish", lambda approve=False: calls.append(approve) or True):
            o, _ = self.run_plan("--plan", "approve")
        self.assertEqual(calls, [True])
        self.assertEqual(self.store.read_json(self.root / "state" / "run.json")["status"], "crawling")

    def test_hold_with_unchanged_config_does_nothing(self):
        self.write("state/run.json", state("needs_review"))
        self.write("build/candidate/gates.json", gates("hold", ci.config_hash()))
        with mock.patch.object(self.process, "build", side_effect=AssertionError("no build")):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["work"], "none"); self.assertEqual(o["alert"], "none")

    def test_audit_due_alerts_or_resolves(self):
        self.write("state/run.json", state("published"))
        self.write("build/published/manifest.json", manifest(1))
        import crawler
        fake = types.ModuleType("crawler.audit")
        fake.run = lambda wm: {"match_rate": 0.91, "within_5pct": 0.95, "outlier_share": 0.001, "alert": True, "examples": [1]}
        with mock.patch.dict(sys.modules, {"crawler.audit": fake}), mock.patch.object(crawler, "audit", fake, create=True), \
             mock.patch.object(ci, "utcnow", lambda: NOW):
            o, _ = self.run_plan("--plan", "continue")
            self.assertEqual(o["work"], "audit"); self.assertEqual(o["alert"], "audit-regression")
            self.assertIn("0.91", o["alert_title"]); self.assertIn("- match_rate: 0.91", self.body(o))
            fake.run = lambda wm: {"match_rate": 0.99, "alert": False}
            o, _ = self.run_plan("--plan", "audit")
            self.assertEqual(o["alert"], "none"); self.assertEqual(o["resolve"], "audit-failed,audit-regression")
            # a skipped audit writes nothing itself; ci remembers the attempt so decide() waits a full period
            fake.run = lambda wm: {"status": "skipped", "alert": False, "reason": "no eligible rows"}
            o, _ = self.run_plan("--plan", "audit")
            self.assertEqual(o["alert"], "none"); self.assertEqual(o["resolve"], "")
            self.assertEqual(self.store.read_json(self.root / "audit" / "latest.json")["status"], "skipped")
            # an audit error is remembered (retried in TRANSIENT_RETRY_HOURS) and alerts after AUDIT_ERRORS_ALERT tries
            (self.root / "audit" / "latest.json").unlink()
            fake.run = lambda wm: {"status": "error", "alert": False, "reason": "live check unavailable: Throttled: 429"}
            latest = lambda: self.store.read_json(self.root / "audit" / "latest.json")
            for n in range(1, ci.AUDIT_ERRORS_ALERT):
                o, _ = self.run_plan("--plan", "audit")
                self.assertEqual(o["alert"], "none"); self.assertEqual(o["resolve"], "")
                self.assertEqual((latest()["status"], latest()["errors"]), ("error", n))
            o, _ = self.run_plan("--plan", "audit")
            self.assertEqual(o["alert"], "audit-failed"); self.assertEqual(latest()["errors"], ci.AUDIT_ERRORS_ALERT)
            # an HTTP 4xx (key revoked) alerts on the first attempt
            (self.root / "audit" / "latest.json").unlink()
            fake.run = lambda wm: {"status": "error", "alert": False,
                                   "reason": "live check unavailable after 0/500 rows: RuntimeError: HTTP 401 for /items"}
            o, _ = self.run_plan("--plan", "audit")
            self.assertEqual(o["alert"], "audit-failed"); self.assertEqual(latest()["errors"], 1)
            # a successful audit clears it
            fake.run = lambda wm: {"match_rate": 0.99, "alert": False}
            o, _ = self.run_plan("--plan", "audit")
            self.assertEqual(o["alert"], "none"); self.assertIn("audit-failed", o["resolve"].split(","))

    def test_audit_module_missing_is_a_clear_error(self):
        import crawler
        saved = crawler.__dict__.pop("audit", None)
        try:
            with mock.patch.dict(sys.modules, {"crawler.audit": None}):
                with self.assertRaises(SystemExit) as cm:
                    self.run_plan("--plan", "audit")
        finally:
            if saved is not None:
                crawler.audit = saved
        self.assertIn("audit.py", str(cm.exception))

    def test_identify_due_writes_the_marker(self):
        self.write("state/run.json", state("published"))
        self.write("build/published/manifest.json", manifest(1))
        self.write("audit/latest.json", {"checked": iso(1)})
        self.store.write_jsonl_gz(self.root / "build" / "published" / "items.jsonl.gz", [{"id": 1}])
        calls = []
        with mock.patch.object(ci.identify, "fetch", lambda: calls.append("fetch")), \
             mock.patch.object(ci.identify, "match", lambda: calls.append("match")), mock.patch.object(ci, "utcnow", lambda: NOW):
            o, _ = self.run_plan("--plan", "continue")
        self.assertEqual(o["work"], "identify"); self.assertEqual(calls, ["fetch", "match"])
        self.assertEqual(self.read("identify/latest.json")["refreshed"], NOW.isoformat(timespec="seconds"))
        with mock.patch.object(ci, "utcnow", lambda: NOW):
            self.assertEqual(self.run_plan("--plan", "peek")[0]["work"], "none")

    def test_identify_without_a_snapshot_skips_matching(self):
        calls = []
        with mock.patch.object(ci.identify, "fetch", lambda: calls.append("fetch")), \
             mock.patch.object(ci.identify, "match", lambda: calls.append("match")):
            o, _ = self.run_plan("--plan", "identify")
        self.assertEqual(calls, ["fetch"]); self.assertTrue((self.root / "identify" / "latest.json").exists())


class LiveWM:
    """Walmart as the resumed live crawl sees it: the saved cursor of the department in progress gets one final page of
    200 items, every other request (sizing or an unstarted department's first page) one page and no next page."""

    def __init__(self, cursor, total_pages=1579):
        self.cursor, self.total_pages = cursor, total_pages
        self.calls = 0; self.throttle_waited = 0; self.paths = []

    def get(self, path):
        self.calls += 1; self.paths.append(path)
        cat = path.split("category=")[1].split("&")[0]
        if path == self.cursor:
            items = [{"itemId": 9_000_000 + i, "upc": f"0{i:011d}", "name": f"Food item {i}, 10 oz", "salePrice": 1.0,
                      "marketplace": False, "stock": "Available", "categoryPath": "Home Page/Food/Pantry"} for i in range(200)]
            return {"items": items, "totalPages": self.total_pages, "nextPage": None, "nextPageExist": False}
        if "lastDoc" in path or "maxId" in path:
            raise AssertionError(f"unexpected cursor request {path}")
        return {"items": [{"itemId": int(cat) * 10, "name": f"Item in {cat}, 10 oz", "salePrice": 3.0}],
                "totalPages": 1, "nextPage": None, "nextPageExist": False}


class LiveState(PlanBase):
    """Resuming from the real state/run.json of the crawl in progress (tests/fixtures/run-live.json, refreshed from the
    data-store branch before each merge): whichever department it is in, the crawl resumes at its saved cursor."""

    def setUp(self):
        super().setUp()
        self.live = live_state()
        self.dept = next(d for d in self.live["departments"] if d["status"] == "crawling")
        self.pending = [d for d in self.live["departments"] if d["status"] == "pending"]
        self.cursor = self.dept["next"]
        self.write("state/run.json", self.live)
        self.wm = LiveWM(self.cursor, self.dept["total_pages"])
        self.first_pages = {f"/paginated/items?category={d}&soldByWmt=true" for d in self.depts}

    def assert_resumed(self, o):
        st = self.read("state/run.json")
        self.assertEqual(st["status"], "crawled"); self.assertEqual(st["run_id"], self.live["run_id"])
        before = {d["id"]: d for d in self.live["departments"]}
        for d in st["departments"]:
            if before[d["id"]]["status"] == "done":
                self.assertEqual(d, before[d["id"]], f"{d['name']} was finished and must be untouched")
        cur = next(d for d in st["departments"] if d["id"] == self.dept["id"])
        self.assertEqual(cur["status"], "done"); self.assertIsNone(cur["next"])
        self.assertEqual(cur["pages"], self.dept["pages"] + 1); self.assertEqual(cur["items"], self.dept["items"] + 200)
        self.assertEqual(cur["parts"], self.dept["parts"] + 1)
        part = self.root / "raw" / self.live["run_id"] / self.dept["id"] / f"part-{self.dept['parts'] + 1:04d}.jsonl.gz"
        rows = list(self.store.iter_jsonl_gz(part))
        self.assertEqual(len(rows), 200); self.assertEqual(rows[0]["itemId"], 9_000_000)
        self.assertTrue(all(d["status"] == "done" for d in st["departments"]))
        self.assertEqual(st["calls"], self.live["calls"] + self.wm.calls); self.assertEqual(st.get("throttled_runs", 0), 0)
        self.assertEqual(o["next"], "continue"); self.assertEqual(o["alert"], "none")
        self.assertIn("throttled", o["resolve"].split(","))

    def test_continue_without_sizing_sizes_then_resumes_at_the_saved_cursor(self):
        o, _ = self.run_plan("--plan", "continue", "--budget-min", "5")
        self.assertEqual(o["work"], "size")
        n = len(self.depts)
        self.assertEqual(set(self.wm.paths[:n]), self.first_pages)             # one sizing call per department first
        self.assertEqual(self.wm.paths[n], self.cursor)                        # then the crawl resumes exactly where it stopped
        siz = self.read("sizing.json")
        self.assertEqual(siz[self.dept["id"]]["total_pages"], 1); self.assertEqual(set(siz), set(self.depts))
        self.assert_resumed(o)
        self.assertEqual(self.wm.calls, n + 1 + len(self.pending))    # sizing + the last page + each unstarted first page

    def test_continue_with_sizing_resumes_at_the_saved_cursor_first(self):
        self.write("sizing.json", sizing(1, depts=self.depts))
        o, _ = self.run_plan("--plan", "continue", "--budget-min", "5")
        self.assertEqual(o["work"], "crawl")
        self.assertEqual(self.wm.paths[0], self.cursor)
        self.assertEqual(self.read("sizing.json"), sizing(1, depts=self.depts))  # untouched
        self.assert_resumed(o)
        self.assertEqual(self.wm.calls, 1 + len(self.pending))

    def test_peek_on_the_live_state(self):
        self.assertEqual(self.run_plan("--plan", "peek")[0]["work"], "size")
        self.write("sizing.json", sizing(1, depts=self.depts))
        o, text = self.run_plan("--plan", "peek")
        self.assertEqual(o["work"], "crawl"); self.assertIn("work=crawl", text); self.assertEqual(o["alert"], "none")
        self.assertEqual(self.wm.calls, 0)

    def test_manual_full_plan_resumes_the_live_crawl_instead_of_restarting(self):
        self.write("sizing.json", sizing(1, depts=self.depts))
        o, _ = self.run_plan("--plan", "full", "--budget-min", "5")
        self.assertEqual(self.wm.paths[0], self.cursor)
        self.assert_resumed(o)


class OtherPlans(PlanBase):
    def test_full_plan_on_a_finished_unbuilt_crawl_builds_it_and_chains_the_full_crawl(self):
        self.write("state/run.json", state("crawled", run_id="run-7"))
        (self.root / "raw" / "run-7" / "1").mkdir(parents=True)
        self.candidate()
        with mock.patch.object(self.crawl, "start", side_effect=AssertionError("must not restart")), \
             mock.patch.object(self.process, "build", lambda: None), mock.patch.object(self.qa, "check", lambda wm=None: "hold"):
            o, _ = self.run_plan("--plan", "full")
        self.assertEqual(o["next"], "full"); self.assertEqual(o["alert"], "gates-hold")
        self.assertTrue((self.root / "raw" / "run-7").exists())
        self.assertIn("waiting to be built", Path(os.environ["GITHUB_STEP_SUMMARY"]).read_text())

    def test_finish_ready_publishes(self):
        self.write("state/run.json", state("built"))
        self.candidate("# report\n\nStatus: ready\n")
        def publish(approve=False):
            self.write("build/published/manifest.json", {"version": "run-1", "items": 1, "published": iso(0)}); return True
        with mock.patch.object(self.qa, "finalize", lambda: "ready", create=True), mock.patch.object(self.qa, "publish", publish):
            o, text = self.run_plan("--plan", "finish")
        self.assertEqual(o["work"], "finish"); self.assertEqual(o["next"], "continue")
        self.assertIn("gates-hold", o["resolve"]); self.assertIn("Status: ready", text)

    def test_finish_hold(self):
        self.write("state/run.json", state("built"))
        self.candidate("# report\n\n- FAIL sample_review\n")
        self.write("build/candidate/review-verdict.json", {"status": "fail", "junk_rate": 0.2})
        with mock.patch.object(self.qa, "finalize", lambda: "hold", create=True):
            o, _ = self.run_plan("--plan", "finish")
        self.assertEqual(o["alert"], "gates-hold"); self.assertIn("FAIL sample_review", self.body(o))

    def test_finish_hold_names_the_review_fix(self):
        for kind, key, words in (("auth", "review-key-invalid", "Replace the key"),
                                 ("permission", "review-key-invalid", "Check the key's access"),
                                 ("credits", "review-credits", "Add credits")):
            self.write("state/run.json", state("built"))
            self.candidate("# report\n\n- FAIL sample_review\n")
            self.write("build/candidate/review-verdict.json", {"status": "error", "error_kind": kind, "reason": "HTTP 4xx: ..."})
            with mock.patch.object(self.qa, "finalize", lambda: "hold", create=True):
                o, _ = self.run_plan("--plan", "finish")
            self.assertEqual(o["alert"], key, kind); self.assertIn(words, self.body(o))
        self.assertIn("review-credits", ci.PUBLISH_RESOLVES); self.assertIn("review-key-invalid", ci.PUBLISH_RESOLVES)

    def test_finish_without_finalize_is_a_clear_error(self):
        self.write("state/run.json", state("built"))
        if hasattr(self.qa, "finalize"):
            self.skipTest("qa.finalize present")
        with self.assertRaises(SystemExit) as cm:
            self.run_plan("--plan", "finish")
        self.assertIn("finalize", str(cm.exception))

    def test_approve_publishes_and_resolves(self):
        self.write("state/run.json", state("needs_review"))
        seen = {}
        def publish(approve=False):
            seen["approve"] = approve; return True
        with mock.patch.object(self.qa, "publish", publish):
            o, _ = self.run_plan("--plan", "approve")
        self.assertTrue(seen["approve"]); self.assertEqual(o["next"], "continue")
        self.assertEqual(set(o["resolve"].split(",")), set(ci.PUBLISH_RESOLVES))
        with mock.patch.object(self.qa, "publish", lambda approve=False: False):
            o, _ = self.run_plan("--plan", "approve")
        self.assertEqual(o["next"], ""); self.assertEqual(o["resolve"], "")

    def test_size_plan(self):
        o, text = self.run_plan("--plan", "size")
        self.assertEqual(o["work"], "size"); self.assertEqual(self.wm.calls, len(self.depts))
        self.assertEqual(set(self.read("sizing.json")), set(self.depts))
        self.assertIn("estimated total", text)

    def test_full_and_core_plans_start_or_resume(self):
        seen = []
        with mock.patch.object(self.crawl, "run", lambda budget, wm=None: seen.append(self.read("state/run.json")["plan"]) or "budget"):
            o, _ = self.run_plan("--plan", "core")
            self.assertEqual(self.read("state/run.json")["plan"], "core"); self.assertEqual(o["next"], "continue")
            o, _ = self.run_plan("--plan", "full")                 # a crawl is in progress: resumed, not restarted
            self.assertEqual(self.read("state/run.json")["plan"], "core")
        self.assertEqual(seen, ["core", "core"])

    def test_status_plan_prints_the_next_work(self):
        self.write("state/run.json", state("crawled"))
        o, text = self.run_plan("--plan", "status")
        self.assertIn("next continue would: build", text); self.assertEqual(o["work"], "status")

    def test_alert_keeps_the_first_key_of_a_run(self):
        ci._reset_outputs("x")
        ci.alert("gates-hold", "a", "body a")
        ci.alert("throttled", "b", "body b")
        self.assertEqual(ci._outputs["alert"], "gates-hold")
        ci.resolve("a", "b", "a")
        self.assertEqual(ci._outputs["resolve"], ["a", "b"])


def _action_script():
    try:
        import yaml
    except ImportError:
        return None
    d = yaml.safe_load((REPO / ".github" / "actions" / "alert" / "action.yml").read_text())
    step = d["runs"]["steps"][0]
    return step["run"], step["env"]


def _workflow_step(step_id):
    try:
        import yaml
    except ImportError:
        return None
    d = yaml.safe_load((REPO / ".github" / "workflows" / "pipeline.yml").read_text())
    return next((s for s in d["jobs"]["run"]["steps"] if s.get("id") == step_id), None)


@unittest.skipUnless(shutil.which("bash") and _workflow_step("result"), "needs bash and pyyaml")
class CollectOutputs(unittest.TestCase):
    """The workflow's 'Collect outputs' step merges peek / run / finish results; run with GitHub's bash flags."""

    BASE = {"PEEK_ALERT": "none", "PEEK_TITLE": "", "PEEK_BODY": "", "CI_OUTCOME": "skipped", "CI_ALERT": "", "CI_TITLE": "",
            "CI_BODY": "", "CI_RESOLVE": "", "CI_NEXT": "", "FIN_OUTCOME": "skipped", "FIN_ALERT": "", "FIN_TITLE": "",
            "FIN_BODY": "", "FIN_RESOLVE": "", "FIN_NEXT": ""}

    def collect(self, **env):
        step = _workflow_step("result")
        self.assertEqual(set(step["env"]), set(self.BASE))     # the step reads exactly these
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.txt"; out.write_text("")
            e = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(out), **self.BASE, **env}
            r = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step["run"]], env=e,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return dict(l.partition("=")[::2] for l in out.read_text().splitlines() if l)

    def test_nothing_happened(self):
        o = self.collect()
        self.assertEqual(o, {"alert": "none", "alert_title": "", "alert_body_file": "", "resolve": "", "next": ""})

    def test_successful_run_resolves_pipeline_failed_and_merges_keys(self):
        o = self.collect(CI_OUTCOME="success", CI_RESOLVE="throttled,gates-hold", FIN_OUTCOME="success", FIN_RESOLVE="gates-hold,")
        self.assertEqual(set(o["resolve"].split(",")), {"throttled", "gates-hold", "pipeline-failed"})
        self.assertEqual(o["alert"], "none")

    def test_finish_alert_beats_run_alert_beats_peek_alert(self):
        o = self.collect(CI_OUTCOME="success", CI_ALERT="throttled", CI_TITLE="t", CI_BODY="/b", PEEK_ALERT="stale-prices", PEEK_TITLE="p")
        self.assertEqual((o["alert"], o["alert_title"], o["alert_body_file"]), ("throttled", "t", "/b"))
        o = self.collect(CI_OUTCOME="success", CI_ALERT="throttled", FIN_OUTCOME="success", FIN_ALERT="gates-hold", FIN_TITLE="held")
        self.assertEqual((o["alert"], o["alert_title"]), ("gates-hold", "held"))
        o = self.collect(PEEK_ALERT="stale-prices", PEEK_TITLE="20 days", PEEK_BODY="/p")
        self.assertEqual((o["alert"], o["alert_title"], o["alert_body_file"]), ("stale-prices", "20 days", "/p"))

    def test_alerts_from_failed_steps_are_ignored(self):
        o = self.collect(CI_OUTCOME="failure", CI_ALERT="throttled", FIN_OUTCOME="failure", FIN_ALERT="gates-hold")
        self.assertEqual(o["alert"], "none"); self.assertEqual(o["resolve"], "")

    def test_alert_raised_and_resolved_in_one_run_is_dropped(self):
        o = self.collect(CI_OUTCOME="success", PEEK_ALERT="stale-prices", CI_RESOLVE="gates-hold,stale-prices")
        self.assertEqual(o["alert"], "none"); self.assertIn("stale-prices", o["resolve"])

    def test_next_prefers_a_named_plan_over_continue(self):
        self.assertEqual(self.collect(CI_NEXT="continue")["next"], "continue")
        self.assertEqual(self.collect(CI_NEXT="continue", FIN_NEXT="continue")["next"], "continue")
        self.assertEqual(self.collect(CI_NEXT="", FIN_NEXT="continue")["next"], "continue")
        self.assertEqual(self.collect(CI_NEXT="full", FIN_NEXT="continue")["next"], "full")


GH_SHIM = r"""#!/usr/bin/env bash
# fake gh: logs every call, answers from canned files
echo "$*" >> "$SHIM_LOG"
case "$1 $2" in
  "issue list")    cat "$SHIM_DIR/issues.json" ;;
  "issue create")  echo "https://github.com/o/r/issues/99"
                   while [ $# -gt 0 ]; do [ "$1" = --body-file ] && cp "$2" "$SHIM_DIR/created-body.md"; shift; done ;;
  "issue view")    cat "$SHIM_DIR/last.txt" ;;
  "issue comment") while [ $# -gt 0 ]; do [ "$1" = --body-file ] && cp "$2" "$SHIM_DIR/comment-body.md"; shift; done ;;
  "issue close")   : ;;
  "label create")  [ -f "$SHIM_DIR/label-fails" ] && exit 1 ;;
  *) echo "unexpected gh call: $*" >&2; exit 1 ;;
esac
exit 0
"""


@unittest.skipUnless(shutil.which("bash") and shutil.which("jq") and _action_script(), "needs bash, jq and pyyaml")
class AlertAction(unittest.TestCase):
    """Runs the composite action's bash against a gh shim."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bin = self.tmp / "bin"; self.bin.mkdir()
        gh = self.bin / "gh"; gh.write_text(GH_SHIM); gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.shim = self.tmp / "shim"; self.shim.mkdir()
        (self.shim / "issues.json").write_text("[]"); (self.shim / "last.txt").write_text("")
        self.script, _ = _action_script()
        self.out = self.tmp / "out.txt"; self.rt = self.tmp / "rt"; self.rt.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_action(self, **inputs):
        env = {"PATH": f"{self.bin}:{os.environ['PATH']}", "SHIM_LOG": str(self.tmp / "log.txt"), "SHIM_DIR": str(self.shim),
               "GITHUB_OUTPUT": str(self.out), "RUNNER_TEMP": str(self.rt), "GH_TOKEN": "t", "REPO": "o/r",
               "RUN_URL": "https://github.com/o/r/actions/runs/1", "MAX_BODY_BYTES": "60000",
               "ALERT_KEY": "", "ALERT_TITLE": "", "ALERT_BODY": "", "ALERT_BODY_FILE": "", "ALERT_MODE": "open",
               "ALERT_LABEL": "pipeline-alert"}
        env.update({f"ALERT_{k.upper()}": v for k, v in inputs.items()})
        self.out.write_text("")
        r = subprocess.run(["bash", "-c", self.script], env=env, capture_output=True, text=True)
        log = (self.tmp / "log.txt").read_text() if (self.tmp / "log.txt").exists() else ""
        (self.tmp / "log.txt").write_text("")
        return r, log

    def outputs(self):
        return dict(l.partition("=")[::2] for l in self.out.read_text().splitlines() if l)

    def test_open_creates_a_labelled_issue_with_run_link_and_hash(self):
        r, log = self.run_action(key="gates-hold", title="snapshot held", body="line one\nline two")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("label create pipeline-alert", log)
        self.assertRegex(log, r"issue create .*--title \[gates-hold\] snapshot held .*--label pipeline-alert")
        body = (self.shim / "created-body.md").read_text()
        self.assertTrue(body.startswith("line one\nline two\n"))
        self.assertIn("Run: https://github.com/o/r/actions/runs/1", body); self.assertIn("sfb-alert-hash:", body)
        self.assertEqual(self.outputs()["issue_url"], "https://github.com/o/r/issues/99")

    def test_open_updates_an_existing_issue_only_when_the_body_changed(self):
        (self.shim / "issues.json").write_text(json.dumps([
            {"number": 3, "title": "[throttled] old", "url": "https://github.com/o/r/issues/3"},
            {"number": 5, "title": "[gates-hold] snapshot held", "url": "https://github.com/o/r/issues/5"}]))
        bf = self.tmp / "body.md"; bf.write_text("report body\n")
        r, log = self.run_action(key="gates-hold", title="x", body_file=str(bf))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("issue create", log); self.assertIn("issue view 5", log); self.assertIn("issue comment 5", log)
        comment = (self.shim / "comment-body.md").read_text()
        self.assertTrue(comment.startswith("report body\n"))
        self.assertEqual(self.outputs()["issue_url"], "https://github.com/o/r/issues/5")
        # same body again: the last comment carries the hash -> no new comment
        (self.shim / "last.txt").write_text(comment)
        (self.shim / "comment-body.md").unlink()
        r, log = self.run_action(key="gates-hold", title="x", body_file=str(bf))
        self.assertEqual(r.returncode, 0); self.assertNotIn("issue comment", log); self.assertIn("already reports", r.stdout)
        self.assertFalse((self.shim / "comment-body.md").exists())

    def test_long_body_is_truncated(self):
        r, log = self.run_action(key="k", body="x" * 70000)
        self.assertEqual(r.returncode, 0)
        body = (self.shim / "created-body.md").read_text()
        self.assertLess(len(body), 61000); self.assertIn("truncated", body)

    def test_resolve_closes_every_matching_issue_for_each_key(self):
        (self.shim / "issues.json").write_text(json.dumps([
            {"number": 3, "title": "[throttled] a", "url": "u3"}, {"number": 4, "title": "[throttled] b", "url": "u4"},
            {"number": 5, "title": "[gates-hold] c", "url": "u5"}, {"number": 6, "title": "[stale-prices] d", "url": "u6"}]))
        r, log = self.run_action(key="throttled, gates-hold,,pipeline-failed", mode="resolve")
        self.assertEqual(r.returncode, 0, r.stderr)
        closed = re.findall(r"issue close (\d+)", log)
        self.assertEqual(sorted(closed), ["3", "4", "5"])
        self.assertIn("--comment Cleared by pipeline run https://github.com/o/r/actions/runs/1", log)
        self.assertIn("resolve pipeline-failed: no open issue", r.stdout)
        self.assertEqual(self.outputs()["issue_url"], "")

    def test_never_fails_the_job(self):
        r, log = self.run_action(key="", mode="open")
        self.assertEqual(r.returncode, 0); self.assertIn("::warning::", r.stdout); self.assertEqual(log, "")
        r, _ = self.run_action(key="k", mode="sideways")
        self.assertEqual(r.returncode, 0); self.assertIn("unknown mode", r.stdout)
        (self.shim / "label-fails").write_text("")
        r, log = self.run_action(key="k", title="t")
        self.assertEqual(r.returncode, 0); self.assertIn("issue create", log)   # label trouble is a warning only
        r, _ = self.run_action(key="k", title="t", body="b")
        self.assertEqual(r.returncode, 0)

    def test_title_defaults_to_the_key_and_body_to_the_title(self):
        r, log = self.run_action(key="stale-prices")
        self.assertEqual(r.returncode, 0)
        self.assertRegex(log, r"--title \[stale-prices\] stale-prices ")
        self.assertTrue((self.shim / "created-body.md").read_text().startswith("stale-prices\n"))


if __name__ == "__main__":
    unittest.main()
