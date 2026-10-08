"""process.build() drops per-unit prices that are more than 10x off their category+unit median, flags the rows,
and records the raw share for the unit_outliers gate (which measures that record, not the cleaned rows)."""
import importlib, json, os, shutil, tempfile, unittest
from pathlib import Path


def corn(i, size_oz, price):
    return {"itemId": 100000 + i, "upc": f"{78742054261 + i:012d}", "brandName": "Great Value", "salePrice": price,
            "name": f"Great Value Whole Kernel Sweet Corn, {size_oz} oz Can", "marketplace": False, "stock": "Available",
            "categoryPath": "Home Page/Food/Pantry/Canned goods/Canned vegetables/Canned corn"}


class Safeguard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SFB_STORE"] = self.tmp; os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.process, crawler.qa
        for m in (crawler.store, crawler.process, crawler.qa):
            importlib.reload(m)
        self.store, self.process, self.qa = crawler.store, crawler.process, crawler.qa
        root = Path(self.tmp)
        rows = [corn(i, 15.25, 0.87 + (i % 5) * 0.01) for i in range(60)]        # ~5.7 c/oz
        rows.append(corn(900, 0.25, 3.99))                                        # 1596 c/oz: a packet size read as the can
        self.store.write_jsonl_gz(root / "raw" / "run-1" / "976759" / "part-0001.jsonl.gz", rows)
        depts = [{"id": d["id"], "name": d["name"], "status": "done" if d["id"] == "976759" else "pending", "next": None,
                  "pages": 1 if d["id"] == "976759" else 0, "items": 0, "parts": 1, "total_pages": 1}
                 for d in self.store.config()["departments"]]
        self.store.write_json(root / "state" / "run.json", {"run_id": "run-1", "plan": "full", "status": "crawled",
                                                            "started": "2026-10-07T00:00:00+00:00", "updated": "2026-10-07T00:00:00+00:00",
                                                            "departments": depts, "calls": 1, "throttle_wait_s": 0})

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_outlier_unit_price_is_dropped_flagged_and_measured(self):
        stats = self.process.build()
        rows = {r["id"]: r for r in self.store.iter_jsonl_gz(Path(self.tmp) / "build" / "candidate" / "items.jsonl.gz")}
        bad = rows[100900]
        self.assertIsNone(bad["unit_price"]); self.assertIn("unit_price_suspect", bad["flags"])
        self.assertEqual(bad["price"], 3.99, "the item price itself is kept")
        self.assertTrue(all(r["unit_price"] for i, r in rows.items() if i != 100900))
        raw = stats["unit_outliers_raw"]
        self.assertEqual(raw["count"], 1); self.assertEqual(raw["unit_priced_rows"], 61)
        self.assertAlmostEqual(raw["share"], 1 / 61, places=4); self.assertEqual(raw["examples"][0]["id"], 100900)
        self.assertEqual(stats["flags"].get("unit_price_suspect"), 1)
        # the gate reads the raw record (the cleaned rows would always measure 0) and is measure-only by default
        gate, examples = self.qa.gate_unit_outliers(list(rows.values()), self.qa.gates_config(), stats)
        self.assertAlmostEqual(gate["value"], 1 / 61, places=4); self.assertIsNone(gate["threshold"]); self.assertTrue(gate["pass"])
        self.assertEqual(examples[0]["id"], 100900)
        strict, _ = self.qa.gate_unit_outliers(list(rows.values()), {**self.qa.gates_config(), "unit_outliers_max": 0.005}, stats)
        self.assertFalse(strict["pass"], "a threshold below the measured share holds")
        direct, _ = self.qa.gate_unit_outliers(list(rows.values()), self.qa.gates_config(), None)
        self.assertEqual(direct["value"], 0.0, "without the record the cleaned rows measure 0")

    def test_group_min_comes_from_gates_json(self):
        from unittest import mock
        with mock.patch.object(self.qa, "gates_config", lambda: {**self.qa.DEFAULTS, "unit_outlier_group_min": 1000}):
            stats = self.process.build()
        rows = {r["id"]: r for r in self.store.iter_jsonl_gz(Path(self.tmp) / "build" / "candidate" / "items.jsonl.gz")}
        self.assertIsNotNone(rows[100900]["unit_price"], "a 61-row group is below a 1000-row minimum: nothing is nulled")
        self.assertEqual(stats["unit_outliers_raw"]["count"], 0)



def item(i, name, price, path):
    return {"itemId": 200000 + i, "upc": f"{78742060000 + i:012d}", "brandName": "Brand", "salePrice": price, "name": name,
            "marketplace": False, "stock": "Available", "categoryPath": path}


class PackResolution(unittest.TestCase):
    """The parse keeps its default pack reading unless it is more than 10x off comparable items; then the reading the
    name also supports that agrees with them wins (flag pack_resolved). Comparable = most specific category path."""
    TARTS = "Home Page/Food/Breakfast & Cereal/Toaster Pastries"
    SPICES = "Home Page/Food/Pantry/Herbs, spices & seasoning mixes/Spices"
    FLOUR = "Home Page/Food/Pantry/Baking/Flour"

    def build(self, raw):
        tmp = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, tmp)
        os.environ["SFB_STORE"] = tmp; os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.process, crawler.qa
        for m in (crawler.store, crawler.process, crawler.qa):
            importlib.reload(m)
        store, process = crawler.store, crawler.process
        root = Path(tmp)
        store.write_jsonl_gz(root / "raw" / "run-1" / "976759" / "part-0001.jsonl.gz", raw)
        depts = [{"id": d["id"], "name": d["name"], "status": "done" if d["id"] == "976759" else "pending", "next": None,
                  "pages": 1 if d["id"] == "976759" else 0, "items": 0, "parts": 1, "total_pages": 1} for d in store.config()["departments"]]
        store.write_json(root / "state" / "run.json", {"run_id": "run-1", "plan": "full", "status": "crawled", "started": "x",
                                                       "updated": "x", "departments": depts, "calls": 1, "throttle_wait_s": 0})
        stats = process.build()
        return {r["id"]: r for r in store.iter_jsonl_gz(root / "build" / "candidate" / "items.jsonl.gz")}, stats

    def test_total_weight_beside_a_piece_count_is_one_box(self):
        raw = [item(i, f"Toaster Pastries, {20 + i % 5} oz Box", 3.0 + (i % 5) * 0.1, self.TARTS) for i in range(60)]
        raw += [item(i + 100, f"Toaster Pastries Single, {3 + (i % 3)} oz", 0.6, self.TARTS) for i in range(10)]
        raw.append(item(900, "Pop-Tarts Frosted Strawberry, 58.6 oz, 32 Count", 10.94, self.TARTS))
        rows, stats = self.build(raw)
        r = rows[200900]
        self.assertEqual(r["pack"], 1, "58.6 oz is the whole box, not 32 boxes"); self.assertIn("pack_resolved", r["flags"])
        self.assertAlmostEqual(r["unit_price"], round(10.94 / 58.6, 4)); self.assertNotIn("unit_price_suspect", r["flags"])
        self.assertNotIn("pack_options", r, "the candidates never reach the snapshot")
        self.assertGreaterEqual(stats["unit_outliers_raw"]["pack_resolved"], 1)

    def test_containers_beside_a_size_multiply_it(self):
        beans = "Home Page/Food/Pantry/Canned goods/Canned beans"
        raw = [item(i, f"Baked Beans, {15 + i % 3} oz Can", 1.5 + (i % 4) * 0.1, beans) for i in range(60)]
        raw.append(item(901, "(12 Cans) Bush's Original Baked Beans, Canned Beans, 16 oz", 20.38, beans))
        raw.append(item(902, "Famous Amos Cookies, 2 oz Snack Pack, 36/Carton", 30.22, beans))
        rows, _ = self.build(raw)
        self.assertEqual(rows[200901]["pack"], 12); self.assertIn("pack_resolved", rows[200901]["flags"])
        self.assertEqual(rows[200902]["pack"], 36)
        self.assertEqual(rows[200000]["pack"], 1); self.assertNotIn("pack_resolved", rows[200000]["flags"], "in-band rows keep their reading")

    def test_comparable_items_are_the_category_path_not_the_whole_category(self):
        # spices at ~$4/oz and flour at ~$0.04/oz share a snapshot category; each is judged against its own path
        raw = [item(i, f"Ground Spice {i}, 1.{i % 9 + 1} oz", 4.5 + (i % 7) * 0.2, self.SPICES) for i in range(60)]
        raw += [item(i + 100, f"All Purpose Flour {i}, 5 lb", 2.5 + (i % 5) * 0.2, self.FLOUR) for i in range(60)]
        rows, stats = self.build(raw)
        self.assertEqual(stats["unit_outliers_raw"]["count"], 0)
        self.assertFalse(any("unit_price_suspect" in r["flags"] for r in rows.values()))

    def test_a_pack_count_cut_off_the_name_is_recovered_from_comparable_items(self):
        beans = "Home Page/Food/Pantry/Canned goods/Canned beans"
        raw = [item(i, f"Baked Beans, {15 + i % 3} oz Can", 1.5 + (i % 4) * 0.1, beans) for i in range(60)]
        raw.append(item(903, "Bush's Baked Beans, 16 Oz (pack Of", 21.48, beans))     # a case of 12 at $1.79
        rows, _ = self.build(raw)
        self.assertEqual(rows[200903]["pack"], 12)
        self.assertIn("pack_truncated", rows[200903]["flags"]); self.assertIn("pack_resolved", rows[200903]["flags"])
        self.assertNotIn("unit_price_suspect", rows[200903]["flags"])

    def test_a_reading_nothing_supports_stays_flagged(self):
        beans = "Home Page/Food/Pantry/Canned goods/Canned beans"
        raw = [item(i, f"Baked Beans, {15 + i % 3} oz Can", 1.5 + (i % 4) * 0.1, beans) for i in range(60)]
        raw.append(item(904, "Baked Beans Deluxe, 16 oz Can", 60.0, beans))            # no pack anywhere: still flagged
        rows, _ = self.build(raw)
        self.assertIn("unit_price_suspect", rows[200904]["flags"])
        self.assertNotIn("pack_resolved", rows[200904]["flags"])


if __name__ == "__main__":
    unittest.main()


def upc(body11):
    """A 12-digit UPC-A with a valid check digit."""
    d = [int(c) for c in f"{body11:011d}"]
    return f"{body11:011d}{(10 - (3 * sum(d[0::2]) + sum(d[1::2])) % 10) % 10}"


class PlaceholderNames(unittest.TestCase):
    """Barcode-only listings get a real name: another Walmart listing with the same UPC, else Open Facts, else
    "(name not provided)" after the brand; the feed's text stays in listed_name."""

    def test_names_come_from_a_listing_with_the_same_upc_then_open_facts(self):
        beans = "Home Page/Food/Pantry/Canned goods/Canned beans"
        same, facts, none = upc(7874206101), upc(7874206102), upc(7874206103)
        raw = [item(i, f"Baked Beans, {15 + i % 3} oz Can", 1.5, beans) for i in range(10)]
        raw.append(dict(item(901, "Merchandise", 1.8, beans), upc=same, brandName="Bush's"))
        raw.append(dict(item(902, "Bush's Best Original Baked Beans, 16 oz", 1.8, beans), upc=same, brandName="Bush's"))
        raw.append(dict(item(903, "coming soon", 2.5, beans), upc=facts, brandName="Unbranded"))
        raw.append(dict(item(904, "PROGRESSO", 2.08, beans), upc=none, brandName="Progresso"))
        import crawler.store
        tmp = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, tmp)
        os.environ["SFB_STORE"] = tmp
        importlib.reload(crawler.store)
        key = "00" + facts
        crawler.store.write_jsonl_gz(Path(tmp) / "identify" / "products_us.jsonl.gz",
                                     [{"upc": key, "name": "Organic Black Beans", "brand": "Simple Truth", "quantity": "15 oz"}])
        rows, stats = self.build_in(tmp, raw)
        a, b, c = rows[200901], rows[200903], rows[200904]
        self.assertEqual((a["name"], a["name_src"], a["listed_name"]), ("Bush's Best Original Baked Beans, 16 oz", "walmart_listing", "Merchandise"))
        self.assertEqual((b["name"], b["brand"], b["name_src"], b["size"], b["unit"]), ("Organic Black Beans", "Simple Truth", "open_facts", 15.0, "oz"))
        self.assertEqual((c["name"], c["brand"], c["name_src"]), ("(name not provided)", "Progresso", "none"))
        for r in (a, b, c):
            self.assertIn("placeholder", r["flags"], "still barcode-only"); self.assertIsNone(r["unit_price"])
        self.assertEqual(stats["placeholders"]["names_filled"], {"walmart_listing": 1, "open_facts": 1, "none": 1})

    def test_a_brand_that_only_repeats_the_placeholder_is_dropped(self):
        from crawler import process
        rows = {1: {"id": 1, "upc": "1", "name": "Merchandise", "brand": "ONLINE", "flags": ["placeholder"]},
                2: {"id": 2, "upc": "2", "name": "Merchandise", "brand": "Merchandise", "flags": ["placeholder"]},
                3: {"id": 3, "upc": "3", "name": "Merchandise", "brand": "Hello Bello", "flags": ["placeholder"]},
                4: {"id": 4, "upc": "3", "name": "(4 pack) Hello Bello Diapers", "brand": "Hello Bello", "flags": []},
                5: {"id": 5, "upc": "3", "name": "Hello Bello Diapers Size 3, 32 ct", "brand": "Hello Bello", "flags": []}}
        process.fill_placeholder_names(rows)
        self.assertEqual([rows[i]["brand"] for i in (1, 2)], [None, None])
        self.assertEqual(rows[3]["name"], "Hello Bello Diapers Size 3, 32 ct", "the plain listing beats the multipack")

    def build_in(self, tmp, raw):
        os.environ["SFB_STORE"] = tmp; os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.process, crawler.qa
        for m in (crawler.store, crawler.process, crawler.qa):
            importlib.reload(m)
        store, process = crawler.store, crawler.process
        root = Path(tmp)
        store.write_jsonl_gz(root / "raw" / "run-1" / "976759" / "part-0001.jsonl.gz", raw)
        depts = [{"id": d["id"], "name": d["name"], "status": "done" if d["id"] == "976759" else "pending", "next": None,
                  "pages": 1 if d["id"] == "976759" else 0, "items": 0, "parts": 1, "total_pages": 1} for d in store.config()["departments"]]
        store.write_json(root / "state" / "run.json", {"run_id": "run-1", "plan": "full", "status": "crawled", "started": "x",
                                                       "updated": "x", "departments": depts, "calls": 1, "throttle_wait_s": 0})
        stats = process.build()
        return {r["id"]: r for r in store.iter_jsonl_gz(root / "build" / "candidate" / "items.jsonl.gz")}, stats
