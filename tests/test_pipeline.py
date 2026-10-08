"""End-to-end test of crawl -> process -> qa (gates + sample review) -> publish with a fake Walmart API."""
import importlib, json, os, shutil, tempfile, unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

FOOD_ITEMS = [
    {"itemId": 15544057, "upc": "078742054261", "name": "Great Value Whole Kernel Sweet Corn, Gluten-Free, 15.25 oz Can",
     "brandName": "Great Value", "salePrice": 0.87, "marketplace": False, "stock": "Available",
     "categoryPath": "Home Page/Food/Pantry/Canned goods/Canned vegetables/Canned corn"},
    {"itemId": 1033828, "upc": "075992724142", "name": "Fleetwood Mac", "salePrice": 7.88, "marketplace": False,
     "brandName": "Warner Records", "categoryPath": "Home Page/Food/Pantry/Lunchbox favorites"},
    {"itemId": 2, "upc": "012000001291", "name": "Mountain Dew Soda Pop, 12 fl oz, 12 Pack Cans", "brandName": "Mountain Dew",
     "salePrice": 7.48, "marketplace": False, "categoryPath": "Home Page/Food/Beverages/Soda", "clearance": True},
]


class FakeWM:
    """Two pages per department; food page 1 holds real-looking items incl. junk and a sentinel.
    `/items?ids=` answers with the same items (and prices) the pages served, so a live check matches."""
    ITEMS_CHUNK = 20

    def __init__(self, throttle_after=None, prices=None):
        self.calls = 0; self.throttle_waited = 0; self.throttle_after = throttle_after
        self.prices = prices or {}          # itemId -> salePrice override (a price change between runs)
        self.item_requests = []

    def _item(self, iid):
        iid = int(iid)
        base = next((dict(i) for i in FOOD_ITEMS if i["itemId"] == iid), None)
        if base is None and iid % 10 == 0:
            cat = iid // 10
            base = {"itemId": iid, "name": f"Item in {cat}, 10 oz", "salePrice": 3.0, "marketplace": False,
                    "categoryPath": f"Home Page/Dept {cat}"}
        if base and iid in self.prices:
            base["salePrice"] = self.prices[iid]
        return base

    def get(self, path):
        from crawler.wm import Throttled
        self.calls += 1
        if self.throttle_after and self.calls > self.throttle_after:
            raise Throttled("test")
        if path.startswith("/items?ids="):
            ids = path.split("ids=", 1)[1].split(",")
            self.item_requests.append(ids)
            return {"items": [it for it in (self._item(i) for i in ids) if it]}
        cat = path.split("category=")[1].split("&")[0]
        page2 = "maxId" in path
        items = []
        if cat == "976759" and not page2:
            items = [self._item(i["itemId"]) for i in FOOD_ITEMS]
        elif not page2:
            items = [self._item(int(cat) * 10)]
        nxt = None if page2 else f"/api-proxy/service/affil/product/v2/paginated/items?category={cat}&soldByWmt=true&maxId=9"
        return {"items": items, "totalPages": 2, "nextPage": nxt, "nextPageExist": nxt is not None}

    def get_items(self, ids):
        from crawler.wm import Walmart
        return Walmart.get_items(self, ids)      # the real chunking code, over this fake transport


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SFB_STORE"] = self.tmp; os.environ["SFB_NO_COMMIT"] = "1"
        self.saved_env = {k: os.environ.pop(k, None) for k in ("WM_CONSUMER_ID", "WM_PRIVATE_KEY")}
        import crawler.store, crawler.crawl, crawler.process, crawler.history, crawler.review, crawler.qa
        for m in (crawler.store, crawler.crawl, crawler.process, crawler.history, crawler.review, crawler.qa):
            importlib.reload(m)
        self.store, self.crawl, self.process, self.qa = crawler.store, crawler.crawl, crawler.process, crawler.qa
        # narrow sentinels to the one item the fake API serves
        self.sent = Path(self.tmp) / "s.json"
        self.sent.write_text(json.dumps({"sentinels": [{"q": "gv corn", "all": ["great value", "corn"], "size": [15.25, "oz"]}]}))
        self.qa.SENTINELS = self.sent

    def tearDown(self):
        shutil.rmtree(self.tmp)
        for k, v in self.saved_env.items():
            if v is not None:
                os.environ[k] = v

    def _verdict(self, run_id, **kw):
        v = {"status": "pass", "systematic_junk": False, "junk_rate": 0.0, "junk_examples": [], "notes": "clean", "run_id": run_id}
        v.update(kw)
        self.store.write_json(self.qa.CAND / "review-verdict.json", v)

    def test_full_flow_with_pause_and_resume(self):
        self.crawl.start("core")
        out1 = self.crawl.run(60, wm=FakeWM(throttle_after=3))
        self.assertEqual(out1, "throttled")
        st = self.store.read_json(self.crawl.STATE)
        self.assertEqual(st["status"], "crawling")
        out2 = self.crawl.run(60, wm=FakeWM())
        self.assertEqual(out2, "done")
        st = self.store.read_json(self.crawl.STATE)
        self.assertEqual(st["status"], "crawled")
        run1 = st["run_id"]
        food = next(d for d in st["departments"] if d["name"] == "Food")
        self.assertEqual(food["pages"], 2)
        stats = self.process.build()
        self.assertEqual(stats["rejects_by_department"]["Food"].get("media"), 1)
        rows = {r["id"]: r for r in self.store.iter_jsonl_gz(self.process.BUILD / "candidate" / "items.jsonl.gz")}
        self.assertIn(15544057, rows); self.assertNotIn(1033828, rows)
        self.assertEqual(rows[2]["pack"], 12); self.assertIn("promo_price", rows[2]["flags"])
        self.assertTrue(rows[15544057]["primary"])

        # gates: deterministic ones pass against the fake API, the sample review is pending
        wm = FakeWM()
        self.assertEqual(self.qa.check(wm=wm), "review")
        self.assertEqual(wm.item_requests, [["15544057"]], "only the in-stock, non-promo, UPC-bearing primary row is live-checked")
        g = self.store.read_json(self.qa.CAND / "gates.json")
        self.assertEqual(g["status"], "review"); self.assertTrue(g["passed_deterministic"]); self.assertEqual(g["run_id"], run1)
        self.assertEqual(g["gates"]["live_match"]["value"], 1.0)
        self.assertIsNone(g["gates"]["sample_review"]["pass"])
        self.assertEqual(self.store.read_json(self.crawl.STATE)["status"], "built")
        sample = (self.qa.CAND / "review-sample.jsonl").read_text().splitlines()
        self.assertEqual(len(sample), len(rows))
        self.assertFalse(self.qa.publish(), "review pending: not publishable")
        self.assertEqual(self.qa.finalize(), "hold", "no verdict yet -> hold")
        self.assertEqual(self.store.read_json(self.crawl.STATE)["status"], "needs_review")
        self.assertFalse(self.qa.publish())
        self._verdict(run1)
        self.assertEqual(self.qa.finalize(), "ready")
        self.assertEqual(self.store.read_json(self.crawl.STATE)["status"], "built")
        self.assertTrue(self.qa.publish())
        man = self.store.read_json(self.qa.PUB / "manifest.json")
        self.assertEqual(man["version"], run1); self.assertTrue(man["gates_passed"]); self.assertFalse(man["approved_manually"])
        self.assertEqual(man["history"]["kind"], "baseline"); self.assertEqual(man["gates"]["status"], "ready")
        self.assertTrue((self.store.ROOT / "history" / man["history"]["file"]).exists())
        self.assertEqual(self.store.read_json(self.crawl.STATE)["status"], "published")

        # second (core) run with one price change: gates compare with the published snapshot; a stale
        # verdict never carries over; the publish records a changes file
        wm2 = FakeWM(prices={15544057: 0.97})

        class _Later:                      # run ids carry a second-resolution timestamp: start the next run "a minute later"
            @staticmethod
            def now(tz=None):
                return datetime.now(tz) + timedelta(minutes=1)
        with mock.patch.object(self.crawl, "datetime", _Later):
            self.crawl.start("core")
        self.crawl.run(60, wm=wm2)
        run2 = self.store.read_json(self.crawl.STATE)["run_id"]
        self.assertNotEqual(run1, run2)
        self.process.build()
        self.assertEqual(self.qa.check(wm=wm2), "review")
        self.assertFalse((self.qa.CAND / "review-verdict.json").exists(), "check removes the previous run's verdict")
        self.assertEqual(self.qa.finalize(), "hold")
        self._verdict(run2)
        self.assertEqual(self.qa.finalize(), "ready")
        self.assertTrue(self.qa.publish())
        man = self.store.read_json(self.qa.PUB / "manifest.json")
        self.assertEqual(man["version"], run2); self.assertEqual(man["history"]["kind"], "changes")
        changes = list(self.store.iter_jsonl_gz(self.store.ROOT / "history" / man["history"]["file"]))
        self.assertEqual([(c["id"], c["old"], c["new"]) for c in changes], [(15544057, 0.87, 0.97)])
        index = self.store.read_json(self.store.ROOT / "history" / "index.json")
        self.assertEqual([e["kind"] for e in index], ["baseline", "changes"])


if __name__ == "__main__":
    unittest.main()
