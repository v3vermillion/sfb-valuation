"""crawler/valuation.py: implausible prices are withheld and valued at an equivalent; never blank."""
import unittest

from crawler import valuation as V

CFG = {"price_sanity": {"floor": 0.10, "over_p99": 5, "caps": {"Food": 500, "default": 5000}}}


def row(i, name, price, cat="6", dept="Food", qty=None, unit=None, pack=1, flags=None, brand="Great Value", path=None):
    up = round(price / (qty * pack), 4) if qty else None
    return {"id": i, "upc": f"{i:014d}", "name": name, "brand": brand, "price": price, "cat": cat, "dept": dept,
            "base_qty": qty, "base_unit": unit, "pack": pack, "unit_price": up, "flags": list(flags or []),
            "path": path or "Home Page/Food/Pantry/Canned goods/Canned corn"}


def snapshot(extra):
    rows = {i: row(i, f"Great Value Whole Kernel Corn {i}", 1.0 + (i % 7) * 0.1, qty=15.25, unit="oz") for i in range(1, 400)}
    for r in extra:
        rows[r["id"]] = r
    return rows


class Bounds(unittest.TestCase):
    def test_range_is_the_cap_or_a_multiple_of_the_99th_percentile(self):
        rows = [row(i, "x", float(i)) for i in range(1, 101)]          # p99 = 100
        lo, hi, p99 = V.bounds(rows, CFG)["Food"]
        self.assertEqual((lo, hi, p99), (0.10, 500, 100))               # 5 x 100 = 500, the Food cap
        rows = [row(i, "x", i / 10) for i in range(1, 101)]            # p99 = 10
        self.assertEqual(V.bounds(rows, CFG)["Food"][1], 50)

    def test_placeholders_do_not_shape_the_range(self):
        rows = [row(i, "x", 1.0) for i in range(1, 100)] + [row(999, "Merchandise", 9000.0, flags=["placeholder"])]
        self.assertEqual(V.bounds(rows, CFG)["Food"][1], 5.0)


class Apply(unittest.TestCase):
    def test_an_absurd_price_is_withheld_and_valued_at_the_closest_comparable(self):
        rows = snapshot([row(1000, "Great Value Whole Kernel Corn 3", 3.26e21, qty=15.25, unit="oz")])
        withheld, bounds, dropped = V.apply(rows, CFG)
        r = rows[1000]
        self.assertTrue(r["price_withheld"]); self.assertIn("price_withheld", r["flags"])
        self.assertEqual(r["price"], 3.26e21, "Walmart's price is kept as listed for history and audits")
        self.assertIsNone(r["unit_price"])
        self.assertEqual(r["equiv"]["method"], "comparable item")
        self.assertTrue(1.0 <= r["equiv"]["price"] <= 1.7)
        self.assertEqual([w["id"] for w in withheld], [1000]); self.assertEqual(withheld[0]["raw_price"], 3.26e21)
        self.assertEqual(dropped, [])

    def test_a_one_cent_listing_is_withheld_too(self):
        rows = snapshot([row(1001, "Great Value Whole Kernel Corn 4", 0.01, qty=15.25, unit="oz")])
        V.apply(rows, CFG)
        self.assertTrue(rows[1001]["price_withheld"])
        self.assertGreater(rows[1001]["equiv"]["price"], 0.10)

    def test_without_a_comparable_the_per_unit_median_then_the_category_median(self):
        odd = row(1002, "Zqxv Unusual Imported Thing", 99999.0, qty=30.5, unit="oz", brand="Zqxv")
        rows = snapshot([odd])
        V.apply(rows, CFG, group_min=50)
        self.assertEqual(rows[1002]["equiv"]["method"], "median per-unit price of comparable items")
        self.assertAlmostEqual(rows[1002]["equiv"]["price"], round(1.3 / 15.25 * 30.5, 2), delta=0.5)
        nosize = row(1003, "Zqxv Unusual Imported Thing", 99999.0, brand="Zqxv")
        rows = snapshot([nosize])
        V.apply(rows, CFG)
        self.assertEqual(rows[1003]["equiv"]["method"], "median price of its category")
        self.assertEqual(rows[1003]["equiv"]["confidence"], "rough")
        self.assertGreater(rows[1003]["equiv"]["price"], 0)

    def test_a_placeholder_with_an_implausible_price_is_dropped(self):
        rows = snapshot([row(1004, "Merchandise", 7009.32, flags=["placeholder"])])
        withheld, _, dropped = V.apply(rows, CFG)
        self.assertNotIn(1004, rows)
        self.assertEqual(dropped, [(1004, "Food")]); self.assertEqual(withheld, [])

    def test_a_register_name_priced_like_a_pallet_is_dropped(self):
        rows = snapshot([row(1005, "Old El Paso Bold/Pri", 1042.0), row(1006, "ReadyWise 2160 Serving Emergency Food Bucket", 4599.99)])
        withheld, _, dropped = V.apply(rows, CFG)
        self.assertEqual(dropped, [(1005, "Food")])
        self.assertEqual([w["id"] for w in withheld], [1006], "a full product name is withheld and valued, not dropped")

    def test_plausible_prices_are_untouched(self):
        rows = snapshot([])
        before = {i: dict(r) for i, r in rows.items()}
        withheld, _, _ = V.apply(rows, CFG)
        self.assertEqual(withheld, []); self.assertEqual(rows, before)


if __name__ == "__main__":
    unittest.main()
