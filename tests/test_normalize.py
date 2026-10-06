import json, unittest
from pathlib import Path
from crawler import normalize as N

CFG = json.loads((Path(__file__).resolve().parent.parent / "data" / "categories.json").read_text())
FOOD = next(d for d in CFG["departments"] if d["name"] == "Food")


class T(unittest.TestCase):
    def q(self, s): return N.parse_quantity(s)

    def test_quantities(self):
        self.assertEqual(self.q("Great Value Whole Kernel Sweet Corn, Gluten-Free, 29 oz Can"), (29.0, "oz", None))
        self.assertEqual(self.q("(8 pack) Great Value Golden Sweet Whole Kernel Corn, 15.25 oz"), (15.25, "oz", 8))
        self.assertEqual(self.q("Mountain Dew Soda Pop, 16.9 fl oz, 24 Pack Bottles"), (16.9, "fl oz", 24))
        self.assertEqual(self.q("Mt. Olive PicklePak Kosher Dill Petites Pickles, 4 - 3.7 fl oz Cups"), (3.7, "fl oz", 4))
        self.assertEqual(self.q("Don Pancho Whole Wheat Large Wraps, 17 oz, 8 Count"), (17.0, "oz", 8))
        self.assertEqual(self.q("Fresh Express Crunchy Blends Veggie Lover's Salad, 11 oz"), (11.0, "oz", None))
        self.assertEqual(self.q("Mt. Olive Fresh Pack Whole Kosher Dills Pickles, 128 fl oz Jar"), (128.0, "fl oz", None))
        self.assertEqual(self.q("Equate Ibuprofen Tablets, 200 mg, 100 Count"), (100.0, "ct", None))
        self.assertEqual(self.q("Coca-Cola Soda, 12 x 12 fl oz Cans"), (12.0, "fl oz", 12))
        self.assertEqual(self.q("Lawry's Teriyaki Marinade - 12 fl oz"), (12.0, "fl oz", None))
        self.assertEqual(self.q("Dan-O's Original Seasoning - 3.5oz"), (3.5, "oz", None))
        self.assertEqual(self.q("Bananas, each"), (None, None, None))

    def test_gtin(self):
        self.assertEqual(N.gtin14("078742054261")[0], "00078742054261")
        self.assertTrue(N.gtin14("078742054261")[2])
        key, retired, _ = N.gtin14("deleted_071279261027")
        self.assertTrue(retired); self.assertEqual(key, "00071279261027")
        self.assertEqual(N.gtin14("07874205426")[0], "00078742054261")  # 11 digits -> check digit added

    def test_junk(self):
        book = {"name": "Vinegars of the World, (Paperback)", "brandName": "Laura Solieri", "salePrice": 127.93, "categoryPath": "Home Page/Food/Pantry"}
        self.assertEqual(N.junk_reason(book, "Food", CFG), "media_misfiled")
        cd = {"name": "Soul Sauce", "brandName": "UMGD", "salePrice": 34.47, "upc": "731452166821", "categoryPath": "Home Page/Food/Pantry"}
        self.assertEqual(N.junk_reason(cd, "Food", CFG), "media_misfiled")
        authors = {"name": "Salad Dressings", "brandName": "Jessica Strand; Maren Caruso", "salePrice": 13.68, "categoryPath": "x"}
        self.assertEqual(N.junk_reason(authors, "Food", CFG), "media_misfiled")
        third = {"name": "Whole Kernel Corn 15 oz", "sellerInfo": "Hayam Store", "salePrice": 10.99}
        self.assertEqual(N.junk_reason(third, "Food", CFG), "third_party_seller")
        beer = {"name": "Bud Light 12 pk", "salePrice": 12.0, "categoryPath": "Home Page/Food/Alcohol/Beer"}
        self.assertEqual(N.junk_reason(beer, "Food", CFG), "excluded_category")
        ok = {"name": "Great Value Whole Kernel Sweet Corn, 29 oz Can", "brandName": "Great Value", "salePrice": 1.22, "upc": "078742054261", "sellerInfo": "Walmart.com"}
        self.assertIsNone(N.junk_reason(ok, "Food", CFG))

    def test_row(self):
        item = {"itemId": 1, "name": "(8 pack) Great Value Golden Sweet Whole Kernel Corn, 15.25 oz", "brandName": "Great Value",
                "size": "15 oz", "salePrice": 4.0, "upc": "464583029559", "categoryPath": "Home Page/Food/Pantry/Canned goods/Canned vegetables/Canned corn"}
        row, why = N.normalize(item, FOOD, CFG)
        self.assertIsNone(why)
        self.assertEqual((row["size"], row["unit"], row["pack"], row["cat"]), (15.25, "oz", 8, "6"))
        self.assertAlmostEqual(row["unit_price"], 4.0 / (15.25 * 8), places=4)
        self.assertTrue(row["store_brand"])
        row2, _ = N.normalize({"itemId": 2, "name": "Diet Mountain Dew Soda, 12 fl oz, 12 Pack Cans", "salePrice": 6.48,
                               "categoryPath": "Home Page/Food/Beverages/Soda"}, FOOD, CFG)
        self.assertIn("diet", row2["variants"]); self.assertEqual(row2["cat"], "10"); self.assertEqual(row2["pack"], 12)
        row3, _ = N.normalize({"itemId": 3, "name": "Marketside Bistro Blend Salad, 10 oz", "size": "23 oz", "salePrice": 4.17,
                               "categoryPath": "Home Page/Food/Fresh Produce/Packaged Salads"}, FOOD, CFG)
        self.assertEqual(row3["size"], 10.0); self.assertIn("size_conflict", row3["flags"])


if __name__ == "__main__":
    unittest.main()
