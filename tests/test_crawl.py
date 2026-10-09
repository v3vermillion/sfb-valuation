"""crawler/crawl.py: scope edits apply to the run in progress, split departments, and early ends Walmart reports."""
import importlib, json, os, shutil, tempfile, unittest
from pathlib import Path
from unittest import mock

CFG = {"departments": [
    {"id": "1", "name": "Food", "core": True},
    {"id": "2", "name": "Home", "core": False, "split": [{"id": "2_1", "name": "Kitchen"}, {"id": "2_2", "name": "Bath"}]},
    {"id": "3", "name": "Toys", "core": False},
]}
BASE = "/api-proxy/service/affil/product/v2/paginated/items"


def items(start, n):
    return [{"itemId": start + i, "name": f"Item {start + i}, 10 oz", "salePrice": 1.0} for i in range(n)]


class Script:
    """A Walmart whose answers are scripted per request path; anything unscripted is one item and the end."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = 0; self.throttle_waited = 0; self.paths = []

    def get(self, path):
        self.calls += 1; self.paths.append(path)
        if path in self.answers:
            a = self.answers[path]
            if isinstance(a, Exception):
                raise a
            return a
        if "lastDoc=" in path:      # a continuation after the real end: nothing follows
            return {"items": [], "totalPages": 1, "nextPage": None, "nextPageExist": False}
        cat = path.split("category=")[1].split("&")[0]
        return {"items": items(int(cat.replace("_", "")) * 1000, 1), "totalPages": 1, "nextPage": None,
                "nextPageExist": False}


def page(cat, first, n, *, total, last_doc=None, left=None, end=False):
    nxt = None if end else f"{BASE}?category={cat}&soldByWmt=true&count=200&lastDoc={first + n - 1}&remainingHits={left}"
    return {"items": items(first, n), "totalPages": total, "nextPage": nxt, "nextPageExist": not end}


class Crawl(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"SFB_STORE": str(self.tmp), "SFB_NO_COMMIT": "1"}); self.env.start()
        import crawler.store, crawler.crawl
        importlib.reload(crawler.store); importlib.reload(crawler.crawl)
        self.store, self.crawl = crawler.store, crawler.crawl
        self.cfg = json.loads(json.dumps(CFG))
        p = mock.patch.object(self.store, "config", lambda: self.cfg); p.start(); self.addCleanup(p.stop)
        p = mock.patch.object(self.crawl, "_tolerance", lambda: 0.3); p.start(); self.addCleanup(p.stop)

    def tearDown(self):
        self.env.stop(); shutil.rmtree(self.tmp)

    def state(self):
        return self.store.read_json(self.crawl.STATE)

    def dept(self, name, st=None):
        return next(d for d in (st or self.state())["departments"] if d["name"] == name)

    def raw(self, *parts):
        return self.tmp.joinpath("raw", self.state()["run_id"], *parts)

    # ------------------------------------------------------------------ split departments
    def test_a_split_department_is_crawled_node_by_node(self):
        self.crawl.start("full")
        home = self.dept("Home")
        self.assertEqual([u["id"] for u in home["units"]], ["2_1", "2_2"])
        wm = Script()
        self.assertEqual(self.crawl.run(5, wm=wm), "done")
        st = self.state()
        self.assertEqual(st["status"], "crawled")
        home = self.dept("Home", st)
        self.assertEqual((home["status"], home["pages"], home["items"], home["total_pages"]), ("done", 2, 2, 2))
        self.assertTrue(all(u["status"] == "done" for u in home["units"]))
        self.assertIn(f"/paginated/items?category=2_1&soldByWmt=true", wm.paths)
        self.assertNotIn(f"/paginated/items?category=2&soldByWmt=true", wm.paths)
        self.assertTrue(self.raw("2", "2_1", "part-0001.jsonl.gz").exists())
        self.assertTrue(self.raw("2", "2_2", "part-0001.jsonl.gz").exists())

    def test_a_budget_pause_inside_a_node_resumes_there(self):
        self.crawl.start("full")
        self.cfg["departments"] = [self.cfg["departments"][1]]
        cur = f"{BASE}?category=2_1&soldByWmt=true&count=200&lastDoc=21199&remainingHits=200"
        clock = [1000.0]

        class Slow(Script):
            def get(s, path):
                clock[0] += 3600          # each page takes an hour: the 1-minute budget ends after the first
                return Script.get(s, path)
        wm = Slow({"/paginated/items?category=2_1&soldByWmt=true": page("2_1", 21000, 200, total=2, left=200)})
        with mock.patch.object(self.crawl.time, "time", lambda: clock[0]):
            self.assertEqual(self.crawl.run(1, wm=wm), "budget")
        unit = self.dept("Home")["units"][0]
        self.assertEqual((unit["status"], unit["next"], unit["items"]), ("crawling", cur, 200))
        self.assertEqual(self.dept("Home")["status"], "crawling")
        wm2 = Script({cur: page("2_1", 21200, 200, total=2, end=True)})
        self.assertEqual(self.crawl.run(5, wm=wm2), "done")
        self.assertEqual(wm2.paths[0], cur)
        unit = self.dept("Home")["units"][0]
        self.assertEqual((unit["status"], unit["items"], unit["parts"]), ("done", 400, 2))

    # ------------------------------------------------------------------ scope edits during a run
    def test_scope_edits_apply_to_the_run_in_progress(self):
        self.cfg["departments"][1].pop("split")
        self.crawl.start("full")
        st = self.state()
        for d in st["departments"]:
            d["status"] = "done" if d["name"] != "Toys" else "pending"; d["pages"] = d["items"] = 5
        self.store.write_json(self.crawl.STATE, st)
        self.store.write_jsonl_gz(self.raw("2", "part-0001.jsonl.gz"), items(1, 5))
        food_before = self.dept("Food")
        # the owner splits Home and drops Toys
        self.cfg["departments"][1]["split"] = [{"id": "2_1", "name": "Kitchen"}]
        self.cfg["departments"].pop(2)
        wm = Script()
        self.assertEqual(self.crawl.run(5, wm=wm), "done")
        st = self.state()
        self.assertEqual(st["status"], "crawled")
        self.assertEqual(self.dept("Food", st), food_before)
        self.assertEqual((self.dept("Toys", st)["status"], self.dept("Toys", st)["pages"]), ("dropped", 5))
        home = self.dept("Home", st)
        self.assertEqual((home["status"], home["pages"], [u["id"] for u in home["units"]]), ("done", 1, ["2_1"]))
        self.assertFalse(self.raw("2", "part-0001.jsonl.gz").exists())
        self.assertEqual(wm.paths, ["/paginated/items?category=2_1&soldByWmt=true"])

    def test_a_changed_child_list_keeps_finished_nodes(self):
        self.crawl.start("full")
        self.crawl.run(5, wm=Script())
        st = self.state(); st["status"] = "crawling"; self.store.write_json(self.crawl.STATE, st)
        self.cfg["departments"][1]["split"] = [{"id": "2_1", "name": "Kitchen"}, {"id": "2_3", "name": "Storage"}]
        wm = Script()
        self.crawl.run(5, wm=wm)
        home = self.dept("Home")
        self.assertEqual([(u["id"], u["status"]) for u in home["units"]], [("2_1", "done"), ("2_3", "done")])
        self.assertEqual(wm.paths, ["/paginated/items?category=2_3&soldByWmt=true"])
        self.assertFalse(self.raw("2", "2_2").exists())
        self.assertEqual(home["pages"], 2)

    def test_a_department_added_to_a_full_run_is_crawled(self):
        self.crawl.start("full")
        self.cfg["departments"].append({"id": "4", "name": "Seasonal"})
        wm = Script()
        self.crawl.run(5, wm=wm)
        self.assertEqual(self.dept("Seasonal")["status"], "done")

    def test_sync_is_a_no_op_on_an_unchanged_scope(self):
        self.crawl.start("full")
        st = self.state()
        self.assertEqual(self.crawl.sync(st), [])

    # ------------------------------------------------------------------ early ends
    def test_an_early_end_with_hits_left_is_retried_from_the_last_item_and_continues(self):
        self.cfg["departments"] = [{"id": "1", "name": "Food"}]
        self.crawl.start("full")
        first = "/paginated/items?category=1&soldByWmt=true"
        p2 = f"{BASE}?category=1&soldByWmt=true&count=200&lastDoc=1199&remainingHits=5000"
        forged = f"{BASE}?category=1&soldByWmt=true&count=200&lastDoc=1399&remainingHits=4800"
        wm = Script({first: page("1", 1000, 200, total=26, left=5000),
                     p2: {**page("1", 1200, 200, total=26), "nextPage": None, "nextPageExist": False},   # Walmart: "the end"
                     forged: page("1", 1400, 200, total=26, end=True)})
        self.assertEqual(self.crawl.run(5, wm=wm), "done")
        forged2 = f"{BASE}?category=1&soldByWmt=true&count=200&lastDoc=1599&remainingHits=4600"
        self.assertEqual(wm.paths, [first, p2, forged, forged2])
        d = self.dept("Food")
        self.assertEqual((d["items"], d["pages"]), (600, 3))
        # still far short of Walmart's own 26 pages: truncated, not done
        self.assertEqual(d["status"], "truncated")
        self.assertNotIn("resume", d)
        self.assertEqual(self.state()["status"], "crawled")
        self.assertEqual(self.crawl.truncated(self.state()), ["Food: 3 of 26 pages"])

    def test_an_early_end_confirmed_by_an_empty_continuation_within_tolerance_is_done(self):
        self.cfg["departments"] = [{"id": "1", "name": "Food"}]
        self.crawl.start("full")
        first = "/paginated/items?category=1&soldByWmt=true"
        p2 = f"{BASE}?category=1&soldByWmt=true&count=200&lastDoc=1199&remainingHits=5000"
        forged = f"{BASE}?category=1&soldByWmt=true&count=200&lastDoc=1399&remainingHits=4800"
        wm = Script({first: page("1", 1000, 200, total=2, left=5000),
                     p2: {**page("1", 1200, 200, total=2), "nextPage": None, "nextPageExist": False},
                     forged: {"items": [], "totalPages": 2, "nextPage": None, "nextPageExist": False}})
        self.assertEqual(self.crawl.run(5, wm=wm), "done")
        d = self.dept("Food")
        self.assertEqual((d["status"], d["pages"], d["items"]), ("done", 2, 400))   # the empty answer is not a page

    def test_a_refused_continuation_ends_the_department(self):
        self.cfg["departments"] = [{"id": "1", "name": "Food"}]
        self.crawl.start("full")
        first = "/paginated/items?category=1&soldByWmt=true"
        forged = f"{BASE}?category=1&soldByWmt=true&count=200&lastDoc=1199&remainingHits=4800"
        wm = Script({first: {**page("1", 1000, 200, total=30), "nextPage": None, "nextPageExist": False}})
        # a first page carries no cursor to continue from: nothing to retry, the page count decides
        self.assertEqual(self.crawl.run(5, wm=wm), "done")
        self.assertEqual(self.dept("Food")["status"], "truncated")
        self.cfg["departments"] = [{"id": "9", "name": "Pets"}]
        self.crawl.start("full")  # still the old run (crawled, not crawling): start begins a new one
        st = self.state(); self.assertEqual(st["departments"][0]["name"], "Pets")
        first = "/paginated/items?category=9&soldByWmt=true"
        p2 = f"{BASE}?category=9&soldByWmt=true&count=200&lastDoc=1199&remainingHits=5000"
        forged = f"{BASE}?category=9&soldByWmt=true&count=200&lastDoc=1399&remainingHits=4800"
        wm = Script({first: page("9", 1000, 200, total=2, left=5000),
                     p2: {**page("9", 1200, 200, total=2), "nextPage": None, "nextPageExist": False},
                     forged: RuntimeError("HTTP 400 for cursor")})
        self.assertEqual(self.crawl.run(5, wm=wm), "done")
        self.assertEqual(self.dept("Pets")["status"], "done")

    def test_a_refused_child_node_fails_on_its_own_and_the_crawl_goes_on(self):
        self.crawl.start("full")
        wm = Script({"/paginated/items?category=2_2&soldByWmt=true": RuntimeError("HTTP 400 for /paginated: bad category")})
        self.assertEqual(self.crawl.run(5, wm=wm), "done")
        st = self.state()
        home = self.dept("Home", st)
        self.assertEqual([u["status"] for u in home["units"]], ["done", "failed"]); self.assertEqual(home["status"], "failed")
        self.assertEqual(self.dept("Toys", st)["status"], "done"); self.assertEqual(st["status"], "crawled")
        self.assertEqual(self.crawl.truncated(st), ["Home / Bath: refused by Walmart (HTTP 400 for /paginated: bad category)"])

    def test_an_auth_error_is_never_a_failed_department(self):
        self.cfg["departments"] = [{"id": "1", "name": "Food"}]
        self.crawl.start("full")
        wm = Script({"/paginated/items?category=1&soldByWmt=true": RuntimeError("HTTP 401 for /paginated")})
        with self.assertRaises(RuntimeError):
            self.crawl.run(5, wm=wm)

    def test_an_error_on_an_ordinary_page_still_fails_loudly(self):
        self.cfg["departments"] = [{"id": "1", "name": "Food"}]
        self.crawl.start("full")
        cur = f"{BASE}?category=1&soldByWmt=true&count=200&lastDoc=1199&remainingHits=5000"
        wm = Script({"/paginated/items?category=1&soldByWmt=true": page("1", 1000, 200, total=3, left=5000),
                     cur: RuntimeError("HTTP 400 for cursor")})
        with self.assertRaises(RuntimeError):
            self.crawl.run(5, wm=wm)

    def test_a_normal_last_page_is_not_retried(self):
        self.cfg["departments"] = [{"id": "1", "name": "Food"}]
        self.crawl.start("full")
        first = "/paginated/items?category=1&soldByWmt=true"
        p2 = f"{BASE}?category=1&soldByWmt=true&count=200&lastDoc=1199&remainingHits=150"
        wm = Script({first: page("1", 1000, 200, total=2, left=150), p2: page("1", 1200, 150, total=2, end=True)})
        self.assertEqual(self.crawl.run(5, wm=wm), "done")
        self.assertEqual(wm.paths, [first, p2])
        self.assertEqual(self.dept("Food")["status"], "done")

    def test_a_null_body_is_an_error_not_a_crash(self):
        self.cfg["departments"] = [{"id": "1", "name": "Food"}]
        self.crawl.start("full")
        wm = Script({"/paginated/items?category=1&soldByWmt=true": None})
        with self.assertRaisesRegex(RuntimeError, "unexpected Walmart answer"):
            self.crawl.run(5, wm=wm)
        self.assertEqual(self.dept("Food")["pages"], 0)

    def test_status_lists_child_nodes(self):
        self.crawl.start("full")
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.crawl.status()
        self.assertIn("- Kitchen", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
