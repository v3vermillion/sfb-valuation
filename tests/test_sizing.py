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
        cfg = self.store.config()["departments"]
        depts = {str(d["id"]) for d in cfg}
        units = {str(u["id"]) for d in cfg for u in d.get("split") or []}
        self.assertEqual(set(res), depts | units)
        self.assertEqual(len(wm.paths), len(depts) + len(units) - sum(1 for d in cfg if d.get("split")))
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


class SplitSizing(unittest.TestCase):
    setUp, tearDown = Sizing.setUp, Sizing.tearDown

    def test_a_split_department_is_sized_per_child_node_and_as_their_sum(self):
        cfg = {"departments": [{"id": "976759", "name": "Food"},
                               {"id": "4044", "name": "Home", "split": [{"id": "4044_1", "name": "Kitchen"},
                                                                        {"id": "4044_2", "name": "Bath"}]}]}
        wm = FakeWM(pages={"4044_1": 40, "4044_2": 7})
        res = self.sizing.run(wm, cfg=cfg, now=NOW)
        self.assertEqual([p.split("category=")[1].split("&")[0] for p in wm.paths], ["976759", "4044_1", "4044_2"])
        self.assertEqual(res["4044"]["total_pages"], 47); self.assertEqual(res["4044"]["units"], ["4044_1", "4044_2"])
        self.assertEqual(res["4044_1"]["total_pages"], 40); self.assertNotIn("error", res["4044"])
        self.assertIn("estimated total", self.sizing.table(res))
        self.assertIn(str((3 + 47) * 200), self.sizing.table(res))       # child nodes counted once

    def test_a_failed_child_node_leaves_the_department_unsized_with_the_reason(self):
        cfg = {"departments": [{"id": "4044", "name": "Home", "split": [{"id": "4044_1", "name": "Kitchen"},
                                                                       {"id": "4044_2", "name": "Bath"}]}]}
        res = self.sizing.run(FakeWM(fail={"4044_2"}), cfg=cfg, now=NOW)
        self.assertIsNone(res["4044"]["total_pages"]); self.assertIn("Bath: RuntimeError", res["4044"]["error"])
