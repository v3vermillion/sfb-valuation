"""Throttle analysis on synthetic event streams, and the crawl wiring that records and applies it."""
import importlib, io, json, os, shutil, tempfile, unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

from crawler import throttle

T0 = 1_700_000_000.0


def sliding_limiter(n, window=60.0):
    """A server that accepts a request when fewer than n requests (counting rejected ones) arrived
    in the last `window` seconds."""
    seen = []
    def accept(t):
        while seen and seen[0] <= t - window:
            seen.pop(0)
        seen.append(t)
        return len(seen) <= n
    return accept


def simulate(accept, seconds, interval=1.25, cap=None):
    """A client paced like wm.Walmart (interval, optional 60 s cap, 5 s doubling back-off on 429,
    +15% interval per 429 up to 5 s) talking to `accept` for `seconds`; returns the event stream."""
    events, t, end, backoff, window = [], T0, T0 + seconds, 5.0, []
    while t < end:
        if cap:
            while window and window[0] <= t - 60:
                window.pop(0)
            if len(window) >= cap:
                t = window[0] + 60
                continue
            window.append(t)
        if accept(t):
            events.append([t, 200]); t += interval; backoff = 5.0
        else:
            events.append([t, 429]); events.append([t, "sleep", backoff])
            t += backoff; backoff = min(backoff * 2, 300); interval = min(interval * 1.15, 5.0)
    return events


def clean_stream(seconds, interval, cap=None):
    return simulate(lambda t: True, seconds, interval=interval, cap=cap)


class Analyze(unittest.TestCase):
    def test_per_minute_limiter_is_recognised_and_paced_just_under(self):
        ev = simulate(sliding_limiter(10), seconds=900)
        a = throttle.analyze(ev)
        self.assertGreaterEqual(a["status_429"], 3)
        self.assertEqual(a["pattern"], "per-minute")
        self.assertEqual(a["limit_per_min"], 10, a["windows"])
        self.assertEqual(a["limit_from_429s"], 10)
        self.assertEqual(a["windows"]["60s"]["min"], 10)
        self.assertEqual(a["windows"]["1s"]["max"], 0, "1.25 s spacing never puts two requests in one second")
        self.assertEqual(a["per_min"], 8)                       # 85% of 10, rounded down
        self.assertIn("0.85 x inferred limit 10/min", a["reason"])
        self.assertEqual(a["cap"], None)
        self.assertEqual(a["sleep_s"], sum(e[2] for e in ev if e[1] == "sleep"))
        self.assertEqual(a["requests"], len([e for e in ev if e[1] != "sleep"]))
        self.assertEqual(a["ok"] + a["status_429"], a["requests"])
        self.assertEqual(a["events"], len(ev))
        self.assertTrue(all(r["req_60s"] >= 10 for r in a["per_429"]), "every 429 had at least the limit before it")
        self.assertIsNone(a["safe_per_min"], "a client hitting the limit every minute never has two clean minutes")
        self.assertIsNone(a["consistent"])

    def test_a_spurious_429_does_not_drag_the_limit_down(self):
        ev = simulate(sliding_limiter(10), seconds=900)
        quiet = T0 + 60 * 60                                     # long after the stream, with nothing before it
        ev += [[quiet, 200], [quiet + 1.25, 200], [quiet + 2.5, 429], [quiet + 2.5, "sleep", 5.0], [quiet + 7.5, 200]]
        a = throttle.analyze(ev)
        self.assertEqual(a["windows"]["60s"]["min"], 2)
        self.assertEqual(a["limit_per_min"], 10, "a 429 after 2 requests cannot be a per-minute rejection")
        self.assertEqual(a["per_min"], 8)

    def test_the_busiest_clean_minute_is_a_lower_bound_for_the_limit(self):
        ev = clean_stream(600, interval=1.25)                    # 10 clean minutes at 48/min
        t = T0 + 700
        ev += [[t, 200], [t + 1.25, 200], [t + 2.5, 200],
               [t + 3.75, 429], [t + 3.75, "sleep", 5.0], [t + 8.75, 429], [t + 8.75, "sleep", 10.0],
               [t + 18.75, 429], [t + 18.75, "sleep", 20.0], [t + 38.75, 200]]
        a = throttle.analyze(ev)
        self.assertEqual(a["pattern"], "per-minute")
        self.assertEqual(a["safe_per_min"], 48)
        self.assertEqual([r["req_60s"] for r in a["per_429"]], [3, 4, 5])
        self.assertEqual(a["limit_from_429s"], 3)
        self.assertIs(a["consistent"], False)
        self.assertEqual(a["limit_per_min"], 48, "429s after 3-5 requests cannot be per-minute rejections when a clean minute held 48")
        self.assertEqual(a["per_min"], 40, "85% of the clean rate, not the 6/min floor one hiccup would otherwise force")
        self.assertIn("busiest clean minute", a["reason"])
        self.assertIn("not per-minute rejections", a["reason"])
        text = throttle.report(a)
        self.assertIn("inferred limit 48/min; busiest clean minute 48 ok", text)
        self.assertIn("not a simple per-minute window", text)
        self.assertIn("Pace: next cap 40/min", text)

    def test_per_second_burst_limiter_is_recognised(self):
        ev = simulate(sliding_limiter(2, window=1.0), seconds=300, interval=0.3)
        a = throttle.analyze(ev)
        self.assertGreaterEqual(a["status_429"], 3)
        self.assertEqual(a["pattern"], "per-second")
        self.assertEqual(a["limit_per_s"], 2)
        self.assertIsNone(a["consistent"])
        self.assertIsNone(a["per_min"], "no per-minute evidence and no cap to lower")
        self.assertIn("request spacing", a["reason"])
        self.assertIn("per-second pattern", throttle.report(a))

    def test_clean_run_under_a_cap_probes_upward(self):
        a = throttle.analyze(clean_stream(600, interval=3.0, cap=20), cap=20)
        self.assertEqual(a["status_429"], 0)
        self.assertEqual(a["per_min"], 22)
        self.assertEqual(a["safe_per_min"], 20)
        self.assertAlmostEqual(a["ok_per_min"], 20.0, delta=0.2)   # span is first-to-last request: a fencepost
        self.assertIn("probing up 10%", a["reason"])
        self.assertIsNone(throttle.analyze(clean_stream(600, interval=1.25, cap=48), cap=48)["per_min"], "at the ceiling: nothing to raise")
        self.assertIsNone(throttle.analyze(clean_stream(600, interval=1.25))["per_min"], "no cap: nothing to raise")
        self.assertIsNone(throttle.analyze(clean_stream(60, interval=3.0, cap=20), cap=20)["per_min"],
                          "a minute of traffic proves nothing")
        for cap, nxt in ((6, 7), (7, 8), (10, 11), (30, 33), (40, 44), (47, 48)):   # +10% is at least +1, never above 48
            self.assertEqual(throttle.analyze(clean_stream(600, interval=60 / cap, cap=cap), cap=cap)["per_min"], nxt, cap)

    def test_costly_429s_under_a_cap_lower_it_15_percent(self):
        ev = clean_stream(600, interval=3.0, cap=20)
        ev += [[T0 + 100.5, 429], [T0 + 100.5, "sleep", 6.0], [T0 + 300.5, 429], [T0 + 300.5, "sleep", 11.0]]
        a = throttle.analyze(ev, cap=20)
        self.assertEqual(a["status_429"], 2)
        self.assertGreaterEqual(a["lost_share"], throttle.INCIDENTAL_LOSS)
        self.assertEqual(a["per_min"], 17)
        self.assertIn("lowering 15%", a["reason"])
        self.assertEqual(throttle.analyze(ev, cap=6)["per_min"], 6, "never below the floor")
        self.assertEqual(throttle.analyze(ev, cap=7)["per_min"], 6)

    def test_429s_the_cap_did_not_cause_leave_it_alone(self):
        # 30 clean minutes at the 40/min cap, then a short outage: 429s after only a few requests, ~4% lost
        ev = clean_stream(1800, interval=1.25, cap=40)
        t = ev[-1][0] + 120
        ev += [[t, 200], [t + 1.5, 429], [t + 1.5, "sleep", 5.0], [t + 6.5, 429], [t + 6.5, "sleep", 10.0],
               [t + 16.5, 429], [t + 16.5, "sleep", 20.0], [t + 36.5, 429], [t + 36.5, "sleep", 40.0], [t + 76.5, 200]]
        a = throttle.analyze(ev, cap=40)
        self.assertGreater(a["lost_share"], throttle.INCIDENTAL_LOSS)
        self.assertLess(a["lost_share"], throttle.BOUND_TOLERATED_LOSS)
        self.assertIsNone(a["per_min"], a["reason"])
        self.assertIn("not the cap's doing", a["reason"])

    def test_a_single_429_in_a_short_capped_run_does_not_lower_the_cap(self):
        ev = clean_stream(230, interval=1.5, cap=40)
        t = ev[-1][0] + 1.5
        ev += [[t, 429], [t, "sleep", 6.3], [t + 6.3, 200]]
        a = throttle.analyze(ev, cap=40)
        self.assertGreater(a["lost_share"], throttle.INCIDENTAL_LOSS)
        self.assertIsNone(a["per_min"], a["reason"])
        # the rule itself: one 429, or a run shorter than MIN_SPAN_S, never lowers a cap
        nxt, why = throttle._recommend(1, 0.03, None, None, False, 40, 600)
        self.assertIsNone(nxt); self.assertIn("too little to lower it on", why)
        nxt, why = throttle._recommend(4, 0.05, None, None, False, 40, 60)
        self.assertIsNone(nxt)
        self.assertEqual(throttle._recommend(4, 0.05, None, None, False, 40, 600)[0], 34)

    def test_incidental_429s_leave_the_cap_alone(self):
        ev = clean_stream(3600, interval=3.0, cap=20)
        ev += [[T0 + 100.5, 429], [T0 + 100.5, "sleep", 6.0], [T0 + 2000.5, 429], [T0 + 2000.5, "sleep", 6.0]]
        a = throttle.analyze(ev, cap=20)
        self.assertEqual(a["status_429"], 2)
        self.assertLess(a["lost_share"], throttle.INCIDENTAL_LOSS)
        self.assertIsNone(a["per_min"], "nothing to change")
        self.assertIn("incidental", a["reason"])
        self.assertIn("Pace: unchanged", throttle.report(a))

    def test_many_429s_under_a_cap_never_loosen_it(self):
        ev = simulate(sliding_limiter(10), seconds=900, cap=20)
        a = throttle.analyze(ev, cap=20)
        self.assertGreaterEqual(a["status_429"], 3)
        self.assertLessEqual(a["per_min"], 17)
        self.assertGreaterEqual(a["per_min"], 6)

    def test_the_cap_converges_just_under_the_limit(self):
        """Closed loop: each run is analysed and the next starts with its recommendation."""
        limit, cap, rounds = 10, None, []
        for _ in range(9):
            a = throttle.analyze(simulate(sliding_limiter(limit), seconds=1800, cap=cap), cap=cap)
            rounds.append((cap, a["status_429"], a["ok"], a["per_min"]))
            cap = cap if a["per_min"] is None else a["per_min"]
        self.assertEqual([r[3] for r in rounds], [8, 9, 10, 11, 8, 9, 10, 11, 8], rounds)
        uncapped_ok = rounds[0][2]
        for cap, n429, ok, _ in rounds[1:]:
            if cap <= limit:
                self.assertEqual(n429, 0, f"cap {cap} under the {limit}/min limit must be clean")
                self.assertGreater(ok, uncapped_ok, "a clean capped run fetches more than the uncapped one")
            else:
                self.assertGreaterEqual(n429, 3, "a cap above the limit is punished and lowered again")

    def test_empty_stream(self):
        a = throttle.analyze([])
        self.assertEqual((a["requests"], a["status_429"], a["pattern"], a["per_min"], a["safe_per_min"]), (0, 0, None, None, None))
        self.assertEqual(throttle.report(a), "Throttle: no requests recorded.")
        self.assertIsNone(throttle.analyze([], cap=20)["per_min"], "no traffic: keep whatever cap there was")

    def test_per_429_rows_and_gaps(self):
        ev = [[T0, 200], [T0 + 0.5, 200], [T0 + 1.0, 429], [T0 + 1.0, "sleep", 5.0], [T0 + 6.5, 200], [T0 + 7.0, 429], [T0 + 7.0, "sleep", 10.0]]
        a = throttle.analyze(ev)
        first, second = a["per_429"]
        self.assertEqual((first["req_1s"], first["req_10s"], first["req_60s"], first["ok_60s"]), (1, 2, 2, 2),
                         "the request exactly 1 s before the 429 is outside its 1 s window, as in the client's own window")
        self.assertIsNone(first["since_prev_s"])
        self.assertEqual(second["since_prev_s"], 6.0)
        self.assertEqual((second["req_1s"], second["req_60s"], second["ok_60s"]), (1, 4, 3))
        self.assertEqual(a["gap_s"], {"min": 6.0, "median": 6.0, "max": 6.0})
        self.assertEqual(a["span_s"], 17.0, "the span ends when the last sleep ends")
        self.assertEqual(a["sleep_s"], 15.0)
        self.assertEqual(a["windows"]["300s"], {"min": 2, "median": 3, "max": 4})

    def test_5xx_and_network_errors_are_counted_but_never_mistaken_for_429s(self):
        ev = [[T0, 200], [T0 + 1.25, 503], [T0 + 6.25, 0], [T0 + 16.25, 200]]
        a = throttle.analyze(ev)
        self.assertEqual((a["requests"], a["ok"], a["status_429"], a["status_5xx"], a["network_errors"]), (4, 2, 0, 1, 1))
        self.assertIsNone(a["pattern"])
        self.assertIsNone(a["per_min"])

    def test_report_text_and_cli(self):
        a = throttle.analyze(simulate(sliding_limiter(10), seconds=900))
        text = throttle.report(a)
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertRegex(lines[0], r"^Throttle: \d+ x 429 in 15 min; [\d.]+ min lost to back-off \(\d+% of the run\)\. \d+ requests, \d+ ok \([\d.]+ ok/min\)\.$")
        self.assertIn("Limit: per-minute pattern; 429s came after 10-", lines[1])
        self.assertIn("inferred limit 10/min", lines[1])
        self.assertTrue(lines[2].startswith("Pace: next cap 8/min (0.85 x inferred limit 10/min); this run: no cap"), lines[2])
        tmp = tempfile.mkdtemp()
        try:
            p = Path(tmp) / "x.events.jsonl"
            p.write_text("".join(json.dumps(e) + "\n" for e in [[T0, 200], [T0 + 1.25, 200]]) + '{"not": "an event"}\n\n[truncated')
            self.assertEqual(throttle.load_events(p), [[T0, 200], [T0 + 1.25, 200]], "torn and foreign lines are skipped")
            out = io.StringIO()
            with redirect_stdout(out):
                throttle.main([str(p), "--cap", "20", "--json"])
            self.assertIn("Throttle: no 429s in 0 min; 2 requests, 2 ok", out.getvalue())
            self.assertIn('"per_min": null', out.getvalue(), "1.25 s of traffic is too short to judge: the cap stays")
        finally:
            shutil.rmtree(tmp)


class EventWM:
    """Two pages per department like tests.test_pipeline.FakeWM, but every page costs a 429 and a
    6 s back-off first, and the client records events the way wm.Walmart does."""
    def __init__(self, throttle_after=None, t0=T0):
        self.calls = 0; self.throttle_waited = 0.0; self.events = []; self.t = t0
        self.throttle_after = throttle_after

    def get(self, path):
        from crawler.wm import Throttled
        self.calls += 1
        if self.throttle_after and self.calls > self.throttle_after:
            raise Throttled("test")
        self.events.append((self.t, 429)); self.events.append((self.t, "sleep", 6.0))
        self.t += 6.0; self.throttle_waited += 6.0
        self.events.append((self.t, 200)); self.t += 1.25
        cat = path.split("category=")[1].split("&")[0]
        page2 = "maxId" in path
        nxt = None if page2 else f"/api-proxy/service/affil/product/v2/paginated/items?category={cat}&soldByWmt=true&maxId=9"
        return {"items": [], "totalPages": 2, "nextPage": nxt, "nextPageExist": nxt is not None}

    def drain_events(self):
        ev, self.events = self.events, []
        return ev

    def stats(self):
        return {"requests": self.calls, "status_429": self.calls, "sleep_s": self.throttle_waited}


class _Later:
    """datetime stand-in for crawl.now()/run ids: a second start in the same second would reuse the run_id."""
    @staticmethod
    def now(tz=None):
        return datetime(2030, 1, 1, tzinfo=tz)


class CrawlWiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SFB_STORE"] = self.tmp; os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.crawl
        for m in (crawler.store, crawler.crawl):
            importlib.reload(m)
        self.store, self.crawl = crawler.store, crawler.crawl
        self.throttle_dir = Path(self.tmp) / "throttle"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self, *a, **kw):
        out = io.StringIO()
        with redirect_stdout(out):
            outcome = self.crawl.run(*a, **kw)
        return outcome, out.getvalue()

    def test_run_records_events_analyses_them_and_sets_the_pace(self):
        self.crawl.start("core")
        run_id = self.store.read_json(self.crawl.STATE)["run_id"]
        wm = EventWM()
        outcome, out = self._run(60, wm=wm)
        self.assertEqual(outcome, "done")
        self.assertIn("Throttle:", out)
        lines = [json.loads(l) for l in (self.throttle_dir / f"{run_id}.events.jsonl").read_text().splitlines()]
        self.assertEqual(len(lines), 3 * wm.calls)
        self.assertEqual(lines[0], [T0, 429]); self.assertEqual(lines[1], [T0, "sleep", 6.0]); self.assertEqual(lines[2], [T0 + 6.0, 200])
        self.assertEqual(wm.events, [], "everything was drained")
        analysis = self.store.read_json(self.throttle_dir / f"{run_id}.analysis.json")
        self.assertEqual(analysis["run_id"], run_id)
        self.assertEqual(len(analysis["invocations"]), 1)
        a = analysis["invocations"][0]
        self.assertEqual(a["status_429"], wm.calls)
        self.assertEqual(a["client"]["requests"], wm.calls)
        self.assertEqual(a["run_id"], run_id)
        self.assertEqual(analysis["totals"]["requests"], 2 * wm.calls)
        self.assertEqual(analysis["totals"]["invocations"], 1)
        state = self.store.read_json(self.crawl.STATE)
        self.assertEqual(state["status"], "crawled")
        self.assertEqual(state["throttle_wait_s"], int(wm.throttle_waited))
        pace = state["pace"]
        self.assertEqual(pace["run_id"], run_id)
        self.assertEqual(pace["inferred"]["status_429"], wm.calls)
        self.assertEqual(pace["inferred"]["pattern"], "per-minute")
        self.assertTrue(6 <= pace["per_min"] <= 48, pace)
        self.assertEqual(pace["per_min"], a["per_min"])
        self.assertNotIn("per_429", pace["inferred"], "state carries the summary, the analysis file the detail")
        # status prints the pace line
        out = io.StringIO()
        with redirect_stdout(out):
            self.crawl.status()
        self.assertIn(f"pace: {pace['per_min']}/min cap (set {pace['updated']} after run {run_id}: {wm.calls} x 429, pattern per-minute", out.getvalue())
        # a new run keeps the pace, drops the old run's throttle files and hands the cap to the client
        (self.throttle_dir / "unrelated.txt").write_text("x")
        with mock.patch.object(self.crawl, "datetime", _Later):
            self.crawl.start("core")
        state2 = self.store.read_json(self.crawl.STATE)
        self.assertNotEqual(state2["run_id"], run_id)
        self.assertEqual(state2["pace"], pace)
        self.assertEqual(sorted(p.name for p in self.throttle_dir.iterdir()), [])
        with mock.patch.object(self.crawl, "Walmart", return_value=EventWM()) as W:
            self._run(60)
        W.assert_called_once_with(max_per_min=pace["per_min"])
        self.assertEqual(len(self.store.read_json(self.crawl.STATE)["pace"]["inferred"]), len(pace["inferred"]))

    def test_two_invocations_share_one_events_file_and_the_totals_add_up(self):
        self.crawl.start("core")
        run_id = self.store.read_json(self.crawl.STATE)["run_id"]
        first = EventWM(throttle_after=3)
        outcome, _ = self._run(60, wm=first)
        self.assertEqual(outcome, "throttled")
        self.assertEqual(self.store.read_json(self.crawl.STATE)["status"], "crawling")
        pace1 = self.store.read_json(self.crawl.STATE)["pace"]
        self.assertEqual(pace1["inferred"]["requests"], 6, "3 pages: three 429s and three 200s")
        second = EventWM(t0=T0 + 3600)
        with mock.patch.object(self.crawl, "Walmart", return_value=second) as W:
            outcome, _ = self._run(60)
        W.assert_called_once_with(max_per_min=pace1["per_min"])
        self.assertEqual(outcome, "done")
        lines = (self.throttle_dir / f"{run_id}.events.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 3 * (3 + second.calls))
        self.assertEqual(json.loads(lines[9]), [T0 + 3600, 429], "the second invocation appends after the first")
        analysis = self.store.read_json(self.throttle_dir / f"{run_id}.analysis.json")
        self.assertEqual([a["requests"] for a in analysis["invocations"]], [6, 2 * second.calls])
        totals = analysis["totals"]
        self.assertEqual(totals["invocations"], 2)
        self.assertEqual(totals["requests"], 6 + 2 * second.calls)
        self.assertEqual(totals["status_429"], 3 + second.calls)
        self.assertEqual(totals["ok"], 3 + second.calls)
        self.assertEqual(totals["sleep_s"], 6.0 * (3 + second.calls))
        self.assertAlmostEqual(totals["span_s"], sum(a["span_s"] for a in analysis["invocations"]), places=1)
        self.assertAlmostEqual(totals["ok_per_min"], totals["ok"] / (totals["span_s"] / 60), places=1)
        state = self.store.read_json(self.crawl.STATE)
        self.assertEqual(state["status"], "crawled")
        self.assertEqual(state["pace"]["run_id"], run_id)
        self.assertEqual(state["calls"], 4 + second.calls, "the throttled attempt counted as a call too")

    def test_a_client_without_events_is_left_alone(self):
        class Plain(EventWM):
            drain_events = None
            def get(self, path):
                page = super().get(path); self.events.clear(); return page
        self.crawl.start("core")
        self.assertEqual(self._run(60, wm=Plain())[0], "done")
        self.assertFalse(self.throttle_dir.exists())
        self.assertNotIn("pace", self.store.read_json(self.crawl.STATE))
        out = io.StringIO()
        with redirect_stdout(out):
            self.crawl.status()
        self.assertIn("pace: no cap yet", out.getvalue())

    def test_nothing_to_infer_keeps_the_previous_cap(self):
        self.crawl.start("core")
        state = self.store.read_json(self.crawl.STATE)
        state["pace"] = {"per_min": 12, "inferred": {}, "updated": "x", "run_id": "old"}
        self.store.write_json(self.crawl.STATE, state)
        class Quiet(EventWM):
            def get(self, path):
                self.calls += 1
                self.events.append((self.t, 200)); self.t += 5.0        # 1 request: too short to judge
                return {"items": [], "totalPages": 1, "nextPage": None, "nextPageExist": False}
        with mock.patch.object(self.crawl, "Walmart", return_value=Quiet()) as W:
            self._run(60)
        W.assert_called_once_with(max_per_min=12)
        pace = self.store.read_json(self.crawl.STATE)["pace"]
        self.assertEqual(pace["per_min"], 12)
        self.assertNotEqual(pace["run_id"], "old")
        self.assertIn("too short to judge", pace["inferred"]["reason"])

    def test_an_analysis_failure_never_breaks_the_crawl(self):
        self.crawl.start("core")
        state = self.store.read_json(self.crawl.STATE)
        state["pace"] = {"per_min": 12, "inferred": {}, "updated": "x", "run_id": "old"}
        self.store.write_json(self.crawl.STATE, state)
        wm = EventWM()
        with mock.patch.object(self.crawl.throttle, "analyze", side_effect=ZeroDivisionError("boom")):
            outcome, out = self._run(60, wm=wm)
        self.assertEqual(outcome, "done")
        self.assertIn("pace: analysis failed (ZeroDivisionError('boom')); keeping 12 cap", out)
        state = self.store.read_json(self.crawl.STATE)
        self.assertEqual(state["status"], "crawled", "the crawl finished and saved")
        self.assertEqual(state["pace"]["per_min"], 12, "the previous pace stands")
        self.assertEqual(state["pace"]["run_id"], "old")
        lines = (self.throttle_dir / f"{state['run_id']}.events.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 3 * wm.calls, "the events were still logged for a later look")
        self.assertFalse((self.throttle_dir / f"{state['run_id']}.analysis.json").exists())


if __name__ == "__main__":
    unittest.main()
