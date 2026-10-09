"""crawler/storeprice.py probe: read-only comparison of location-less, zipCode and storeId answers."""
import importlib, os, shutil, tempfile, unittest
from pathlib import Path
from unittest import mock


class FakeWM:
    def __init__(self):
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        if path.startswith("/stores"):
            return [{"no": 2266, "name": "Strongsville Supercenter", "city": "Strongsville", "zip": "44136"}]
        store = "storeId=2266" in path
        if path.startswith("/items"):
            ids = [int(i) for i in path.split("ids=")[1].split("&")[0].split(",")]
            return {"items": [{"itemId": i, "name": f"Item {i}", "salePrice": 2.0 if store and i % 2 else 1.0,
                               "stock": "Available" if store else "Not available"} for i in ids]}
        if path.startswith("/paginated"):
            if store:
                raise RuntimeError("HTTP 400 for paginated with storeId")
            return {"items": [{"itemId": 1, "salePrice": 1.0}], "totalPages": 3}
        raise AssertionError(path)


class Probe(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"SFB_STORE": str(self.tmp)}); self.env.start()
        import crawler.store, crawler.storeprice
        importlib.reload(crawler.store); importlib.reload(crawler.storeprice)
        self.store, self.sp = crawler.store, crawler.storeprice

    def tearDown(self):
        self.env.stop(); shutil.rmtree(self.tmp)

    def test_probe_finds_the_store_and_reports_differences(self):
        part = self.tmp / "p.jsonl.gz"
        self.store.write_jsonl_gz(part, [{"itemId": i, "stock": "Not available" if i < 50 else "Available"} for i in range(100)])
        wm = FakeWM()
        r = self.sp.probe(wm, "44136", None, part)
        self.assertEqual(r["store_id"], "2266"); self.assertEqual(r["sample"], 20)
        c = r["items"]["storeId"]["vs_plain"]
        self.assertEqual(c["items_both"], 20); self.assertEqual(c["differ"]["stock"], 20)
        self.assertGreater(c["differ"]["salePrice"], 0)
        self.assertEqual(r["items"]["zipCode"]["vs_plain"]["differ"]["salePrice"], 0)
        self.assertIn("HTTP 400", r["paginated"]["error"])
        md = self.sp.markdown(r)
        self.assertIn("#2266 Strongsville Supercenter", md); self.assertIn("/paginated` with storeId: RuntimeError", md)
        self.assertLessEqual(len(wm.paths), 6)

    def test_probe_without_a_sample_still_checks_stores_and_pages(self):
        r = self.sp.probe(FakeWM(), "44136", "2266", None)
        self.assertEqual(r["sample"], 0); self.assertNotIn("items", r); self.assertIn("paginated", r)


if __name__ == "__main__":
    unittest.main()
