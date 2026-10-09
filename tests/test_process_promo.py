"""process.build: a promo keeps the last normal price for as long as the promo runs, not just the first crawl."""
import importlib, json, os, shutil, tempfile, unittest
from pathlib import Path
from unittest import mock

ITEM = {"itemId": 2, "upc": "012000001291", "name": "Mountain Dew Soda Pop, 12 fl oz, 12 Pack Cans", "brandName": "Mountain Dew",
        "salePrice": 5.00, "marketplace": False, "stock": "Available", "categoryPath": "Home Page/Food/Beverages/Soda",
        "clearance": True}


class Promo(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"SFB_STORE": str(self.tmp), "SFB_NO_COMMIT": "1"}); self.env.start()
        import crawler.store, crawler.process
        importlib.reload(crawler.store); importlib.reload(crawler.process)
        self.store, self.process = crawler.store, crawler.process

    def tearDown(self):
        self.env.stop(); shutil.rmtree(self.tmp)

    def build(self, item, prev=None):
        run = "run-x"
        self.store.write_json(self.tmp / "state" / "run.json", {"run_id": run, "plan": "core", "status": "crawled",
                              "departments": [{"id": "976759", "name": "Food", "status": "done"}]})
        self.store.write_jsonl_gz(self.tmp / "raw" / run / "976759" / "part-0001.jsonl.gz", [item])
        if prev is not None:
            self.store.write_jsonl_gz(self.tmp / "build" / "published" / "items.jsonl.gz", [prev])
        self.process.build()
        return {r["id"]: r for r in self.store.iter_jsonl_gz(self.tmp / "build" / "candidate" / "items.jsonl.gz")}[2]

    def test_first_publish_without_a_normal_price_shows_the_promo_flagged(self):
        r = self.build(ITEM)
        self.assertEqual(r["price"], 5.00); self.assertIn("promo_price", r["flags"]); self.assertNotIn("kept_normal_price", r["flags"])

    def test_the_normal_price_is_kept_through_a_promo_that_spans_several_crawls(self):
        normal = dict(self.build({**ITEM, "clearance": False, "salePrice": 7.48}))
        self.assertEqual(normal["price"], 7.48)
        first = dict(self.build(ITEM, prev=normal))                         # promo starts
        self.assertEqual((first["price"], first["promo"]), (7.48, 5.00)); self.assertIn("kept_normal_price", first["flags"])
        second = dict(self.build({**ITEM, "salePrice": 4.50}, prev=first))  # still on promo next crawl
        self.assertEqual((second["price"], second["promo"]), (7.48, 4.50)); self.assertIn("kept_normal_price", second["flags"])
        after = self.build({**ITEM, "clearance": False, "salePrice": 7.98}, prev=second)   # promo over
        self.assertEqual(after["price"], 7.98); self.assertNotIn("kept_normal_price", after["flags"])

    def test_a_promo_published_as_is_is_not_taken_for_a_normal_price(self):
        promo_only = dict(self.build(ITEM))                                 # first publish: promo price, flagged
        again = self.build({**ITEM, "salePrice": 4.50}, prev=promo_only)
        self.assertEqual(again["price"], 4.50); self.assertNotIn("kept_normal_price", again["flags"])


if __name__ == "__main__":
    unittest.main()
