"""crawler/classify.py: store categories, exclusions and placeholders, measured against the hand-labelled sample.

tests/fixtures/category-gold.jsonl.gz holds 2,811 items drawn from the live crawl (1,000 random Food, 400 from Food's
catch-all paths, and 100-300 from each other crawled department), each labelled from docs/CATEGORIES.md by reading the
item, not Walmart's path. Two independent labellers agreed on 98.5% of a 350-item overlap. The thresholds below are the
measured floor of the rules without path statistics (the pipeline adds them, about one point more); a change that lowers
accuracy fails here.
"""
import gzip, json, unittest
from collections import Counter
from pathlib import Path

from crawler import classify as C

REPO = Path(__file__).resolve().parent.parent
CFG = json.loads((REPO / "data" / "categories.json").read_text())
DEPTS = {d["name"]: d for d in CFG["departments"]}
FOOD = DEPTS["Food"]


def gold():
    with gzip.open(REPO / "tests" / "fixtures" / "category-gold.jsonl.gz", "rt") as f:
        return [json.loads(l) for l in f]


def cat(name, path="Home Page/Food/Pantry/Pantry meal essentials", dept=FOOD, brand=None):
    return C.category(C.clean_name(name)[0], brand, path, dept, CFG)


class Gold(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = gold()

    def test_exclusions_match_the_labels(self):
        tp = fp = fn = 0
        for g in self.rows:
            ex = C.exclusion(g["name"], g["brand"], g["path"], g["dept"], g["upc"])
            tp += bool(ex and g["exclude"]); fp += bool(ex and not g["exclude"]); fn += bool(g["exclude"] and not ex)
        self.assertGreaterEqual(tp / (tp + fn), 0.95, f"recall {tp}/{tp + fn}")
        self.assertLessEqual(fp, 3, "items wrongly excluded")

    def test_placeholders_match_the_labels(self):
        agree = sum(C.placeholder(g["name"], g["brand"]) == g["placeholder"] for g in self.rows)
        self.assertGreaterEqual(agree / len(self.rows), 0.99)

    def test_category_accuracy(self):
        ok, n, by = 0, 0, Counter()
        for g in self.rows:
            if g["exclude"] or g["placeholder"]:
                continue
            c = C.category(C.clean_name(g["name"])[0], g["brand"], g["path"], DEPTS[g["dept"]], CFG)
            n += 1; ok += c == g["cat"]
            by[(g["dept"] == "Food", c == g["cat"])] += 1
        food = by[(True, True)] / (by[(True, True)] + by[(True, False)])
        self.assertGreaterEqual(ok / n, 0.90, f"overall {ok}/{n}")
        self.assertGreaterEqual(food, 0.90, "Food")

    def test_walmart_path_alone_is_much_worse(self):
        # the reason the classifier exists: Walmart's path mislabels roughly a quarter of these items
        ok = n = 0
        for g in self.rows:
            if g["exclude"] or g["placeholder"]:
                continue
            n += 1; ok += C.decide(None, g["path"], DEPTS[g["dept"]], CFG) == g["cat"]
        self.assertLess(ok / n, 0.8)


class Exclusions(unittest.TestCase):
    def ex(self, name, path="Home Page/Food/Pantry", dept="Food", brand="", upc=None):
        return C.exclusion(name, brand, path, dept, upc)

    def test_apparel_and_shoes_anywhere(self):
        self.assertEqual(self.ex("White Stag® Long Sleeve Ribbed Turtleneck", "Home Page/Food/Fresh Food"), "apparel")
        self.assertEqual(self.ex("Holiday Time Red Plaid Dog Sweater, X-Small", "Home Page/Pets/Dogs", "Pets"), "apparel")
        self.assertEqual(self.ex("Garanimals - Baby Girls' Fleece Sweatsuit", "Home Page/Baby", "Baby"), "apparel")
        self.assertEqual(self.ex("Truform Compression Stockings, Knee High", "Home Page/Health and Medicine", "Health and Medicine"),
                         "apparel")
        self.assertEqual(self.ex("No Boundaries Nb Women Casual", "Home Page/Food/Meat & Seafood", brand="No Boundaries"), "apparel")
        self.assertEqual(self.ex("Faded Glory Msy Synthetic Sandal", "Home Page/Baby/Feeding", "Baby"), "footwear")

    def test_garment_words_inside_other_products_are_kept(self):
        for name in ("Capri Sun Juice Pouches, Lemonade, 6 Fl Oz, 10 Count", "(11 Pack) Prince Bow Ties 12 oz. Box",
                     "Graco Fastaction Fold Jogger Click Connect", "Universal Lightweight Blow Dryer Diffuser Sock",
                     "Assurance Underwear Small/Medium", "Safeskin Purple Nitrile Powder-Free Exam Disposable Gloves",
                     "Dr. Scholl's Women's Massaging Gel Insoles, Size 6-10", "Hooded Towel with Fish, Pink",
                     "Kraft Classic Ranch Dressing, 16 fl oz"):
            self.assertIsNone(self.ex(name), name)

    def test_reusable_period_underwear_is_apparel(self):
        self.assertEqual(self.ex("Proof Women's Super Heavy Absorbency, Brief Period Underwear", "Home Page/Personal Care",
                                 "Personal Care"), "apparel")

    def test_pet_beds(self):
        self.assertEqual(self.ex('Vibrant Life Small 21" x 17" Pet Bed, Solid', "Home Page/Food/Meat & Seafood"), "pet_bed")
        self.assertEqual(self.ex("Aspca High Pile Sherpa Crate Mat Medium", "Home Page/Pets/Dogs/Dog Crates", "Pets"), "pet_bed")
        self.assertIsNone(self.ex("Vibrant Life XL Training Pads, Super Absorbent", "Home Page/Pets/Dogs", "Pets"))

    def test_alcohol_is_a_drink_not_a_flavour(self):
        self.assertEqual(self.ex("(6 pack) White Claw Hard Seltzer Ruby Grapefruit, 19.2 fl oz Can, 5% ABV",
                                 "Home Page/Food/Alcohol/Single Serve"), "alcohol")
        self.assertIsNone(self.ex("(6 pack) Yellowstone Bourbon Brown Sugar BBQ Sauce, 19 oz"))
        self.assertIsNone(self.ex("Estrella Galicia 0,0 Non-Alcoholic Beer 15 Pack", "Home Page/Food/Alcohol/Beer"))
        self.assertIsNone(self.ex("Coco Lopez Pina Colada Drink Mix, 12 oz", "Home Page/Food/Alcohol/Pre-Mixed Cocktails"))

    def test_media(self):
        self.assertEqual(self.ex("Vinegars of the World, (Paperback)", brand="Laura Solieri"), "media")
        self.assertEqual(self.ex("Soul Sauce", brand="UMGD"), "media")
        self.assertEqual(self.ex("High-Hanging Fruit: Build Something Great by Going Where No One Else Will",
                                 brand="Mark Rampolla"), "media")
        self.assertEqual(self.ex("The Pacifier (2005)", "Home Page/Baby/Feeding", "Baby"), "media")
        self.assertIsNone(self.ex("Warner Brothers Looney Tunes Best Buds Super Soft Baby Blanket", "Home Page/Baby", "Baby",
                                  brand="Warner Bros."))


class Placeholders(unittest.TestCase):
    def test_names_that_identify_no_product(self):
        for name, brand in (("Merchandise", "Unbranded"), ("coming soon", "Munchkin"), ("(5 pack) coming soon", ""),
                            ("Signing Test 9173 Dummy Stress Test", "Unbranded"), ("TEST ITEM 3", "Parent's Choice"),
                            ("DO NOT USE- Barbecue Beans with Hickory BBQ Beef", "Fiorella's"), ("HUGGIES", "Huggies"),
                            ("CVP NON-TAX FL6206 D3 CVP Item", "Non Branded"), ("300PC CH GHST PPR HP", ""),
                            ("Discontinued Item by Supplier", "Prell"), ("Thai Kitchen Merchandise", "Thai Kitchen"),
                            ("Crest 32pc Cr Snstv Pdq3", "Oral-B")):
            self.assertTrue(C.placeholder(name, brand), name)

    def test_real_products_are_not(self):
        for name, brand in (("Great Value Whole Kernel Corn, 15.25 oz", "Great Value"), ("CRISOL VEG 128OZ", "Crisol"),
                            ("CAR SUN CHICK SEASON", "Caribbean Sunshine"), ("TRIPLE CROWN EVERLASTING TREATS", "Triple Crown"),
                            ("Hawaiian Naturals Soap", "Hawaiian Naturals Soap"),
                            ("Redpack Crushed Tomatoes in Puree with Basil, Garlic, and Oregano, Kosher, 28 oz", "Redpack"),
                            ("Extra White Gold Merchandise Gluten Free Bread Ground Flour Blend", "")):
            self.assertFalse(C.placeholder(name, brand), name)

    def test_store_displays_and_modules(self):
        """Walmart's pre-packed displays: module, half module, pallet, endcap (EC), shipper, a "- Display" floor model."""
        for name, price in (("FF Half Mod", 537.84), ("Ast 12pk Mod 1512ct", 3583.44), ("Baked Mod- 98case", 2916.48),
                            ("PLTR 400C WM Fall", 2972.0), ("HBO Pebbles Mega Pal", 1128.33), ("GIRL SCOUTS HALF PAL", 899.57),
                            ("Axe Kenobi Split EC", 1416.87), ("Lottie London Outer", 996.0), ("Voortman Spring Ship", 171.52),
                            ("DISP SLIDE2ME 2024", 0.01), ("Ingenuity Massage Seat - Display", 0.01),
                            ("Hair Color 4' Section Header Kit Walmart", 0.01), ("Hairitage - Shelf Rise - MINI 6 SKU", 0.01),
                            ("Non Tech/ Fitting SKU: Ray-Ban Meta Gen 2 Optics", 0.03)):
            self.assertTrue(C.placeholder(name, "", price), name)

    def test_products_that_only_look_like_displays(self):
        for name, price in (("Baby Mod Lily 2-in-1 Convertible Crib Honey Oak", 113.64), ("Maxim Wooden Pirate Ship", 59.97),
                            ("7\" LEMUR POUNCE PAL PLUSH, Case of 6", 73.5), ("LeapFrog - My Pal Violet - purple", 34.99),
                            ("Disp. Glove Free Form PF Nitrile Lge", 21.28), ("S/B Disp Rzr Twin + 12ct (Gn)", 6.25),
                            ("Delta Children Bassinet with Nightlight and Music Module", 49.99),
                            ("Iron Round 5 Tier Nail Polish Display Rack Wall Mounted Organizer", 44.31),
                            ("Digital Thermometer with Large Display", 35.0), ("(GIFT WITH PURCHASE) RoC Retinol Eye Cream", 17.99),
                            ("AAA Road Trip First Aid Kit, 121pc", 29.99), ("Hershey Assortment Bag Mini Mix 230 Pc", 12.04),
                            ("100pc Eye Shadow Set", 13.41), ("108pcs/sheet Nail Sticker Flower Nail Decal", 7.82)):
            self.assertFalse(C.placeholder(name, "", price), name)

    def test_discontinued_marker_is_removed_from_a_real_name(self):
        self.assertEqual(C.clean_name("***DISCONTINUED***Generations Night Time Moisturizer"),
                         ("Generations Night Time Moisturizer", True))
        self.assertEqual(C.clean_name("[Incomplete Data] Tia Rosa White Corn Megathin Tortilla Chips, 14 oz"),
                         ("Tia Rosa White Corn Megathin Tortilla Chips, 14 oz", False))


class Categories(unittest.TestCase):
    def test_the_product_noun_decides(self):
        self.assertEqual(cat("(3 pack) (3 Pack) Hershey's Instant Pudding Special Dark Chocolate, 3.56 Oz"), 28)
        self.assertEqual(cat("PBfit Organic Peanut Butter Powder, 30 Ounce"), 11)
        self.assertEqual(cat("Old London Melba Snacks Sea Salt, 5.25 oz"), 9)
        self.assertEqual(cat("(6 pack) Crown Prince Skinless & Boneless Sardines in Olive Oil, 3.75 oz Can"), 6)
        self.assertEqual(cat("(3 pack) (3 Pack) Hormel Compleats XL Chicken Breast & Mashed Potatoes, 13 Ounce"), 6)
        self.assertEqual(cat("Pride No Salt Added Whole Kernel Golden Corn, 15 oz Can"), 6)
        self.assertEqual(cat("Reese's Peanut Butter Cups, 1.5 oz"), 9)
        self.assertEqual(cat("Clipper Tea Organic Tea After Dinner Mint, 20 Bags"), 10)
        self.assertEqual(cat("Great Value Frozen Cut Green Beans, 16 oz"), 5)
        self.assertEqual(cat("Iberia Lentil Beans, Lentejas, 16 oz Bag"), 7)
        self.assertEqual(cat("La Fe Sweetened Condensed Milk, 14 oz Can"), 28)

    def test_non_food_found_in_food_is_labelled_as_what_it_is(self):
        self.assertEqual(cat("Brew Rite 8-12 Cup Basket Style Coffee Filters, 200 Ct", "Home Page/Food/Coffee/Coffee Filters"), 16)
        self.assertEqual(cat("Round Slate Cheese Board and Serving Tray", "Home Page/Food/Deli/Create Your Charcuterie Board"), 17)

    def test_flavour_words_never_move_a_non_food_item_into_food(self):
        pc = DEPTS["Personal Care"]
        self.assertEqual(cat("Le Petit Marseillais Shea Butter, Aloe & Beeswax Body Balm, 8.4 fl. oz",
                             "Home Page/Personal Care/Bath & Body/Body Lotions", pc), 15)
        self.assertEqual(cat("MIX:BAR Coconut Palm Body Wash with Vitamin E, 16fl oz",
                             "Home Page/Personal Care/Bath & Body/Body Wash", pc), 15)

    def test_specialty_departments_keep_their_items(self):
        self.assertEqual(cat("PET HEAD De Shed Me!! Shampoo", "Home Page/Pets/Cats/Cat Grooming", DEPTS["Pets"]), 19)
        self.assertEqual(cat("Status Milano Swivel Glider With Ottoman", "Home Page/Baby/Nursery & Decor/Gliders",
                             DEPTS["Baby"]), 13)
        self.assertEqual(cat("SAFAVIEH Monaco Vivyan Traditional Runner Rug, Green, 2'2\" X 8'",
                             "Home Page/Baby/Nursery & Decor/Baby Decor/Baby Rugs", DEPTS["Baby"]), 18)

    def test_every_category_id_is_named(self):
        named = set(CFG["categories"])
        for c, _, _ in C.LEXICON:
            self.assertIn(str(c), named)
        for _, c in CFG["path_rules"]:
            self.assertIn(str(c), named)
        for d in CFG["departments"]:
            self.assertIn(d["default_category"], named)


if __name__ == "__main__":
    unittest.main()
