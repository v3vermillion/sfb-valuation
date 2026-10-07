"""crawler/sizing.py: one call per department, a complete sizing.json even when a department fails."""
import importlib, json, os, shutil, tempfile, unittest
from datetime import datetime, timezone

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
CFG = {"departments": [{"id": "976759", "name": "Food", "core": True},
                       {"id": "5440", "name": "Pets", "core": True},
                       {"id": "a b", "name": "Odd id", "core": False}]}


class FakeWM:
    def __init__(self, pages=None, fail=(), throttle=()):
        self.pages, self.fail, self.throttle = pages or {}, set(fail), set(throttle)
        self.paths = []

    def get(self, path):
        from crawler.wm import Throttled
        self.paths.append(path)
        cat = path.split("category=")[1].split("&")[0]
        if cat in self.throttle:
            raise Throttled("429 persisted")
        if cat in self.fail:
            raise RuntimeError(f"HTTP 400 for {path}")
        tp = self.pages.get(cat, 3)
        return {"items": [{"itemId": i} for i in range(5)], "totalPages": tp, "nextPage": None, "nextPageExist": False}


class Sizing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SFB_STORE"] = self.tmp; os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.sizing
        importlib.reload(crawler.store); importlib.reload(crawler.sizing)
        self.store, self.sizing = crawler.store, crawler.sizing

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_one_call_per_department_and_a_complete_file(self):
        wm = FakeWM(pages={"976759": 512, "5440": 40})
        res = self.sizing.run(wm, cfg=CFG, now=NOW)
        self.assertEqual(len(wm.paths), 3)
        self.assertEqual(wm.paths[0], "/paginated/items?category=976759&soldByWmt=true")
        self.assertIn("category=a%20b&soldByWmt=true", wm.paths[2])   # ids are URL-quoted
        self.assertEqual(set(res), {"976759", "5440", "a b"})
        food = res["976759"]
        self.assertEqual(food, {"name": "Food", "total_pages": 512, "first_page_items": 5, "est_items": 512 * 200,
                                "checked": "2026-10-07T12:00:00+00:00"})
        self.assertEqual(res["5440"]["est_items"], 8000)
        on_disk = json.loads((self.sizing.path()).read_text())
        self.assertEqual(on_disk, res)
        self.assertEqual(self.sizing.path(), self.store.ROOT / "sizing.json")

    def test_a_failing_department_is_recorded_and_the_others_still_sized(self):
        wm = FakeWM(fail={"5440"})
        res = self.sizing.run(wm, cfg=CFG, now=NOW)
        self.assertEqual(len(wm.paths), 3)
        pets = res["5440"]
        self.assertIsNone(pets["total_pages"]); self.assertIsNone(pets["est_items"])
        self.assertIn("RuntimeError: HTTP 400", pets["error"])
        self.assertEqual(pets["checked"], "2026-10-07T12:00:00+00:00")
        self.assertEqual(res["976759"]["total_pages"], 3)
        self.assertTrue(self.sizing.path().exists())

    def test_rate_limiting_propagates_and_nothing_is_written(self):
        from crawler.wm import Throttled
        wm = FakeWM(throttle={"5440"})
        with self.assertRaises(Throttled):
            self.sizing.run(wm, cfg=CFG, now=NOW)
        self.assertFalse(self.sizing.path().exists())

    def test_odd_total_pages_values_do_not_break_the_estimate(self):
        class OddWM:
            def __init__(self): self.n = 0
            def get(self, path):
                self.n += 1
                tp = ["12", None, True][self.n - 1]
                return {"items": [], "totalPages": tp}
        res = self.sizing.run(OddWM(), cfg=CFG, now=NOW)
        for r in res.values():
            self.assertIsNone(r["total_pages"]); self.assertIsNone(r["est_items"]); self.assertEqual(r["first_page_items"], 0)
            self.assertNotIn("error", r)

    def test_default_now_and_config_are_used(self):
        wm = FakeWM()
        res = self.sizing.run(wm)
        depts = {str(d["id"]) for d in self.store.config()["departments"]}
        self.assertEqual(set(res), depts)
        self.assertEqual(len(wm.paths), len(depts))
        stamp = datetime.fromisoformat(next(iter(res.values()))["checked"])
        self.assertLess(abs((datetime.now(timezone.utc) - stamp).total_seconds()), 120)

    def test_table_lists_every_department_with_the_estimate(self):
        res = self.sizing.run(FakeWM(pages={"976759": 10}, fail={"5440"}), cfg=CFG, now=NOW)
        t = self.sizing.table(res)
        self.assertIn("Food", t); self.assertIn("2000", t)
        self.assertIn("Pets", t); self.assertIn("ERROR RuntimeError", t)
        self.assertIn("estimated total", t)
        self.assertEqual(t.splitlines()[2].split()[0], "976759")   # largest department first


if __name__ == "__main__":
    unittest.main()
