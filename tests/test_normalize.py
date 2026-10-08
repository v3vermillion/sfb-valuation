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

    def test_count_beside_a_pack(self):
        # the count survives a stated pack; a stated total is never multiplied again
        self.assertEqual(self.q("(5 pack) (5 Pack) Miracle Tree Tea Organic Moringa, 16 Count"), (16.0, "ct", 5))
        self.assertEqual(self.q("Lipton Decaf Tea Bags Family Size, 24 ct (Pack of 6)"), (24.0, "ct", 6))
        self.assertEqual(self.q("Senseo Decaf Coffee Pods, 108 Count (6 Packs of 18 Pods)"), (108.0, "ct", None))
        self.assertEqual(self.q("Trident Gum, 9 Packs of 16 Pieces (144 Total Pieces)"), (144.0, "ct", None))
        self.assertEqual(self.q("GUM Soft-Picks, 90 Count (Pack of 3) 270 Total"), (90.0, "ct", 3))
        self.assertEqual(self.q("(6 pack) Equate Wipes, 40 Total Wipes"), (40.0, "ct", 6), "under a (6 pack) wrapper the total is per unit")
        self.assertEqual(self.q("Equate Tampons (20 Count)"), (20.0, "ct", None), "(20 Count) is not a pack of 20 as well")
        self.assertEqual(self.q("Colgate 360 Total Advanced Toothbrush - 2 Count"), (2.0, "ct", None))
        self.assertEqual(self.q("(0 pack) (12 Pack) Kedem Juice Grape, 22 Fz"), (22.0, "fl oz", 12), "(0 pack) is ignored")
        # the basic pass keeps the long-standing reading so a size field's weight still wins over "(12 Count)"
        self.assertEqual(N.parse_quantity("Powerful Greek Yogurt Protein Drink (12 Count)", extended=False), (None, None, 12))

    def test_count_nouns_dozen_and_word_numbers(self):
        self.assertEqual(self.q("Celestial Seasonings Peppermint, 20 Tea Bags"), (20.0, "ct", None))
        self.assertEqual(self.q("CLIF BAR Peanut Butter Banana, 12 Bars"), (12.0, "ct", None))
        self.assertEqual(self.q("Brooklyn Bean Breakfast Blend, 40 K-Cup Pods"), (40.0, "ct", None))
        self.assertEqual(self.q("Sunbeam Coffee Filters, 100 Each"), (100.0, "ct", None))
        self.assertEqual(self.q("Red Roses with Premium Greens, Two Dozen"), (24.0, "ct", None))
        self.assertEqual(self.q("Two Pounds Of Fresh Raw Walnuts"), (2.0, "lb", None))
        self.assertEqual(self.q("Fieldpack Fresh Stem Strawberries 1#"), (1.0, "lb", None))
        self.assertEqual(self.q("Covermark SPF 15 # 50 Beige, 1 oz"), (1.0, "oz", None), "a shade number is not pounds")
        self.assertEqual(self.q("Oakhurst Pumpkin Spice Eggnog, Quart"), (1.0, "qt", None))
        self.assertEqual(self.q("Swiss Premium Orange Blast Drink - 1 Half Gallon Jug"), (0.5, "gal", None))
        self.assertEqual(self.q("Bud Light Gift Bucket with Two Pint Glasses, 5.5 oz"), (5.5, "oz", None))
        self.assertEqual(N.parse_quantity("Celestial Seasonings Peppermint, 20 Tea Bags", extended=False), (None, None, None),
                         "count nouns are read only when no weight or volume is stated anywhere")

    def test_unit_abbreviations_fractions_and_shorthands(self):
        self.assertEqual(self.q("Kedem Juice Grape, 22 Fz"), (22.0, "fl oz", None))
        self.assertEqual(self.q("Gel Shwr White Tea, 16.9 Fo (pack Of 1)"), (16.9, "fl oz", 1))
        self.assertEqual(self.q("Orion Choco Chip Cookie, 104 Gm"), (104.0, "g", None))
        self.assertEqual(self.q("Pom Peach Passion White Tea 1.5lt"), (1.5, "l", None))
        self.assertEqual(self.q("Naturtint 7GM Chocolate Caramel Hair Color"), (None, None, None), "7GM is a shade")
        self.assertEqual(self.q("MISS CLAIROL 46 LT COOL"), (None, None, None), "46 LT is a shade")
        self.assertEqual(self.q("Stay Hard 1 1/2oz"), (1.5, "oz", None))
        self.assertEqual(self.q("Wilton Icing Tube, 4-1/4 ounces"), (4.25, "oz", None))
        self.assertEqual(self.q("RICA PEAR NECTAR 1/2 LT 500ml 18/1"), (0.5, "l", None))
        self.assertEqual(self.q("Orajel Kids Toothpaste 24/2oz"), (2.0, "oz", None), "N/size keeps the long-standing reading")
        self.assertEqual(self.q("Betty Crocker Complete Meals | 24. OZ"), (24.0, "oz", None))
        self.assertEqual(self.q("Sechler's Jalapeno Sweet Relish, 16 Fl O"), (16.0, "fl oz", None))
        self.assertEqual(self.q("Raisin Bran Rb 28.2ozx14 Bns Pk"), (28.2, "oz", None), "x14 is the supplier case; Walmart prices one box")
        self.assertEqual(self.q("LorAnn Oils Flavoring | 1 Fl Dram"), (0.125, "fl oz", None))
        self.assertEqual(self.q("11.5z Mh Dark Roast Can"), (11.5, "oz", None))
        self.assertEqual(N.parse_quantity("11.5z Mh Dark Roast Can", extended=False), (None, None, None))
        self.assertEqual(self.q("Nissan 350z by Nissan for Men"), (None, None, None))

    def test_sold_each_counts_as_sized_by_basis(self):
        def row(name, path, size=None):
            r, _ = N.normalize({"itemId": 9, "name": name, "salePrice": 1.0, "size": size, "upc": "078742054261", "categoryPath": path}, FOOD, CFG)
            return r
        for name, path, size in [("Red Grapefruit, each", "Home Page/Food/Fresh Produce/Fresh Fruit", None),
                                 ("Hass Avocado", "Home Page/Food/Fresh Produce/Fresh Fruit/Avocados", None),
                                 ("Louisiana Grills Sweet Heat Rub", "Home Page/Food/Pantry", "EA"),
                                 ("1/4 Marble Sheet Cake with Batman Kit", "Home Page/Food/Bakery & Bread/Cakes/Shop all cakes", None),
                                 ("Nostalgic Gift Basket", "Home Page/Food/Food Gifts/All Food Gifts", None),
                                 ("Polka Dot Number 7 Birthday Candle", "Home Page/Food/Baking/Baking Ingredients/Frosting, Toppings & Decorations", None),
                                 ("Farm Direct Bouquet of 12 Roses", "Home Page/Food/Flower Shop/All Flowers", None)]:
            r = row(name, path, size)
            self.assertIn("sold_each", r["flags"], name); self.assertIsNone(r["size"]); self.assertIsNone(r["unit_price"])
        for name, path in [("Louisiana Hot Sauce", "Home Page/Food/Pantry/Pantry meal essentials"),
                           ("Wilton Easter Clr Egg Sprinkl Mix", "Home Page/Food/Baking/Baking Ingredients/Frosting, Toppings & Decorations"),
                           ("Merchandise", "Home Page/Food/Pantry/Pantry meal essentials")]:
            self.assertNotIn("sold_each", row(name, path)["flags"], f"{name}: a packaged good with a missing size is a failure")

    def test_stated_weight_beats_a_piece_count(self):
        r, _ = N.normalize({"itemId": 5, "name": "Powerful Coconut Greek Yogurt Protein Drink (12 Count)", "size": "12 oz",
                            "salePrice": 24.0, "categoryPath": "Home Page/Food/Dairy"}, FOOD, CFG)
        self.assertEqual((r["size"], r["unit"], r["pack"]), (12.0, "oz", 12))
        r, _ = N.normalize({"itemId": 6, "name": "Haagen Dazs Chocolate Pint", "size": "14 fl oz", "salePrice": 5.0,
                            "categoryPath": "Home Page/Food/Frozen"}, FOOD, CFG)
        self.assertEqual((r["size"], r["unit"]), (14.0, "fl oz"), "the stated 14 fl oz beats the word Pint")

    def test_nutrient_grams_are_not_the_size(self):
        self.assertEqual(self.q("Ratio Granola Cereal, 18g Protein, 9.8 oz"), (9.8, "oz", None))
        self.assertEqual(self.q("Nalley Chili, 19g Protein Per Serving, 14 oz. Can"), (14.0, "oz", None))
        self.assertEqual(N.parse_quantity("Chomps Beef Sticks, 10g of Protein", extended=False), (None, None, None))
        self.assertEqual(self.q("Quest Bar 60g"), (60.0, "g", None))

    def test_pack_options_list_every_reading_the_name_supports(self):
        po = N.pack_options
        self.assertEqual(po("Pop-Tarts Frosted Strawberry, 58.6 oz, 32 Count"), [1, 32])
        self.assertEqual(po("Kikkoman Miso Soup, 1.05 oz, 3 Packets"), [1, 3])
        self.assertEqual(po("(24 Cans) Monster Rehab, 15.5 fl oz"), [1, 24])
        self.assertEqual(po("Famous Amos 2 oz Snack Pack, 36/Carton"), [1, 36])
        self.assertEqual(po("(3 pack) Pop-Ice, 1.5 Fl Oz, 80 Ct"), [1, 3, 80, 240])
        self.assertEqual(po("Hershey Topping Bettercream 15/12oz"), [1, 15])
        self.assertEqual(po("120pcspk Swdsh Fsh"), [1, 120])
        self.assertEqual(po("2.5oz Popcorn Kernel Packs, 24 Case"), [1, 24])
        self.assertEqual(po("Rhythm Kale Chips, 2 oz, (Pack of, 12)"), [1, 12])
        self.assertEqual(po("Niagara Water, 16.9 oz Bottle, 24/Pack, 2016/Pallet"), [1, 24, 2016])
        self.assertEqual(po("Del Monte Cut Green Beans, 14.5 oz Can"), [1])
        self.assertEqual(self.q("Klass Pineapple Drink, 0.26 Fl Oz, 36 Co"), (0.26, "fl oz", 36), "a count cut to 'Co'")

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
