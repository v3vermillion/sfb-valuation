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


NOW_ = __import__("datetime").datetime(2026, 10, 12, 12, 0, tzinfo=__import__("datetime").timezone.utc)
CFG = {"store_id": "2266", "name": "Strongsville Supercenter", "refresh_every_days": 7, "max_age_days": 21}


def row(i, dept="Food", price=2.0, **kw):
    return {"id": i, "upc": f"{i:012d}", "name": f"Item {i}", "dept": dept, "price": price, "unit_price": price / 10,
            "flags": [], "primary": True, **kw}


class StoreWM:
    """/items with storeId: the store charges 1.50 for even ids; id 13 is no longer listed."""

    def __init__(self, throttle_after=None):
        self.paths = []; self.throttle_after = throttle_after

    def get(self, path):
        from crawler.wm import Throttled
        self.paths.append(path)
        if self.throttle_after is not None and len(self.paths) > self.throttle_after:
            raise Throttled("429")
        assert "storeId=2266" in path, path
        ids = [int(x) for x in path.split("ids=")[1].split("&")[0].split(",")]
        return {"items": [{"itemId": i, "salePrice": 1.5 if i % 2 == 0 else 2.0, "stock": "Available"} for i in ids if i != 13]}


class Refresh(unittest.TestCase):
    def setUp(self):
        Probe.setUp(self)
        p = mock.patch.object(self.sp, "config", lambda: dict(CFG)); p.start(); self.addCleanup(p.stop)
        p = mock.patch.object(self.sp, "_consumable_depts", lambda: {"Food"}); p.start(); self.addCleanup(p.stop)
        rows = [row(i, dept="Toys" if i < 5 else "Food") for i in range(1, 51)]
        rows += [row(100, flags=["placeholder"]), row(101, primary=False), row(102, upc=None)]
        self.store.write_jsonl_gz(self.tmp / "build" / "published" / "items.jsonl.gz", rows)

    def tearDown(self):
        Probe.tearDown(self)

    def test_refresh_prices_every_barcode_row_consumables_first_and_records_what_is_gone(self):
        wm = StoreWM()
        res = self.sp.refresh(wm, 60, now=NOW_)
        self.assertEqual((res["due"], res["checked"], res["gone"], res["remaining"], res["calls"]), (50, 50, 1, 0, 3))
        first = [int(x) for x in wm.paths[0].split("ids=")[1].split("&")[0].split(",")]
        self.assertTrue(all(i >= 5 for i in first), "Food (consumable) rows go first")
        recs = self.sp.load("2266")
        self.assertEqual(set(recs), set(range(1, 51)))
        self.assertEqual(recs[2], {"id": 2, "p": 1.5, "s": "Available", "t": "2026-10-12"})
        self.assertTrue(recs[13]["g"])
        latest = self.store.read_json(self.tmp / "store_prices" / "latest.json")
        self.assertEqual((latest["due"], latest["next_due"]), (0, "2026-10-19"))
        self.assertFalse(self.sp.due(latest, NOW_))
        self.assertTrue(self.sp.due(latest, NOW_ + __import__("datetime").timedelta(days=7)))
        self.assertTrue(self.sp.due(None, NOW_))
        # a second pass the same week has nothing to do
        wm2 = StoreWM()
        self.assertEqual(self.sp.refresh(wm2, 60, now=NOW_)["due"], 0); self.assertEqual(wm2.paths, [])

    def test_a_throttled_refresh_keeps_what_it_got(self):
        from crawler.wm import Throttled
        with self.assertRaises(Throttled):
            self.sp.refresh(StoreWM(throttle_after=1), 60, now=NOW_)
        self.assertEqual(len(self.sp.load("2266")), 20)
        self.assertEqual(self.store.read_json(self.tmp / "store_prices" / "latest.json")["due"], 30)

    def test_apply_shows_fresh_store_prices_and_reverts_stale_ones(self):
        self.sp.refresh(StoreWM(), 60, now=NOW_)
        rows = {r["id"]: r for r in [row(2, price=2.5), row(3, price=2.0), row(13), row(60),
                                     row(4, price=3.0, flags=["promo_price", "kept_normal_price"], promo=2.0)]}
        n = self.sp.apply(rows, now=NOW_)
        self.assertEqual(n, 3)
        r2 = rows[2]
        self.assertEqual((r2["price"], r2["online_price"], r2["store_checked"], r2["store_stock"]), (1.5, 2.5, "2026-10-12", "Available"))
        self.assertIn("store_price", r2["flags"]); self.assertAlmostEqual(r2["unit_price"], 0.25 * 1.5 / 2.5)
        self.assertEqual(rows[3]["price"], 2.0)                                # same price, still labelled the store's
        self.assertNotIn("store_price", rows[13]["flags"]); self.assertNotIn("store_price", rows[60]["flags"])
        self.assertEqual(rows[4]["price"], 1.5); self.assertNotIn("promo", rows[4])
        self.assertEqual([f for f in rows[4]["flags"] if f != "store_price"], [])
        # applied again (a carried-over row) it starts from Walmart.com's price, not the store's
        self.sp.apply(rows, now=NOW_)
        self.assertEqual((rows[2]["price"], rows[2]["online_price"]), (1.5, 2.5))
        # 22 days later the store price is too old: Walmart.com's price again, no store label
        self.assertEqual(self.sp.apply(rows, now=NOW_ + __import__("datetime").timedelta(days=22)), 0)
        self.assertEqual(rows[2]["price"], 2.5); self.assertNotIn("online_price", rows[2])
        self.assertNotIn("store_price", rows[2]["flags"]); self.assertAlmostEqual(rows[2]["unit_price"], 0.25)

    def test_without_a_store_nothing_is_due_or_applied(self):
        with mock.patch.object(self.sp, "config", lambda: None):
            self.assertFalse(self.sp.due(None, NOW_))
            self.assertEqual(self.sp.refresh(StoreWM(), 60, now=NOW_)["status"], "skipped")
            self.assertEqual(self.sp.apply({1: row(1)}, now=NOW_), 0)


class LiveCheck(unittest.TestCase):
    def test_store_priced_rows_are_checked_against_the_store(self):
        import crawler.qa as qa
        calls = []

        class WM:
            def get_items(self, ids, store_id=None):
                calls.append((tuple(ids), store_id))
                return [{"itemId": int(i), "salePrice": 1.5 if store_id else 2.5} for i in ids]
        sample = [row(1, price=2.5), {**row(2, price=1.5), "flags": ["store_price"]}]
        with mock.patch("crawler.storeprice.config", lambda: dict(CFG)):
            res = qa.live_check(WM(), sample)
        self.assertEqual(res["exact"], 2)
        self.assertEqual(calls, [(("1",), None), (("2",), "2266")])
