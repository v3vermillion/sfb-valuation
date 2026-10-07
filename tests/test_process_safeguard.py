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


if __name__ == "__main__":
    unittest.main()
