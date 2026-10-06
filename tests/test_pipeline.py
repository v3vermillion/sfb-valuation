"""End-to-end test of crawl -> process -> qa -> publish with a fake Walmart API."""
import importlib, json, os, shutil, tempfile, unittest
from pathlib import Path


class FakeWM:
    """Two pages per department; food page 1 holds real-looking items incl. junk and a sentinel."""
    def __init__(self, throttle_after=None):
        self.calls = 0; self.throttle_waited = 0; self.throttle_after = throttle_after

    def get(self, path):
        from crawler.wm import Throttled
        self.calls += 1
        if self.throttle_after and self.calls > self.throttle_after:
            raise Throttled("test")
        cat = path.split("category=")[1].split("&")[0]
        page2 = "maxId" in path
        items = []
        if cat == "976759" and not page2:
            items = [
                {"itemId": 15544057, "upc": "078742054261", "name": "Great Value Whole Kernel Sweet Corn, Gluten-Free, 15.25 oz Can",
                 "brandName": "Great Value", "salePrice": 0.87, "marketplace": False, "stock": "Available",
                 "categoryPath": "Home Page/Food/Pantry/Canned goods/Canned vegetables/Canned corn"},
                {"itemId": 1033828, "upc": "075992724142", "name": "Fleetwood Mac", "salePrice": 7.88, "marketplace": False,
                 "brandName": "Warner Records", "categoryPath": "Home Page/Food/Pantry/Lunchbox favorites"},
                {"itemId": 2, "upc": "012000001291", "name": "Mountain Dew Soda Pop, 12 fl oz, 12 Pack Cans", "brandName": "Mountain Dew",
                 "salePrice": 7.48, "marketplace": False, "categoryPath": "Home Page/Food/Beverages/Soda", "clearance": True},
            ]
        elif not page2:
            items = [{"itemId": int(cat) * 10, "name": f"Item in {cat}, 10 oz", "salePrice": 3.0, "marketplace": False,
                      "categoryPath": f"Home Page/Dept {cat}"}]
        nxt = None if page2 else f"/api-proxy/service/affil/product/v2/paginated/items?category={cat}&soldByWmt=true&maxId=9"
        return {"items": items, "totalPages": 2, "nextPage": nxt, "nextPageExist": nxt is not None}


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SFB_STORE"] = self.tmp; os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.crawl, crawler.process, crawler.qa
        for m in (crawler.store, crawler.crawl, crawler.process, crawler.qa):
            importlib.reload(m)
        self.store, self.crawl, self.process, self.qa = crawler.store, crawler.crawl, crawler.process, crawler.qa
        # narrow sentinels to the one item the fake API serves
        self.sent = Path(self.tmp) / "s.json"
        self.sent.write_text(json.dumps({"sentinels": [{"q": "gv corn", "all": ["great value", "corn"], "size": [15.25, "oz"]}]}))
        self.qa.SENTINELS = self.sent

    def tearDown(self):
        shutil.rmtree(self.tmp)

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
        food = next(d for d in st["departments"] if d["name"] == "Food")
        self.assertEqual(food["pages"], 2)
        stats = self.process.build()
        self.assertEqual(stats["rejects_by_department"]["Food"].get("media_misfiled"), 1)
        rows = {r["id"]: r for r in self.store.iter_jsonl_gz(self.process.BUILD / "candidate" / "items.jsonl.gz")}
        self.assertIn(15544057, rows); self.assertNotIn(1033828, rows)
        self.assertEqual(rows[2]["pack"], 12); self.assertIn("promo_price", rows[2]["flags"])
        self.assertTrue(rows[15544057]["primary"])
        self.assertEqual(self.qa.check(), "awaiting_approval")
        self.assertFalse(self.qa.publish())
        self.assertTrue(self.qa.publish(approve=True))
        self.assertTrue((self.qa.PUB / "manifest.json").exists())
        # second (core) run: no throttling, gates compare with the published snapshot and auto-publish
        self.crawl.start("core"); self.crawl.run(60, wm=FakeWM())
        self.process.build()
        self.assertEqual(self.qa.check(), "ready")
        self.assertTrue(self.qa.publish())


if __name__ == "__main__":
    unittest.main()
