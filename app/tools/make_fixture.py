#!/usr/bin/env python3
"""Full-scale fixture: a published snapshot shaped exactly like the pipeline's output.

    python3 app/tools/make_fixture.py --store app/build/fixture-store --items 760000 --seed 7

Writes, under --store (same layout as the data-store branch):
    build/published/items.jsonl.gz   rows produced by crawler.normalize.normalize() — the real code path
    build/published/stats.json       like crawler/process.py
    build/published/manifest.json    like crawler/qa.py publish (with "fixture": true)
    identify/equivalents.jsonl.gz    like crawler/identify.py match()
    identify/equivalents_stats.json

Why this shape: the app's DB builder (app/tools/build-db.mjs) reads a store checkout. Until the first
real snapshot publishes, CI points it at this fixture, so every byte the app loads went through the
same normalizer, primary-row selection and schema the production data will.

Realism knobs (see fixture_vocab.py): ~30% store brands, Walmart-style names, multipacks, retired
("deleted_") UPCs, duplicate UPCs across listings, promo flags, unreliable size fields. Every entry in
data/sentinels.json is present verbatim (sentinel_items.py) so the pipeline's own sentinel gate passes.
"""
import argparse, gzip, hashlib, json, math, os, random, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from crawler.normalize import normalize, gtin14, parse_quantity, to_base  # noqa: E402
from crawler.identify import OTHER_STORE_BRANDS, WALMART_STORE_BRANDS  # noqa: E402
import fixture_vocab as V  # noqa: E402
from sentinel_items import SENTINEL_ITEMS  # noqa: E402

CFG = json.loads((ROOT / "data" / "categories.json").read_text())
DEPTS = {d["id"]: d for d in CFG["departments"]}
DEPT_BY_TOP = {
    "food": "976759", "health and medicine": "976760", "pharmacy": "5431", "personal care": "1005862", "beauty": "1085666",
    "baby": "5427", "pets": "5440", "household essentials": "1115193", "home": "4044", "home improvement": "1072864",
    "patio & garden": "5428", "office supplies": "1229749", "arts crafts & sewing": "1334134", "toys": "4171", "books": "3920",
    "seasonal": "1085632", "party & occasions": "2637", "auto & tires": "91083", "electronics": "3944", "cell phones": "1105910",
    "jewelry": "3891", "sports & outdoors": "4125",
}

# Brand affinity: products whose brands would otherwise be drawn from a wide category list.
BRAND_HINTS = {
    "TV": ["onn.", "Samsung", "LG", "Sony", "TCL", "Hisense", "Vizio", "Roku", "Insignia", "Toshiba", "Philips"],
    "Laptop": ["HP", "Dell", "Lenovo", "Acer", "ASUS", "Apple", "Microsoft", "Samsung", "Google"],
    "Tablet": ["Apple", "Samsung", "Amazon", "onn.", "Lenovo", "Microsoft"],
    "Headphones": ["onn.", "JBL", "Bose", "Beats", "Skullcandy", "Apple", "Samsung", "Sony", "Anker", "Jabra", "Raycon", "Sennheiser", "Razer", "Turtle Beach"],
    "Bluetooth Speaker": ["onn.", "JBL", "Bose", "Anker", "Sony", "Amazon", "Google", "Apple", "Vizio", "Samsung"],
    "Phone Case": ["onn.", "OtterBox", "Speck", "Spigen", "Apple", "Samsung", "Casetify", "Zagg", "Belkin"],
    "Charger": ["onn.", "Anker", "Belkin", "Apple", "Samsung", "Scosche", "Mophie", "Duracell", "Energizer", "Zagg"],
    "Prepaid Phone": ["TracFone", "Straight Talk", "Total Wireless", "Motorola", "Samsung", "Apple", "Google"],
    "Video Game": ["Nintendo", "PlayStation", "Xbox", "Microsoft", "Sony", "Meta", "PowerA", "8Bitdo", "Hori", "Turtle Beach"],
    "Camera": ["GoPro", "Canon", "Fujifilm", "Polaroid", "Kodak", "Nikon", "DJI", "Sony"],
    "Smart Home Device": ["Ring", "Wyze", "Blink", "Eufy", "TP-Link", "Netgear", "Amazon", "Google", "Apple", "Roku", "Philips"],
    "Wearable": ["Apple", "Samsung", "Google", "Fitbit", "Garmin", "Amazfit", "Oura", "Whoop"],
    "Computer Accessory": ["onn.", "Logitech", "HP", "SanDisk", "Seagate", "WD", "Anker", "Belkin", "Razer", "Corsair", "HyperX", "SteelSeries", "Apple", "Samsung", "Canon", "Epson", "Brother", "Lexmark", "PopSockets", "Tile", "Chipolo"],
    "Watch": ["Timex", "Casio", "Armitron", "Fossil", "Citizen", "Seiko", "Bulova", "Michael Kors", "Guess", "Anne Klein", "Invicta", "Time and Tru", "Disney"],
    "Earrings": ["Brilliance Fine Jewelry", "Believe by Brilliance", "Time and Tru", "No Boundaries", "Pandora", "Swarovski", "Kendra Scott", "Kate Spade", "Disney", "Claire's", "Sterling Forever"],
    "Necklace": ["Brilliance Fine Jewelry", "Believe by Brilliance", "Keepsake", "Time and Tru", "Pandora", "Swarovski", "Kendra Scott", "Kate Spade", "Disney", "Alex and Ani"],
    "Ring": ["Brilliance Fine Jewelry", "Believe by Brilliance", "Keepsake", "Time and Tru", "Pandora", "Kay Jewelers", "Zales"],
    "Bracelet": ["Brilliance Fine Jewelry", "Time and Tru", "No Boundaries", "Pandora", "Alex and Ani", "Pura Vida", "Lokai", "Kendra Scott", "Disney"],
    "Jewelry Set": ["Brilliance Fine Jewelry", "Believe by Brilliance", "Time and Tru", "Disney", "Claire's", "Swarovski"],
    "Motor Oil": ["SuperTech", "Pennzoil", "Mobil 1", "Castrol", "Valvoline", "Quaker State", "Shell Rotella", "Royal Purple", "Lucas Oil", "STP"],
    "Automotive Fluid": ["SuperTech", "Prestone", "Peak", "Zerex", "Rain-X", "STP", "Lucas Oil", "Gumout", "Sea Foam", "Valvoline", "Castrol"],
    "Car Care": ["Rain-X", "Armor All", "Meguiar's", "Turtle Wax", "Chemical Guys", "Black Magic", "Mothers", "WD-40", "Auto Drive", "Adam's Polishes"],
    "Auto Part": ["SuperTech", "EverStart", "Bosch", "Trico", "Michelin", "Anco", "Fram", "K&N", "Purolator", "Motorcraft", "ACDelco", "NGK", "Denso", "Champion", "Autolite", "Duralast", "Optima", "DieHard", "Wagner", "Raybestos", "Monroe", "Gates", "Dorman", "Schumacher", "NOCO", "Stanley", "Energizer"],
    "Car Accessory": ["Auto Drive", "Weathertech", "Husky Liners", "Motor Trend", "BDK", "FH Group", "Garmin", "Cobra", "Scosche", "iOttie", "Belkin", "Anker", "Budge", "Classic Accessories", "Thule", "Curt", "Reese", "Hopkins"],
    "Exercise Equipment": ["Athletic Works", "CAP Barbell", "Gold's Gym", "Weider", "Marcy", "Bowflex", "NordicTrack", "ProForm", "Sunny Health & Fitness", "Everlast", "TRX", "Gaiam", "Theragun", "Hyperice", "Bala", "Echelon", "Schwinn Fitness"],
    "Camping Gear": ["Ozark Trail", "Coleman", "Igloo", "Yeti", "Stanley", "Hydro Flask", "Intex", "Bestway", "Lifetime", "Pelican", "Sevylor", "Zebco", "Shakespeare", "Ugly Stik", "Berkley", "Rapala", "Plano", "Lew's", "Abu Garcia", "Eagle Claw", "Bushnell", "Garmin", "Thermacell", "Mossy Oak"],
    "Bike": ["Schwinn", "Huffy", "Kent", "Mongoose", "Hyper Bicycles", "Bell", "Razor", "Ozark Trail"],
    "Sports Equipment": ["Athletic Works", "Wilson", "Spalding", "Rawlings", "Franklin", "Easton", "Louisville Slugger", "Mizuno", "Nike", "Adidas", "Under Armour", "Everlast", "Callaway", "TaylorMade", "Titleist", "Top Flite", "Pinnacle", "Nitro", "Lifetime", "Speedo", "TYR", "Intex", "Nerf"],
    "Sports Nutrition": ["Optimum Nutrition", "Premier Protein", "Muscle Milk", "BSN", "Cellucor", "Ghost", "Alani Nu", "Celsius", "Gatorade", "BodyArmor", "Liquid I.V.", "LMNT", "Nuun", "GU", "Clif", "Quest", "Kind", "RXBAR", "Pure Protein", "Orgain", "Vega", "Vital Proteins", "Six Star", "MuscleTech", "Dymatize", "Isopure", "C4", "Bucked Up", "Ryse", "Redcon1", "Xtend"],
    "Christmas Lights": ["Holiday Time", "GE", "Philips", "Sylvania", "National Tree Company", "Wondershop"],
    "Christmas Decoration": ["Holiday Time", "National Tree Company", "Wondershop", "Hallmark", "Elf on the Shelf", "Rudolph", "Peanuts", "Disney", "Mainstays", "Better Homes & Gardens", "The Pioneer Woman", "Hershey's", "Reese's", "Russell Stover", "Lindt", "Ferrero", "Brach's", "Peeps"],
    "Halloween Decoration": ["Way to Celebrate", "Spooky Village", "Spirit Halloween", "Rubie's", "Disguise", "Jazwares", "Hershey's", "Mars", "Reese's", "Brach's", "Disney", "Marvel", "Nickelodeon"],
    "Party Supplies": ["Way to Celebrate", "Amscan", "Unique", "Creative Converting", "Balloon Time", "Qualatex", "Anagram", "Disney", "Nickelodeon", "Marvel", "Barbie", "Hot Wheels", "Paw Patrol", "Bluey"],
    "Party Tableware": ["Way to Celebrate", "Amscan", "Unique", "Creative Converting", "Hefty", "Solo", "Dixie", "Chinet", "Vanity Fair", "Disney", "Nickelodeon", "Marvel"],
    "Gift Wrap": ["Way to Celebrate", "Hallmark", "American Greetings", "Papyrus", "Holiday Time", "Scotch", "Duck", "Disney", "Nickelodeon", "Marvel", "Star Wars"],
    "Greeting Card": ["Hallmark", "American Greetings", "Papyrus", "Way to Celebrate"],
    "Building Set": ["LEGO", "Mega Bloks", "Magna-Tiles", "Picasso Tiles", "K'NEX", "Lincoln Logs", "Tinkertoy", "Melissa & Doug", "Spark Create Imagine", "Kid Connection"],
    "Toy Car": ["Hot Wheels", "Matchbox", "Disney Pixar Cars", "Monster Jam", "Paw Patrol", "Adventure Force", "Kid Connection", "Tonka", "John Deere", "Bruder"],
    "Doll": ["Barbie", "L.O.L. Surprise!", "Rainbow High", "Baby Alive", "My Life As", "American Girl", "Our Generation", "Disney Princess", "Monster High", "Polly Pocket", "Gabby's Dollhouse"],
    "Action Figure": ["Marvel", "Star Wars", "Transformers", "Paw Patrol", "Bluey", "Pokemon", "Funko Pop!", "Jurassic World", "Beyblade", "Spin Master", "Imaginext", "Fisher-Price", "Playskool"],
    "Board Game": ["Hasbro Gaming", "Mattel Games", "Monopoly", "UNO", "Jenga", "Connect 4", "Candy Land", "Spin Master", "Catan", "Ticket to Ride", "Exploding Kittens", "Codenames", "Cards Against Humanity", "Bicycle", "Buffalo Games", "Ravensburger"],
    "Puzzle": ["Buffalo Games", "Ravensburger", "Ceaco", "Melissa & Doug", "Spin Master", "Cra-Z-Art", "Spark Create Imagine", "Hasbro Gaming"],
    "Book": ["Scholastic", "Penguin Random House", "HarperCollins", "Simon & Schuster", "Hachette", "Macmillan", "Dr. Seuss", "Golden Books", "Usborne", "DK", "Highlights", "Little Golden Books", "Random House", "Disney Press", "Marvel Press"],
    "Dry Dog Food": ["Ol' Roy", "Pure Balance", "Pedigree", "Purina Dog Chow", "Purina ONE", "Purina Pro Plan", "Beneful", "Kibbles 'n Bits", "Iams", "Blue Buffalo", "Rachael Ray Nutrish", "Taste of the Wild", "Hill's Science Diet", "Royal Canin", "Nutro", "Wellness", "Merrick", "Diamond Naturals", "Natural Balance"],
    "Wet Dog Food": ["Ol' Roy", "Pure Balance", "Pedigree", "Cesar", "Alpo", "Gravy Train", "Purina ONE", "Purina Pro Plan", "Beneful", "Blue Buffalo", "Rachael Ray Nutrish", "Hill's Science Diet"],
    "Dog Treats": ["Ol' Roy", "Pure Balance", "Milk-Bone", "Pup-Peroni", "Beggin' Strips", "Greenies", "Dentastix", "Busy Bone", "Blue Buffalo", "Nylabone", "Full Moon", "Canine Carry Outs", "Charlee Bear", "Purina Pro Plan"],
    "Dry Cat Food": ["Special Kitty", "Pure Balance", "Friskies", "Meow Mix", "Purina Cat Chow", "9Lives", "Purina ONE", "Purina Pro Plan", "Blue Buffalo", "Iams", "Hill's Science Diet", "Royal Canin", "Rachael Ray Nutrish"],
    "Wet Cat Food": ["Special Kitty", "Friskies", "Fancy Feast", "Sheba", "9Lives", "Meow Mix", "Purina ONE", "Purina Pro Plan", "Blue Buffalo", "Iams"],
    "Cat Treats": ["Temptations", "Friskies", "Fancy Feast", "Greenies", "Special Kitty", "Blue Buffalo", "Purina Pro Plan"],
    "Cat Litter": ["Special Kitty", "Tidy Cats", "Fresh Step", "Arm & Hammer", "Scoop Away", "Purina Yesterday's News", "Frisco"],
    "Flea & Tick Treatment": ["Frontline Plus", "Advantage II", "Seresto", "Hartz", "Adams", "PetArmor", "Sentry", "Vibrant Life"],
    "Dog Supplies": ["Vibrant Life", "Kong", "Nylabone", "Chuckit!", "PetSafe", "Petmate", "Midwest Homes", "Frisco", "Furhaven", "K&H", "Coastal Pet", "Blueberry Pet", "Lupine", "Flexi", "Earth Rated", "Nature's Miracle", "Simple Solution", "Burt's Bees for Pets", "Wahl", "FURminator", "Hertzko", "Arm & Hammer for Pets", "Rocco & Roxie", "Hartz"],
    "Cat Supplies": ["Vibrant Life", "Catit", "SmartyKat", "Yeowww!", "Trixie", "PetFusion", "Litter Genie", "Petmate", "Frisco", "Furhaven", "K&H", "Nature's Miracle", "Hartz", "Arm & Hammer for Pets", "FURminator"],
    "Aquarium Supplies": ["Tetra", "Aqueon", "API", "Top Fin", "Vibrant Life"],
    "Small Animal Supplies": ["Kaytee", "Wild Harvest", "Oxbow", "Carefresh", "Vibrant Life"],
    "Crayons": ["Crayola", "Cra-Z-Art", "Rose Art", "Pen+Gear"], "Colored Pencils": ["Crayola", "Prismacolor", "Faber-Castell", "Cra-Z-Art", "Staedtler", "Arteza", "Pen+Gear"],
    "Markers": ["Crayola", "Sharpie", "Expo", "Pen+Gear", "Cra-Z-Art", "Paper Mate", "Tombow", "Ohuhu", "Arteza", "BIC"],
    "Pens": ["Pen+Gear", "BIC", "Paper Mate", "Pilot", "Uni-ball", "Pentel", "Zebra", "Sharpie", "Sakura"],
    "Pencils": ["Ticonderoga", "Pen+Gear", "BIC", "Paper Mate", "Pentel", "Crayola", "Staedtler"],
    "Notebook": ["Pen+Gear", "Five Star", "Mead", "Moleskine", "Rocketbook", "Leuchtturm1917", "Blue Sky", "At-A-Glance", "Day-Timer", "TOPS", "Oxford", "Strathmore", "Canson"],
    "Paper": ["Pen+Gear", "HP", "Hammermill", "Georgia-Pacific", "Boise", "Astrobrights", "Neenah", "Southworth", "Avery", "Crayola", "Strathmore", "Canson", "Artist's Loft", "Cricut", "Scotch", "Fellowes"],
    "Food Storage Containers": ["Mainstays", "Rubbermaid", "Pyrex", "Anchor Hocking", "Sterilite", "Hefty", "Glad", "Ziploc", "Tupperware", "OXO", "Snapware", "Lock & Lock", "The Pioneer Woman"],
    "Water Pitcher": ["Brita", "PUR", "ZeroWater", "Mainstays"], "Water Filter Replacement": ["Brita", "PUR", "ZeroWater", "Mainstays"],
    "Water Bottle": ["Contigo", "Stanley", "Yeti", "Hydro Flask", "Ozark Trail", "Thermos", "Takeya", "Simple Modern", "Owala", "Mainstays"],
    "Tumbler": ["Stanley", "Yeti", "Ozark Trail", "Simple Modern", "Contigo", "Mainstays", "Thermos"],
    "Dinnerware Set": ["Mainstays", "Better Homes & Gardens", "The Pioneer Woman", "Beautiful by Drew Barrymore", "Corelle", "Gibson", "Pfaltzgraff"],
    "Dinner Plates": ["Mainstays", "Better Homes & Gardens", "The Pioneer Woman", "Corelle", "Gibson", "Pfaltzgraff"],
    "Drinking Glasses": ["Mainstays", "Libbey", "Better Homes & Gardens", "The Pioneer Woman", "Anchor Hocking"],
    "Cookware Set": ["Mainstays", "T-fal", "Farberware", "Calphalon", "Carote", "Tramontina", "Rachael Ray", "The Pioneer Woman", "Beautiful by Drew Barrymore", "Cuisinart", "Lodge"],
    "Frying Pan": ["T-fal", "Farberware", "Calphalon", "Lodge", "Carote", "Tramontina", "Mainstays", "The Pioneer Woman", "Cuisinart"],
    "Saucepan": ["T-fal", "Farberware", "Calphalon", "Tramontina", "Mainstays", "Cuisinart"], "Stock Pot": ["T-fal", "Farberware", "Tramontina", "Mainstays", "Lodge", "Cuisinart", "The Pioneer Woman"],
    "Baking Sheet": ["Wilton", "Nordic Ware", "Mainstays", "Farberware", "Good Cook", "The Pioneer Woman"], "Glass Baking Dish": ["Pyrex", "Anchor Hocking", "Mainstays"],
    "Kitchen Utensil Set": ["Mainstays", "OXO", "Farberware", "The Pioneer Woman", "Beautiful by Drew Barrymore", "Good Cook", "Tramontina"],
    "Kitchen Gadget": ["Mainstays", "OXO", "Farberware", "Good Cook", "Ekco", "KitchenAid", "The Pioneer Woman", "Rubbermaid", "Cuisinart"],
    "Knife Set": ["Farberware", "Chicago Cutlery", "Henckels", "Cuisinart", "Mainstays", "The Pioneer Woman", "Beautiful by Drew Barrymore"],
    "Chef Knife": ["Farberware", "Chicago Cutlery", "Henckels", "Victorinox", "Cuisinart", "Mainstays"],
    "Storage Tote": ["Sterilite", "Rubbermaid", "Hefty", "Mainstays", "Iris", "Hometrends"], "Trash Can": ["Mainstays", "Hefty", "Sterilite", "Rubbermaid", "Glad", "Better Homes & Gardens"],
    "Coffee Maker": ["Keurig", "Mr. Coffee", "Hamilton Beach", "Black+Decker", "Ninja", "Cuisinart", "Bodum", "Chemex", "Mainstays", "Beautiful by Drew Barrymore"],
    "Blender": ["Ninja", "Nutribullet", "Vitamix", "Hamilton Beach", "Oster", "KitchenAid", "Black+Decker", "Mainstays", "Beautiful by Drew Barrymore", "Cuisinart"],
    "Toaster": ["Hamilton Beach", "Black+Decker", "Cuisinart", "Oster", "Mainstays", "Beautiful by Drew Barrymore", "Ninja", "Dash"],
    "Air Fryer": ["Ninja", "Instant Pot", "Gourmia", "Cosori", "Chefman", "Dash", "Bella", "Beautiful by Drew Barrymore", "Mainstays", "Hamilton Beach", "Black+Decker"],
    "Slow Cooker": ["Crock-Pot", "Instant Pot", "Ninja", "Hamilton Beach", "Black+Decker", "Oster", "Mainstays", "Presto", "Cuisinart", "KitchenAid", "Dash", "Elite Gourmet"],
    "Microwave": ["Hamilton Beach", "Mainstays", "Black+Decker", "Toshiba", "Panasonic", "Frigidaire", "LG", "Hisense", "Midea"],
    "Sheet Set": ["Mainstays", "Better Homes & Gardens", "Allswell", "Hometrends", "Gap Home", "Utopia Bedding", "Bare Home", "Martha Stewart", "AmazonBasics", "Serta"],
    "Comforter": ["Mainstays", "Better Homes & Gardens", "Allswell", "Hometrends", "Gap Home", "Utopia Bedding", "Martha Stewart", "The Pioneer Woman"],
    "Pillow": ["Mainstays", "Better Homes & Gardens", "Allswell", "Serta", "Beautyrest", "Sealy", "Tempur-Pedic", "Casper", "Linenspa", "Lucid", "Sleep Innovations"],
    "Bath Towel": ["Mainstays", "Better Homes & Gardens", "Allswell", "Hometrends", "Gap Home", "Martha Stewart", "Utopia Bedding"],
    "Candle": ["Yankee Candle", "Glade", "Febreze", "Bath & Body Works", "Village Candle", "Chesapeake Bay", "WoodWick", "Mrs. Meyer's", "Mainstays", "Better Homes & Gardens"],
    "Lamp": ["Mainstays", "Better Homes & Gardens", "Hyper Tough", "GE", "Philips", "Sylvania", "Hunter", "Harbor Breeze", "Hometrends"],
    "Furniture": ["Mainstays", "Better Homes & Gardens", "Sauder", "Ameriwood", "Furinno", "Zinus", "Lifetime", "Cosco", "Flash Furniture", "Walker Edison", "Dorel Living", "Hometrends", "Allswell", "Serta", "Linenspa", "Lucid", "Ozark Trail", "Keter", "Suncast"],
    "Area Rug": ["Mainstays", "Better Homes & Gardens", "Hometrends", "Gap Home", "The Pioneer Woman", "Beautiful by Drew Barrymore"],
    "Wall Decor": ["Mainstays", "Better Homes & Gardens", "Hometrends", "The Pioneer Woman", "Beautiful by Drew Barrymore", "Martha Stewart"],
    "Hanger": ["Mainstays", "Whitmor", "Honey-Can-Do", "Simple Houseware", "ClosetMaid"], "Closet Organizer": ["Mainstays", "Sterilite", "Rubbermaid", "Whitmor", "Honey-Can-Do", "Simple Houseware", "ClosetMaid", "Iris"],
    "Hand Tool": ["Hyper Tough", "Hart", "Stanley", "DeWalt", "Black+Decker", "Craftsman", "Ryobi", "Milwaukee", "Kobalt", "Husky", "Irwin", "Klein Tools", "Fiskars", "Corona", "Ames", "True Temper", "Expert Gardener", "Flexzilla", "Gilmour", "Orbit", "Rain Bird", "Scotts"],
    "Paint": ["Glidden", "Behr", "Rust-Oleum", "Valspar", "Kilz", "Minwax"], "Spray Paint": ["Rust-Oleum", "Krylon", "Hyper Tough"], "Paint Supplies": ["Hyper Tough", "Purdy", "Wooster", "Frog Tape", "Scotch", "3M", "DAP", "Rust-Oleum", "Minwax", "Gorilla"],
    "Hardware": ["Hyper Tough", "Hart", "Stanley", "Gorilla", "3M", "Command", "Scotch", "Expert Gardener", "Scotts", "Miracle-Gro", "Roundup", "Ortho", "Spectracide", "Pennington", "Vigoro", "Burpee", "Ferry-Morse"],
    "Grill": ["Expert Grill", "Weber", "Char-Broil", "Blackstone", "Traeger", "Pit Boss", "Kingsford", "Royal Oak", "Coleman", "Ozark Trail", "Igloo", "Yeti"],
    "Fan": ["Mainstays", "Lasko", "Vornado", "Honeywell", "Dyson", "Frigidaire", "LG", "Hisense", "Midea", "Toshiba", "Black+Decker", "Pelonis", "Holmes", "Levoit", "Winix", "Germ Guardian", "Dreo", "GE"],
}


HEALTH_DEVICES = ["Equate", "Omron", "Braun", "ACE", "Futuro", "Dr. Scholl's", "Band-Aid", "Curad", "Nexcare", "Johnson & Johnson", "ReliOn", "OneTouch", "Accu-Chek", "FreeStyle", "Contour", "Vicks", "Breathe Right", "Debrox", "Similasan", "Systane", "Refresh", "Bausch + Lomb", "Opti-Free", "Biotrue"]
for _n in ["Digital Thermometer", "Blood Pressure Monitor", "Pulse Oximeter", "Heating Pad", "Hot/Cold Pack", "Compression Socks", "Pill Organizer", "Blood Glucose Test Strips",
           "Blood Glucose Meter", "Lancets", "Glucose Tablets", "Insulin Syringes", "Reading Glasses", "Humidifier", "Foot Insoles", "Corn & Callus Remover", "Foot Cream", "Knee Brace",
           "Wrist Brace", "Ankle Support", "Elastic Bandage", "Medical Tape", "Gauze Pads", "First Aid Kit", "Adhesive Bandages", "Hydrogen Peroxide", "Isopropyl Alcohol", "Nasal Strips",
           "Eye Drops", "Contact Lens Solution", "Ear Wax Removal", "Denture Adhesive", "Denture Cleanser Tablets"]:
    BRAND_HINTS[_n] = HEALTH_DEVICES
for _n in ["Hair Dryer", "Flat Iron", "Curling Iron", "Hair Brush", "Hair Ties"]:
    BRAND_HINTS[_n] = ["Conair", "Remington", "Revlon One-Step", "Scunci", "Goody", "Wet Brush", "Tangle Teezer", "Equate"]
for _n in ["Electric Shaver", "Hair Clippers"]:
    BRAND_HINTS[_n] = ["Remington", "Wahl", "Conair", "Gillette", "Equate", "Philips"]
for _n in ["Electric Toothbrush", "Toothbrush Heads"]:
    BRAND_HINTS[_n] = ["Oral-B", "Oral-B Pro", "Philips Sonicare", "Equate", "Colgate", "Waterpik"]
BRAND_HINTS["Makeup Brushes"] = ["e.l.f.", "Real Techniques", "EcoTools", "Equate", "Maybelline"]
BRAND_HINTS["Perfume"] = ["Bath & Body Works", "Britney Spears", "Curve", "Body Fantasies", "Ariana Grande", "Calvin Klein", "Marc Jacobs", "Davidoff"]
BRAND_HINTS["Cologne"] = ["Axe", "Old Spice", "Nautica", "Curve", "Davidoff", "Giorgio Armani", "Calvin Klein", "Ralph Lauren"]


FOOD_HH_HINTS = {
    "Soda Pop": ["Coca-Cola", "Diet Coke", "Coke Zero Sugar", "Pepsi", "Diet Pepsi", "Pepsi Zero Sugar", "Mountain Dew", "Dr Pepper", "Sprite", "Fanta", "7UP", "A&W", "Canada Dry", "Sunkist", "Mug", "Crush", "Barq's", "Starry", "Sam's Choice", "Great Value"],
    "Mini Cans Soda": ["Coca-Cola", "Diet Coke", "Pepsi", "Sprite", "Dr Pepper", "Canada Dry"],
    "Purified Drinking Water": ["Great Value", "Sam's Choice", "Dasani", "Aquafina", "Nestle Pure Life", "Pure Life", "Ice Mountain", "Deer Park", "Poland Spring"],
    "Purified Water": ["Great Value", "Pure Life", "Dasani", "Aquafina"], "Water": ["Great Value", "Smartwater", "Fiji", "Essentia", "LIFEWTR", "Core", "Dasani", "Aquafina", "Ice Mountain", "Deer Park", "Poland Spring", "Ozarka"],
    "Sparkling Water": ["La Croix", "Bubly", "Polar", "Perrier", "Topo Chico", "Spindrift", "Clear American", "Great Value", "Liquid Death"], "Flavored Water": ["Clear American", "Propel", "Vitaminwater", "Sparkling Ice", "Bai"],
    "Orange Juice": ["Tropicana", "Simply", "Minute Maid", "Florida's Natural", "Great Value"], "Apple Juice": ["Mott's", "Great Value", "Tree Top", "Juicy Juice", "Apple & Eve"],
    "Cranberry Juice Cocktail": ["Ocean Spray", "Great Value"], "Grape Juice": ["Welch's", "Great Value"], "Juice Drink": ["Capri Sun", "Kool-Aid", "Honest Kids", "Hi-C", "Juicy Juice", "Great Value"],
    "Fruit Punch": ["Hawaiian Punch", "Minute Maid", "Great Value"], "Vegetable Juice": ["V8", "Great Value"], "Sports Drink": ["Gatorade", "Powerade", "BodyArmor", "Propel", "Prime", "Great Value"],
    "Energy Drink": ["Red Bull", "Monster", "Celsius", "Bang", "Rockstar", "Reign", "Alani Nu", "Ghost"], "Ground Coffee": ["Folgers", "Maxwell House", "Dunkin'", "Starbucks", "Community Coffee", "Eight O'Clock", "Peet's", "Cafe Bustelo", "Great Value"],
    "Coffee Pods": ["Green Mountain", "Keurig", "Starbucks", "Dunkin'", "Folgers", "Maxwell House", "Peet's", "Great Value", "Donut Shop"], "Instant Coffee": ["Nescafe", "Folgers", "Maxwell House", "Cafe Bustelo", "Great Value"],
    "Black Tea Bags": ["Lipton", "Tetley", "Luzianne", "Great Value", "Twinings", "Bigelow"], "Herbal Tea Bags": ["Celestial Seasonings", "Bigelow", "Twinings", "Tazo", "Yogi", "Traditional Medicinals"],
    "Iced Tea": ["Arizona", "Pure Leaf", "Gold Peak", "Snapple", "Brisk", "Lipton", "Great Value"], "Drink Mix": ["Crystal Light", "Kool-Aid", "Great Value", "Country Time", "Wyler's Light", "Gatorade", "Propel"],
    "Drink Mix Canister": ["Kool-Aid", "Country Time", "Tang", "Great Value", "Gatorade"], "Liquid Water Enhancer": ["Mio", "Crystal Light", "Great Value", "Kool-Aid"],
    "Chocolate Drink Mix": ["Nesquik", "Ovaltine", "Great Value", "Hershey's"], "Hot Cocoa Mix": ["Swiss Miss", "Nestle", "Great Value", "Starbucks", "Ghirardelli"],
    "Nutrition Shake": ["Ensure", "Boost", "Glucerna", "Premier Protein", "Carnation Breakfast Essentials", "Equate", "Great Value"], "Protein Shake": ["Premier Protein", "Muscle Milk", "Fairlife Core Power", "Orgain", "Ensure", "Boost", "Equate"],
    "Electrolyte Solution": ["Pedialyte", "Equate", "Parent's Choice"], "Electrolyte Powder Packets": ["Liquid I.V.", "Pedialyte", "LMNT", "Equate"], "Chocolate Milk": ["Nesquik", "Fairlife", "Great Value", "TruMoo", "Horizon Organic"],
    "Cereal": ["Cheerios", "Honey Nut Cheerios", "Kellogg's", "Frosted Flakes", "Raisin Bran", "Post", "Quaker", "Cap'n Crunch", "Lucky Charms", "Cinnamon Toast Crunch", "Froot Loops", "Life", "Special K", "Honey Bunches of Oats", "General Mills", "Great Value", "Kashi", "Cascadian Farm"],
    "Cereal Bag": ["Malt-O-Meal", "Great Value"], "Old Fashioned Oats": ["Quaker", "Great Value", "Bob's Red Mill"], "Quick Oats": ["Quaker", "Great Value"], "Instant Oatmeal": ["Quaker", "Great Value", "Kodiak Cakes", "Nature's Path"],
    "Grits": ["Quaker", "Great Value"], "Pancake & Waffle Mix": ["Pearl Milling Company", "Bisquick", "Krusteaz", "Hungry Jack", "Kodiak Cakes", "Great Value"], "Pancake Syrup": ["Pearl Milling Company", "Mrs. Butterworth's", "Log Cabin", "Hungry Jack", "Great Value"],
    "Peanut Butter": ["Jif", "Skippy", "Peter Pan", "Great Value", "Smucker's", "Justin's", "Reese's"], "Hazelnut Spread": ["Nutella", "Great Value", "Jif"], "Grape Jelly": ["Smucker's", "Welch's", "Great Value"], "Strawberry Preserves": ["Smucker's", "Bonne Maman", "Great Value", "Welch's"],
    "Jam": ["Smucker's", "Bonne Maman", "Great Value", "Welch's"], "Spaghetti": ["Barilla", "Great Value", "Ronzoni", "Mueller's", "De Cecco"], "Elbow Macaroni": ["Great Value", "Barilla", "Ronzoni", "Mueller's"],
    "Penne Rigate": ["Barilla", "Great Value", "Ronzoni"], "Rotini": ["Barilla", "Great Value", "Ronzoni"], "Macaroni & Cheese Dinner": ["Kraft", "Great Value", "Annie's", "Velveeta"], "Shells & Cheese": ["Velveeta", "Kraft", "Great Value", "Annie's"],
    "Macaroni & Cheese Cups": ["Kraft", "Velveeta", "Great Value", "Annie's"], "Hamburger Helper": ["Hamburger Helper", "Great Value"], "Rice Mix": ["Rice-A-Roni", "Knorr", "Zatarain's", "Great Value", "Ben's Original"],
    "Long Grain White Rice": ["Great Value", "Mahatma", "Carolina", "Riceland"], "Jasmine Rice": ["Mahatma", "Great Value", "Carolina", "Three Ladies"], "Instant Rice": ["Minute", "Great Value", "Success"], "Ready Rice": ["Ben's Original", "Uncle Ben's", "Great Value", "Minute"],
    "Dried Beans": ["Great Value", "Goya", "Camellia", "Hurst's"], "All Purpose Flour": ["Gold Medal", "King Arthur", "Pillsbury", "Great Value"], "Granulated Sugar": ["Domino", "C&H", "Imperial Sugar", "Great Value"],
    "Brown Sugar": ["Domino", "C&H", "Great Value"], "Powdered Sugar": ["Domino", "C&H", "Great Value"], "Vegetable Oil": ["Great Value", "Wesson", "Crisco", "Mazola"], "Canola Oil": ["Great Value", "Wesson", "Crisco", "Mazola"],
    "Olive Oil": ["Bertolli", "Pompeian", "Filippo Berio", "Great Value", "Colavita"], "Cooking Spray": ["Pam", "Great Value", "Crisco"], "Cake Mix": ["Betty Crocker", "Duncan Hines", "Pillsbury", "Great Value"], "Frosting": ["Betty Crocker", "Duncan Hines", "Pillsbury", "Great Value"],
    "Brownie Mix": ["Betty Crocker", "Duncan Hines", "Pillsbury", "Ghirardelli", "Great Value"], "Chocolate Chips": ["Nestle Toll House", "Hershey's", "Ghirardelli", "Great Value"], "Granola Bars": ["Nature Valley", "Quaker Chewy", "Kind", "Clif", "Great Value"],
    "Toaster Pastries": ["Pop-Tarts", "Great Value"], "Breakfast Bars": ["Nutri-Grain", "Great Value"], "Breakfast Biscuits": ["Belvita"], "Protein Bars": ["Quest", "Kind", "Clif", "Pure Protein", "RXBAR"],
    "Peanuts": ["Planters", "Great Value", "Fisher"], "Almonds": ["Blue Diamond", "Great Value", "Planters"], "Mixed Nuts": ["Planters", "Great Value"], "Cashews": ["Planters", "Great Value"], "Pistachios": ["Wonderful Pistachios", "Great Value"],
    "Raisins": ["Sun-Maid", "Great Value"], "Dried Cranberries": ["Ocean Spray", "Craisins", "Great Value"], "Mashed Potatoes": ["Idahoan", "Great Value", "Hungry Jack"], "Stuffing Mix": ["Stove Top", "Great Value", "Pepperidge Farm"],
    "Pasta Side": ["Knorr", "Pasta Roni", "Great Value"], "Taco Dinner Kit": ["Old El Paso", "Ortega", "Great Value", "Taco Bell"], "Whole Kernel Corn": ["Great Value", "Del Monte", "Green Giant", "Libby's"],
    "Cut Green Beans": ["Great Value", "Del Monte", "Green Giant", "Allens"], "Sweet Peas": ["Great Value", "Del Monte", "Green Giant", "Le Sueur"], "Mixed Vegetables": ["Great Value", "Del Monte", "Veg-All"], "Sliced Carrots": ["Great Value", "Del Monte"],
    "Sliced Peaches": ["Del Monte", "Great Value", "Dole"], "Pineapple": ["Dole", "Great Value", "Del Monte"], "Fruit Cocktail": ["Great Value", "Del Monte", "Dole"], "Mandarin Oranges": ["Dole", "Great Value", "Del Monte"],
    "Applesauce": ["Mott's", "Great Value", "Musselman's"], "Applesauce Cups": ["Mott's", "Great Value", "GoGo squeeZ"], "Baked Beans": ["Bush's", "Great Value", "Van Camp's", "B&M"], "Black Beans": ["Great Value", "Goya", "Bush's"],
    "Dark Red Kidney Beans": ["Great Value", "Bush's", "Goya"], "Pinto Beans": ["Great Value", "Bush's", "Goya"], "Refried Beans": ["Old El Paso", "Rosarita", "Great Value", "Goya"], "Chili with Beans": ["Hormel", "Wolf Brand", "Great Value", "Armour"],
    "Chicken Noodle Soup": ["Campbell's", "Progresso", "Great Value", "Healthy Choice"], "Tomato Soup": ["Campbell's", "Great Value", "Progresso"], "Cream of Mushroom Soup": ["Campbell's", "Great Value"], "Cream of Chicken Soup": ["Campbell's", "Great Value"],
    "Soup": ["Progresso", "Campbell's", "Great Value", "Healthy Choice", "Amy's"], "Ramen Noodle Soup": ["Maruchan", "Nissin", "Nongshim", "Great Value"], "Chicken Broth": ["Swanson", "Great Value", "College Inn", "Kitchen Basics"], "Beef Broth": ["Swanson", "Great Value", "College Inn"],
    "Chunk Light Tuna": ["StarKist", "Bumble Bee", "Chicken of the Sea", "Great Value"], "Solid White Albacore Tuna": ["StarKist", "Bumble Bee", "Chicken of the Sea", "Great Value"], "Chunk Chicken Breast": ["Great Value", "Swanson", "Kirkland Signature"],
    "Spam": ["Spam"], "Vienna Sausage": ["Armour", "Libby's", "Great Value"], "Beef Stew": ["Dinty Moore", "Great Value", "Armour"], "Corned Beef Hash": ["Hormel", "Armour", "Libby's"], "Pink Salmon": ["Chicken of the Sea", "Bumble Bee", "Great Value"],
    "Beef Ravioli": ["Chef Boyardee", "Great Value"], "Spaghetti & Meatballs": ["Chef Boyardee", "Great Value"], "Beefaroni": ["Chef Boyardee"], "Diced Tomatoes": ["Great Value", "Hunt's", "Del Monte", "Red Gold", "Rotel"],
    "Tomato Sauce": ["Hunt's", "Great Value", "Del Monte", "Contadina"], "Tomato Paste": ["Hunt's", "Great Value", "Contadina"], "Crushed Tomatoes": ["Hunt's", "Great Value", "Cento", "Red Gold"], "Pumpkin": ["Libby's", "Great Value"],
    "Pasta Sauce": ["Prego", "Ragu", "Bertolli", "Classico", "Rao's", "Barilla", "Great Value", "Hunt's", "Newman's Own"], "Alfredo Sauce": ["Bertolli", "Classico", "Ragu", "Prego", "Great Value", "Rao's"], "Pizza Sauce": ["Ragu", "Great Value", "Contadina"],
    "Tomato Ketchup": ["Heinz", "Hunt's", "Great Value", "Sir Kensington's"], "Mustard": ["French's", "Heinz", "Grey Poupon", "Great Value"], "Mayonnaise": ["Hellmann's", "Duke's", "Kraft", "Best Foods", "Great Value", "Primal Kitchen"],
    "Salad Dressing": ["Hidden Valley", "Wish-Bone", "Ken's Steak House", "Kraft", "Newman's Own", "Olive Garden", "Great Value", "Marzetti", "Litehouse"], "Barbecue Sauce": ["Sweet Baby Ray's", "KC Masterpiece", "Kraft BBQ", "Stubb's", "Bull's-Eye", "Great Value", "Kinder's"],
    "Hot Sauce": ["Frank's RedHot", "Tabasco", "Cholula", "Texas Pete", "Louisiana", "Tapatio", "Valentina", "Great Value"], "Soy Sauce": ["Kikkoman", "La Choy", "Great Value", "Lee Kum Kee"], "Pickles": ["Vlasic", "Mt. Olive", "Claussen", "Grillo's", "Great Value"],
    "Relish": ["Vlasic", "Heinz", "Mt. Olive", "Great Value"], "Seasoning": ["McCormick", "Lawry's", "Tony Chachere's", "Old Bay", "Badia", "Great Value", "Dan-O's", "Slap Ya Mama", "Mrs. Dash"], "Salt": ["Morton", "Great Value"], "Black Pepper": ["McCormick", "Great Value"],
    "Salsa": ["Pace", "Tostitos", "Herdez", "Chi-Chi's", "Old El Paso", "Great Value"], "Cheese Dip": ["Tostitos", "Ricos", "Great Value", "Pace"], "Potato Chips": ["Lay's", "Ruffles", "Pringles", "Utz", "Cape Cod", "Kettle Brand", "Great Value"],
    "Tortilla Chips": ["Doritos", "Tostitos", "Great Value", "Santitas", "Takis"], "Cheese Puffs": ["Cheetos", "Great Value", "Utz"], "Corn Chips": ["Fritos"], "Rolled Tortilla Chips": ["Takis"], "Stacked Chips": ["Pringles", "Great Value"],
    "Snack Chips Variety Pack": ["Frito-Lay", "Lay's", "Great Value", "Utz"], "Crackers": ["Ritz", "Cheez-It", "Triscuit", "Wheat Thins", "Townhouse", "Club", "Great Value", "Pepperidge Farm"], "Saltine Crackers": ["Premium", "Great Value", "Zesta"],
    "Cheddar Crackers": ["Goldfish", "Cheez-It", "Great Value"], "Graham Crackers": ["Honey Maid", "Great Value", "Keebler"], "Animal Crackers": ["Stauffer's", "Great Value", "Barnum's"], "Sandwich Cookies": ["Oreo", "Great Value", "Hydrox"],
    "Chocolate Chip Cookies": ["Chips Ahoy!", "Great Value", "Keebler", "Pepperidge Farm", "Famous Amos"], "Cookies": ["Nilla", "Nutter Butter", "Fig Newtons", "Keebler", "Pepperidge Farm", "Lorna Doone", "Great Value", "Belvita"],
    "Microwave Popcorn": ["Orville Redenbacher's", "Pop Secret", "Act II", "Great Value"], "Popcorn": ["Smartfood", "Skinny Pop", "Boom Chicka Pop", "Great Value"], "Pretzels": ["Snyder's of Hanover", "Rold Gold", "Utz", "Great Value"],
    "Snack Mix": ["Chex Mix", "Gardetto's", "Great Value", "Munchies"], "Fruit Snacks": ["Welch's", "Mott's", "Betty Crocker", "Annie's", "Great Value"], "Candy Bar": ["Snickers", "Reese's", "Kit Kat", "Hershey's", "Twix", "Milky Way", "3 Musketeers", "Butterfinger"],
    "Share Size Candy": ["Snickers", "Reese's", "M&M's", "Kit Kat", "Twix", "Skittles", "Starburst"], "Chocolate Candy Bag": ["M&M's", "Hershey's", "Reese's", "Kit Kat", "Snickers", "Dove", "Ghirardelli", "Lindt", "Great Value"],
    "Gummy Candy": ["Haribo", "Sour Patch Kids", "Swedish Fish", "Trolli", "Skittles", "Starburst", "Great Value"], "Hard Candy": ["Werther's Original", "Jolly Rancher", "Life Savers", "Brach's", "Great Value"], "Licorice": ["Twizzlers", "Red Vines", "Great Value"],
    "Gum": ["Extra", "Orbit", "Trident", "5 Gum", "Wrigley's"], "Mints": ["Ice Breakers", "Tic Tac", "Altoids", "Mentos"], "Beef Jerky": ["Jack Link's", "Oberto", "Old Trapper", "Great Value"], "Meat Sticks": ["Slim Jim", "Jack Link's", "Great Value"],
    "Milk": ["Great Value", "Fairlife", "Horizon Organic", "Lactaid", "Silk", "Almond Breeze", "Oatly"], "Large White Eggs": ["Great Value", "Eggland's Best", "Marketside"], "Large Brown Eggs": ["Eggland's Best", "Great Value", "Marketside", "Vital Farms"],
    "Shredded Cheese": ["Kraft", "Sargento", "Great Value", "Tillamook"], "Cheese Slices": ["Kraft", "Sargento", "Great Value", "Velveeta", "Borden"], "Cheese Block": ["Great Value", "Cabot", "Tillamook", "Kraft", "Sargento"], "String Cheese": ["Sargento", "Great Value", "Frigo"],
    "Cream Cheese": ["Philadelphia", "Great Value"], "Cottage Cheese": ["Daisy", "Great Value", "Breakstone's"], "Sour Cream": ["Daisy", "Great Value", "Breakstone's"], "Greek Yogurt": ["Chobani", "Oikos", "Fage", "Great Value", "Dannon"],
    "Yogurt": ["Yoplait", "Dannon", "Activia", "Great Value", "Chobani"], "Yogurt Tubes": ["Go-Gurt", "Great Value", "Chobani"], "Salted Butter": ["Land O Lakes", "Great Value", "Kerrygold", "Challenge"], "Unsalted Butter": ["Land O Lakes", "Great Value", "Kerrygold"],
    "Vegetable Oil Spread": ["Country Crock", "I Can't Believe It's Not Butter", "Great Value", "Blue Bonnet"], "Crescent Rolls": ["Pillsbury", "Great Value"], "Cinnamon Rolls": ["Pillsbury", "Great Value"], "Biscuits": ["Pillsbury", "Great Value"],
    "Coffee Creamer": ["Coffee mate", "International Delight", "Great Value", "Chobani"], "Half & Half": ["Great Value", "Land O Lakes", "Organic Valley"], "Heavy Whipping Cream": ["Great Value", "Land O Lakes", "Horizon Organic"],
    "Bacon": ["Great Value", "Oscar Mayer", "Wright", "Smithfield", "Hormel", "Jimmy Dean", "Applegate"], "Beef Franks": ["Ball Park", "Oscar Mayer", "Nathan's Famous", "Hebrew National", "Great Value"], "Hot Dogs": ["Oscar Mayer", "Bar-S", "Great Value", "Ball Park"],
    "Smoked Sausage": ["Hillshire Farm", "Eckrich", "Johnsonville", "Great Value"], "Breakfast Sausage": ["Jimmy Dean", "Johnsonville", "Bob Evans", "Great Value"], "Lunch Meat": ["Oscar Mayer", "Hillshire Farm", "Land O'Frost", "Great Value", "Hormel", "Buddig"],
    "Frozen Pizza": ["DiGiorno", "Red Baron", "Tombstone", "Totino's", "Great Value", "Freschetta", "Jack's", "Celeste"], "Pizza Rolls": ["Totino's", "Great Value"], "Hot Pockets": ["Hot Pockets"], "Frozen Meal": ["Stouffer's", "Marie Callender's", "Lean Cuisine", "Healthy Choice", "Banquet", "Michelina's", "Great Value", "Devour"],
    "Waffles": ["Eggo", "Great Value", "Kodiak Cakes"], "Breakfast Sandwiches": ["Jimmy Dean", "Great Value"], "Ice Cream": ["Breyers", "Blue Bunny", "Great Value", "Edy's", "Turkey Hill", "Friendly's"], "Ice Cream Pint": ["Ben & Jerry's", "Haagen-Dazs", "Talenti", "Halo Top"],
    "French Fries": ["Ore-Ida", "Great Value", "McCain"], "Tater Tots": ["Ore-Ida", "Great Value"], "Chicken Nuggets": ["Tyson", "Great Value", "Perdue"], "Uncrustables": ["Smucker's"], "Frozen Whole Kernel Corn": ["Great Value", "Birds Eye", "Green Giant"],
    "Frozen Vegetables": ["Great Value", "Birds Eye", "Green Giant", "Pictsweet"], "White Bread": ["Great Value", "Wonder", "Sara Lee", "Nature's Own", "Sunbeam"], "Wheat Bread": ["Nature's Own", "Sara Lee", "Great Value", "Oroweat", "Arnold"],
    "Bread": ["Nature's Own", "Sara Lee", "Pepperidge Farm", "Dave's Killer Bread", "Arnold", "Oroweat", "Great Value", "King's Hawaiian"], "Hamburger Buns": ["Great Value", "Ball Park", "Martin's", "Sara Lee", "Nature's Own"], "Hot Dog Buns": ["Great Value", "Ball Park", "Martin's", "Sara Lee"],
    "Flour Tortillas": ["Mission", "Old El Paso", "Great Value", "Guerrero"], "Corn Tortillas": ["Mission", "Guerrero", "Great Value", "La Banderita"], "Bagels": ["Thomas'", "Great Value", "Dave's Killer Bread"], "English Muffins": ["Thomas'", "Great Value"],
    "Snack Cakes": ["Little Debbie", "Hostess", "Tastykake", "Great Value"], "Donuts": ["Entenmann's", "Hostess", "Little Debbie", "Freshness Guaranteed"],
    "Diapers": ["Pampers", "Huggies", "Luvs", "Parent's Choice", "Hello Bello", "Honest"], "Training Pants": ["Pampers", "Huggies", "Parent's Choice"], "Baby Wipes": ["Pampers", "Huggies", "Parent's Choice", "Water Wipes", "Honest"],
    "Infant Formula Powder": ["Similac", "Enfamil", "Parent's Choice", "Gerber", "Earth's Best"], "Ready to Feed Formula": ["Similac", "Enfamil", "Parent's Choice"], "Baby Food Pouch": ["Gerber", "Happy Baby", "Plum Organics", "Parent's Choice", "Earth's Best", "Beech-Nut"],
    "Baby Food Jar": ["Gerber", "Beech-Nut", "Earth's Best", "Parent's Choice"], "Baby Cereal": ["Gerber", "Parent's Choice", "Earth's Best"], "Puffs": ["Gerber", "Happy Baby", "Parent's Choice"],
    "Toilet Paper": ["Charmin", "Angel Soft", "Quilted Northern", "Cottonelle", "Scott", "Great Value"], "Paper Towels": ["Bounty", "Brawny", "Viva", "Sparkle", "Scott", "Great Value"], "Facial Tissues": ["Kleenex", "Puffs", "Great Value"],
    "Liquid Laundry Detergent": ["Tide", "Gain", "Persil", "Arm & Hammer", "Purex", "All", "Xtra", "Great Value"], "Laundry Pods": ["Tide", "Gain", "Persil", "Arm & Hammer", "All", "Great Value"], "Powder Laundry Detergent": ["Tide", "Gain", "Arm & Hammer", "Great Value"],
    "Fabric Softener": ["Downy", "Snuggle", "Gain", "Great Value"], "Dryer Sheets": ["Bounce", "Downy", "Snuggle", "Gain", "Great Value"], "Scent Booster Beads": ["Downy", "Gain", "Great Value"], "Stain Remover": ["Shout", "OxiClean", "Spray 'n Wash", "Resolve", "Tide", "Great Value"],
    "Oxygen Stain Remover Powder": ["OxiClean", "Great Value"], "Bleach": ["Clorox", "Great Value"], "Dish Soap": ["Dawn", "Palmolive", "Ajax", "Great Value", "Method", "Seventh Generation"], "Dishwasher Detergent Pods": ["Cascade", "Finish", "Great Value"],
    "Dishwasher Detergent Gel": ["Cascade", "Finish", "Great Value"], "Rinse Aid": ["Finish", "Cascade"], "Trash Bags": ["Hefty", "Glad", "Great Value"], "Food Storage Bags": ["Ziploc", "Hefty", "Glad", "Great Value"], "Aluminum Foil": ["Reynolds Wrap", "Great Value"],
    "Plastic Wrap": ["Glad", "Reynolds Kitchens", "Great Value"], "Parchment Paper": ["Reynolds Kitchens", "Great Value"], "Wax Paper": ["Reynolds Kitchens", "Great Value"], "Disinfecting Wipes": ["Clorox", "Lysol", "Great Value"], "Disinfectant Spray": ["Lysol", "Clorox"],
    "All Purpose Cleaner": ["Mr. Clean", "Pine-Sol", "Fabuloso", "409", "Lysol", "Clorox", "Method", "Great Value", "Simple Green"], "Glass Cleaner": ["Windex", "Great Value", "Sprayway"], "Bathroom Cleaner": ["Scrubbing Bubbles", "Lysol", "Clorox", "Kaboom", "Comet", "Soft Scrub", "Method"],
    "Toilet Bowl Cleaner": ["Lysol", "Clorox", "Scrubbing Bubbles", "Kaboom", "Great Value"], "Air Freshener": ["Febreze", "Glade", "Air Wick", "Renuzit", "Great Value"], "Sponges": ["Scotch-Brite", "Scrub Daddy", "O-Cedar", "Great Value", "Brillo", "S.O.S"],
    "Floor Cleaner": ["Swiffer", "Bona", "Pine-Sol", "Mr. Clean", "Fabuloso", "Bissell", "Resolve", "Zep"], "Mop": ["Swiffer", "O-Cedar", "Libman", "Rubbermaid", "Bona", "Mainstays"], "Broom": ["O-Cedar", "Libman", "Mainstays", "Rubbermaid", "Quickie"],
    "Insecticide": ["Raid", "Hot Shot", "Off!", "Terro", "Ortho", "Spectracide", "Combat", "Zevo", "Tomcat", "Cutter"], "Light Bulbs": ["GE", "Philips", "Sylvania", "Feit Electric", "Great Value"], "Batteries": ["Duracell", "Energizer", "Rayovac", "Great Value"],
    "Paper Plates": ["Dixie", "Hefty Everyday", "Chinet", "Great Value", "Solo"], "Plastic Cups": ["Solo", "Hefty", "Dixie", "Great Value"], "Plastic Cutlery": ["Hefty", "Dixie", "Great Value", "Solo"], "Napkins": ["Vanity Fair", "Bounty", "Great Value", "Dixie"],
    "Drain Cleaner": ["Drano", "Liquid-Plumr", "Green Gobbler", "Zep"], "Furniture Polish": ["Pledge", "Old English", "Weiman", "Method"], "Carpet Cleaner": ["Resolve", "Bissell", "Woolite", "Folex", "Nature's Miracle", "Rocco & Roxie"],
    "Toothpaste": ["Colgate", "Crest", "Sensodyne", "Arm & Hammer", "Aquafresh", "Equate", "Tom's of Maine"], "Toothbrush": ["Colgate", "Oral-B", "Reach", "Equate", "GUM"], "Mouthwash": ["Listerine", "Scope", "ACT", "Crest", "Colgate", "Equate"],
    "Dental Floss": ["Oral-B", "Glide", "Reach", "Equate"], "Floss Picks": ["Plackers", "Oral-B", "DenTek", "Equate"], "Whitening Strips": ["Crest", "Equate"], "Denture Adhesive Cream": ["Fixodent", "Poligrip", "Equate"],
    "Shampoo": ["Suave", "Head & Shoulders", "Pantene", "Dove", "Garnier Fructis", "Herbal Essences", "TRESemme", "Aussie", "OGX", "Shea Moisture", "Cantu", "Equate", "L'Oreal Paris", "Old Spice", "Selsun Blue"],
    "Conditioner": ["Suave", "Pantene", "Dove", "Garnier Fructis", "Herbal Essences", "TRESemme", "Aussie", "OGX", "Shea Moisture", "Cantu", "Equate"], "2-in-1 Shampoo & Conditioner": ["Suave", "Head & Shoulders", "Pantene", "Old Spice", "Dove", "Equate"],
    "Dry Shampoo": ["Batiste", "Dove", "Not Your Mother's", "TRESemme", "Equate"], "Hair Spray": ["TRESemme", "Aussie", "Got2b", "Suave", "Garnier Fructis", "L'Oreal Paris", "Equate"], "Hair Gel": ["Got2b", "Eco Style", "LA Looks", "Suave", "Cantu", "Equate"],
    "Body Wash": ["Dove", "Old Spice", "Axe", "Irish Spring", "Dial", "Olay", "Caress", "Native", "Dr Teal's", "Method", "Suave", "Equate", "Softsoap"], "Bar Soap": ["Dove", "Irish Spring", "Dial", "Ivory", "Zest", "Lever 2000", "Yardley", "Equate", "Old Spice"],
    "Hand Soap": ["Softsoap", "Dial", "Method", "Mrs. Meyer's", "Equate", "Bath & Body Works"], "Deodorant": ["Secret", "Degree", "Dove", "Old Spice", "Axe", "Gillette", "Speed Stick", "Lady Speed Stick", "Mitchum", "Ban", "Native", "Arm & Hammer Essentials", "Equate"],
    "Maxi Pads": ["Always", "Kotex", "U by Kotex", "Stayfree", "Equate"], "Tampons": ["Tampax", "Playtex", "Kotex", "U by Kotex", "o.b.", "Equate"], "Panty Liners": ["Always", "Carefree", "Kotex", "Equate"], "Feminine Wash": ["Summer's Eve", "Vagisil", "Equate"],
    "Disposable Razors": ["BIC", "Gillette", "Schick", "Venus", "Equate", "Harry's"], "Razor Blade Refills": ["Gillette", "Schick", "Venus", "Equate", "Harry's"], "Razor Handle": ["Gillette", "Schick", "Venus", "Harry's"], "Shaving Cream": ["Barbasol", "Gillette", "Edge", "Skintimate", "Cremo", "Equate"],
    "Facial Cleanser": ["Cetaphil", "CeraVe", "Neutrogena", "Clean & Clear", "St. Ives", "Simple", "Olay", "Garnier", "Bioré", "Pond's", "Noxzema", "Equate"], "Facial Moisturizer": ["CeraVe", "Cetaphil", "Neutrogena", "Olay", "Olay Regenerist", "RoC", "L'Oreal Paris", "Aveeno", "Equate"],
    "Body Lotion": ["Aveeno", "Vaseline", "Jergens", "Eucerin", "Gold Bond", "Lubriderm", "Palmer's", "Nivea", "Curel", "CeraVe", "Cetaphil", "Dove", "Suave", "Equate"], "Hand Cream": ["O'Keeffe's", "Neutrogena", "Eucerin", "Gold Bond", "Aveeno", "Equate"],
    "Sunscreen": ["Banana Boat", "Coppertone", "Hawaiian Tropic", "Sun Bum", "Neutrogena Sun", "Equate"], "Incontinence Underwear": ["Depend", "Always Discreet", "Assurance", "TENA"], "Bladder Control Pads": ["Poise", "Always Discreet", "Assurance", "TENA"],
}
BRAND_HINTS.update(FOOD_HH_HINTS)

# Nouns that only group products; the variant already names the item ("Under Cabinet Light 24 Inch").
UMBRELLA = {"Lamp", "Camping Gear", "Auto Part", "Car Accessory", "Car Care", "Hand Tool", "Kitchen Gadget", "Furniture", "Wall Decor", "Hardware",
            "Paint Supplies", "Fan", "Smart Home Device", "Computer Accessory", "Wearable", "Sports Equipment", "Exercise Equipment", "Christmas Decoration",
            "Halloween Decoration", "Party Supplies", "Party Tableware", "Gift Wrap", "Greeting Card", "Dog Supplies", "Cat Supplies", "Aquarium Supplies",
            "Small Animal Supplies", "Closet Organizer", "Jewelry Set", "Video Game", "Automotive Fluid", "Toy Car", "Book", "Glass Baking Dish", "Notebook",
            "Paper", "Insecticide", "Air Freshener", "Floor Cleaner", "Mop", "Carpet Cleaner", "Vacuum Bags & Filters", "Command Strips", "Tape", "Glue",
            "Toilet Bowl Cleaner", "Bathroom Cleaner", "All Purpose Cleaner", "Glass Cleaner", "Drain Cleaner", "Furniture Polish", "Supplement", "Seasoning",
            "Drink Mix", "Hair Color", "Foundation", "Concealer", "Powder", "Blush", "Eyeshadow Palette", "Eyeliner", "Eyebrow Pencil", "Lipstick", "Lip Gloss",
            "Nail Polish", "Press-On Nails", "Watch", "Charger", "Headphones", "Bluetooth Speaker", "TV", "Laptop", "Tablet", "Prepaid Phone", "Camera", "Bike",
            "Baby Bottles", "Pacifiers", "Sippy Cups", "Infant Car Seat", "Convertible Car Seat", "Stroller", "High Chair", "Baby Monitor", "Bouncer", "Activity Gym",
            "Baby Rattle", "Teether", "Cookware Set", "Knife Set", "Chef Knife", "Coffee Maker", "Blender", "Toaster", "Air Fryer", "Slow Cooker", "Microwave",
            "Sheet Set", "Comforter", "Pillow", "Bath Towel", "Candle", "Area Rug", "Hanger", "Storage Tote", "Trash Can", "Water Bottle", "Tumbler", "Grill",
            "Christmas Lights", "Light Bulbs", "Batteries", "Spray Paint", "Paint", "Motor Oil", "Building Set", "Doll", "Action Figure", "Board Game", "Puzzle",
            "Earrings", "Necklace", "Ring", "Bracelet", "Sports Nutrition", "Wax Strips", "Hair Removal Cream", "Self Tanner", "Sunscreen", "Incontinence Underwear",
            "Bladder Control Pads", "Deodorant", "Bar Soap", "Hand Soap", "Body Wash", "Shampoo", "Conditioner", "2-in-1 Shampoo & Conditioner", "Dry Shampoo",
            "Hair Spray", "Hair Gel", "Hair Oil & Serum", "Leave-In Conditioner", "Toothpaste", "Toothbrush", "Mouthwash", "Dental Floss", "Floss Picks",
            "Whitening Strips", "Facial Cleanser", "Facial Moisturizer", "Acne Treatment", "Body Lotion", "Hand Cream", "Disposable Razors", "Razor Blade Refills",
            "Razor Handle", "Shaving Cream", "Aftershave", "Makeup Remover", "Makeup Wipes", "Setting Spray", "Maxi Pads", "Tampons", "Panty Liners",
            "Liquid Laundry Detergent", "Laundry Pods", "Fabric Softener", "Dryer Sheets", "Scent Booster Beads", "Stain Remover", "Dish Soap", "Dishwasher Detergent Pods",
            "Disinfecting Wipes", "Disinfectant Spray", "Trash Bags", "Food Storage Bags", "Aluminum Foil", "Plastic Wrap", "Parchment Paper", "Wax Paper", "Paper Plates",
            "Plastic Cups", "Plastic Cutlery", "Napkins", "Toilet Paper", "Paper Towels", "Facial Tissues", "Diapers", "Training Pants", "Baby Wipes", "Infant Formula Powder",
            "Cereal", "Cereal Bag", "Soda Pop", "Energy Drink", "Sports Drink", "Water", "Sparkling Water", "Ground Coffee", "Coffee Pods", "Nutrition Shake", "Protein Shake",
            "Frozen Meal", "Frozen Pizza", "Ice Cream", "Ice Cream Pint", "Frozen Vegetables", "Lunch Meat", "Bacon", "Cheese Slices", "Shredded Cheese", "Yogurt", "Greek Yogurt",
            "Pasta Sauce", "Salad Dressing", "Barbecue Sauce", "Hot Sauce", "Pickles", "Potato Chips", "Tortilla Chips", "Crackers", "Cookies", "Sandwich Cookies", "Candy Bar",
            "Chocolate Candy Bag", "Gummy Candy", "Fruit Snacks", "Granola Bars", "Toaster Pastries", "Soup", "Ramen Noodle Soup", "Rice Mix", "Pasta Side", "Cake Mix"}

# share of the catalog per category (roughly Walmart's online mix, food-heavy)
WEIGHTS = {"1": 2.0, "2": 2.5, "3": 2.0, "4": 1.2, "5": 3.5, "6": 4.5, "7": 7.5, "8": 2.5, "9": 6.5, "10": 6.5, "11": 3.5, "12": 2.5,
           "13": 2.5, "14": 6.5, "15": 9.5, "16": 6.0, "17": 4.0, "18": 7.0, "19": 4.0, "20": 3.0, "21": 4.0, "22": 2.0,
           "24": 2.0, "25": 3.5, "26": 1.0, "27": 3.0}
ENDINGS = [0, 12, 24, 36, 44, 47, 48, 56, 64, 67, 74, 76, 84, 86, 88, 92, 94, 96, 97, 98]
COLORS = ["Black", "White", "Gray", "Navy", "Blue", "Red", "Pink", "Teal", "Green", "Beige", "Brown", "Silver", "Gold", "Charcoal", "Ivory", "Burgundy", "Sage", "Blush"]
UNIT_WORD = {"oz": "oz", "fl oz": "fl oz", "lb": "lb", "gal": "Gallon", "l": "Liter", "ml": "ml", "g": "g", "qt": "Quart"}


def clean_variants(vs):
    """Cap runaway variant lists: at most 8 per two-word prefix, 60 per product, deduped, order kept."""
    seen, groups, out = set(), Counter(), []
    for v in vs:
        v = v.strip()
        if v in seen:
            continue
        key = " ".join(v.lower().split()[:2])
        if groups[key] >= 8:
            continue
        groups[key] += 1
        seen.add(v)
        out.append(v)
        if len(out) >= 60:
            break
    return out or [""]


def build_catalog():
    cats = []
    for cid, c in V.CATS.items():
        prods = [(n, k, s, p, u, clean_variants(vs)) for (n, k, s, p, u, vs) in c["products"]]
        store = [b for b in c["brands"] if b in V.STORE]
        other = [b for b in c["brands"] if b not in V.STORE]
        cats.append((cid, c["dept"], c["paths"], store, other, prods, sorted(c["brands"], key=len, reverse=True)))
    return cats


def round_price(raw):
    if raw < 0.5:
        return round(max(0.12, raw), 2)
    dollars = math.floor(raw)
    cents = random.choice(ENDINGS)
    p = dollars + cents / 100
    if p > raw * 1.18 and dollars > 0:
        p = (dollars - 1) + random.choice(ENDINGS[8:]) / 100
    return round(max(p, 0.24), 2)


def brand_prefix(brand):
    h = int(hashlib.md5(brand.encode()).hexdigest(), 16)
    ns = "01367"[h % 5]
    return ns + f"{(h >> 8) % 100000:05d}"


def upc12(prefix, ref):
    body = prefix + f"{ref % 100000:05d}"
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(body)))
    return body + str((10 - total % 10) % 10)


def size_text(kind, size, pack):
    if kind in ("each",):
        return None
    if kind == "ct":
        return f"{int(size)} Count"
    s = f"{size:g}"
    return f"{s} {UNIT_WORD.get(kind, kind)}"


def make_name(brand, variant, noun, kind, size, pack, rng):
    v = (variant + " ") if variant else ""
    container = rng.choice(V.CONTAINERS.get(kind, [""]))
    cont = (" " + container) if container else ""
    if kind == "each":
        tail = ""
        r = rng.random()
        if r < 0.25:
            tail = ", " + rng.choice(COLORS)
        elif r < 0.33:
            tail = " - " + rng.choice(COLORS)
        return f"{brand} {v}{noun}{tail}".strip(), None
    unit = UNIT_WORD.get(kind, kind)
    if kind == "ct":
        if pack > 1:
            return f"{brand} {v}{noun}, {int(size)} Count, {pack} Pack", f"{int(size)} ct"
        r = rng.random()
        if r < 0.6:
            return f"{brand} {v}{noun}, {int(size)} Count", f"{int(size)} ct"
        if r < 0.85:
            return f"{brand} {v}{noun}, {int(size)} ct", f"{int(size)} ct"
        return f"{brand} {v}{noun} ({int(size)} Count)", f"{int(size)} ct"
    s = f"{size:g}"
    r = rng.random()
    if pack > 1:
        if r < 0.35:
            return f"({pack} pack) {brand} {v}{noun}, {s} {unit}", f"{s} {unit}"
        if r < 0.7:
            return f"{brand} {v}{noun}, {s} {unit}, {pack} Pack{(' ' + container + 's') if container else ''}", f"{s} {unit}"
        if r < 0.85:
            return f"{brand} {v}{noun}, {pack} x {s} {unit}", f"{s} {unit}"
        return f"{brand} {v}{noun}, {s} {unit} {container}, Pack of {pack}".replace("  ", " "), f"{s} {unit}"
    if r < 0.55:
        return f"{brand} {v}{noun}, {s} {unit}{cont}", f"{s} {unit}"
    if r < 0.75:
        return f"{brand} {noun} {v.strip()}, {s} {unit}{cont}".replace(" ,", ","), f"{s} {unit}"
    if r < 0.87:
        return f"{brand} {v}{noun} - {s} {unit}", f"{s} {unit}"
    if r < 0.94:
        return f"{brand} {v}{noun} {s}{unit.replace(' ', '')}" if kind in ("oz", "fl oz") else f"{brand} {v}{noun}, {s} {unit}", f"{s} {unit}"
    return f"{brand} {v}{noun}, {s}-{unit}{cont}", f"{s} {unit}"


# Brands that appear in product hints for at least three different products are "umbrella" brands and may be
# assigned to any product in their category; single-product brands (Charmin, Oreo, Cheerios) never leak.
_hint_counts = Counter(b for hints in BRAND_HINTS.values() for b in set(hints))
MULTI_PRODUCT_BRANDS = {b for b, n in _hint_counts.items() if n >= 3} | {"Great Value", "Equate", "Mainstays", "Parent's Choice", "Marketside", "Hyper Tough", "Pen+Gear", "Spring Valley", "Freshness Guaranteed", "Sam's Choice", "Onn.", "Ozark Trail", "Vibrant Life", "Better Homes & Gardens"}


def gen_chunk(args):
    """Generate `n` raw items for seed `seed` and run them through the real normalizer."""
    seed, n, cats, weights, start_id = args
    rng = random.Random(seed)
    random.seed(seed)
    rows, rejects = [], Counter()
    cids = list(weights.keys())
    wts = [weights[c] for c in cids]
    by_cid = {c[0]: c for c in cats}
    recent_upcs = []
    ref_counter = defaultdict(lambda: rng.randint(100, 90000))
    item_id = start_id
    for _ in range(n):
        cid = rng.choices(cids, wts)[0]
        _, dept_id, paths, store, other, prods, _brands_sorted = by_cid[cid]
        noun, kind, sizes, packs, unit_price, variants = rng.choice(prods)
        hint = BRAND_HINTS.get(noun)
        if hint and rng.random() < 0.9:
            brand = rng.choice(hint)
        elif store and rng.random() < 0.45:
            brand = rng.choice(store)
        else:
            # no product-specific hint: only brands that make many kinds of product (never "Charmin Wood Glue")
            pool = [b for b in other if b in MULTI_PRODUCT_BRANDS] or store or other
            brand = rng.choice(pool)
        variant = "" if (rng.random() < 0.12 and noun not in UMBRELLA) else rng.choice(variants)
        # a variant that starts with a known brand name of this category sets the brand ("Fabuloso Lavender ...")
        vl = variant.lower()
        for b in by_cid[cid][6]:
            if vl.startswith(b.lower() + " "):
                brand = b
                variant = variant[len(b):].strip()
                break
        nlow = noun.lower()
        if variant and (noun in UMBRELLA and (nlow in vl or nlow.rstrip("s") in vl)):
            noun_for_name, variant_for_name = variant, ""
        elif variant and noun in UMBRELLA and kind == "each":
            noun_for_name, variant_for_name = variant, ""
        else:
            noun_for_name, variant_for_name = noun, variant
        size = rng.choice(sizes)
        pack = 1 if (len(packs) == 1 or rng.random() < 0.7) else rng.choice([p for p in packs if p != 1] or [1])
        display_brand = "" if noun_for_name.lower().startswith(brand.lower()) else brand
        name, size_field = make_name(display_brand, variant_for_name, noun_for_name, kind, size, pack, rng)
        name = name.strip()
        mult = V.STORE.get(brand, 1.0) * rng.uniform(0.82, 1.22)
        if kind == "each":
            raw = unit_price * mult
        else:
            disc = 1.0 / (1 + 0.12 * math.log1p(max(size, 1) * pack))   # bigger packages cost less per unit
            raw = unit_price * size * pack * mult * disc * (1.6 if kind == "ct" and size < 12 else 1.0)
        price = round_price(raw)
        path = rng.choice(paths)
        top = path.split("/")[1].strip().lower() if "/" in path else ""
        dept = DEPTS.get(DEPT_BY_TOP.get(top, dept_id)) or DEPTS[dept_id]
        item = {"itemId": item_id, "name": name, "brandName": brand, "salePrice": price, "categoryPath": path,
                "marketplace": False, "sellerInfo": "Walmart.com", "availableOnline": rng.random() < 0.9,
                "stock": "Available" if rng.random() < 0.86 else "Not available", "offerType": "ONLINE_AND_STORE"}
        item_id += 1
        r = rng.random()
        if r < 0.92:
            if r < 0.03 and recent_upcs:
                item["upc"] = rng.choice(recent_upcs)                       # same UPC on two listings
            else:
                pfx = brand_prefix(brand)
                ref_counter[brand] += rng.randint(1, 7)
                u = upc12(pfx, ref_counter[brand])
                item["upc"] = ("deleted_" + u) if rng.random() < 0.025 else u
                recent_upcs.append(u)
                if len(recent_upcs) > 400:
                    recent_upcs.pop(0)
        if size_field:
            rs = rng.random()
            if rs < 0.7:
                item["size"] = size_field
            elif rs < 0.82:
                item["size"] = "Each"
            elif rs < 0.9:
                item["size"] = f"{rng.choice([1, 2, 6, 12, 16, 24]):g} oz"
        if rng.random() < 0.015:
            item["clearance"] = True
        elif rng.random() < 0.005:
            item["flashDeal"] = True
        if rng.random() < 0.3:
            item["msrp"] = round(price * rng.uniform(1.0, 1.4), 2)
        row, why = normalize(item, dept, CFG)
        if why:
            rejects[why] += 1
            continue
        rows.append(row)
    return rows, dict(rejects)


def sentinel_rows():
    rows = []
    for i, (name, brand, price, upc, path) in enumerate(SENTINEL_ITEMS):
        top = path.split("/")[1].strip().lower()
        dept = DEPTS[DEPT_BY_TOP[top]]
        item = {"itemId": 900000000 + i, "name": name, "brandName": brand, "salePrice": price, "upc": upc, "categoryPath": path,
                "marketplace": False, "sellerInfo": "Walmart.com", "availableOnline": True, "stock": "Available"}
        row, why = normalize(item, dept, CFG)
        if why:
            raise SystemExit(f"sentinel item rejected ({why}): {name}")
        rows.append(row)
    return rows


def mark_primary(rows):
    """Same rule as crawler/process.py: one primary row per UPC."""
    by_upc = defaultdict(list)
    for r in rows:
        r.pop("primary", None)
        if r.get("upc"):
            by_upc[r["upc"]].append(r)
    for group in by_upc.values():
        group.sort(key=lambda r: ("retired_upc" in r["flags"], r.get("stock") != "Available", "promo_price" in r["flags"], -int(r["id"])))
        group[0]["primary"] = True
    return len(by_upc)


def write_jsonl_gz(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
            n += 1
    return n


def make_equivalents(rows, n_target, seed):
    """Other-store barcodes priced at the closest Walmart item (identify.py output shape)."""
    rng = random.Random(seed + 101)
    other = sorted(OTHER_STORE_BRANDS)
    wm_upcs = {r["upc"] for r in rows if r.get("upc")}
    cands = [r for r in rows if r.get("unit_price") and r.get("base_unit") and r.get("brand") and r["dept"] in ("Food", "Household Essentials", "Personal Care", "Baby", "Pets", "Health and Medicine", "Beauty")]
    out, stats, used = [], Counter(), set()
    for _ in range(n_target):
        r = rng.choice(cands)
        rb = (r["brand"] or "").lower()
        if rb in WALMART_STORE_BRANDS or rng.random() < 0.55:
            brand = rng.choice(other).title().replace("'S", "'s")
            score = rng.uniform(0.5, 0.86)
        else:
            brand = r["brand"]
            score = rng.uniform(0.6, 0.95)
        # scale to a slightly different size most of the time
        f = rng.choice([1, 1, 1, 0.5, 0.75, 1.25, 1.5, 2])
        base = round(r["base_qty"] * f, 4)
        pack = r["pack"] if rng.random() < 0.8 else rng.choice([1, 2, 4, 6])
        core = r["name"]
        if r["brand"] and core.lower().startswith(r["brand"].lower()):
            core = core[len(r["brand"]):].lstrip(" ,-")
        core = core.split(",")[0].strip()
        qty_unit = r["base_unit"] if r["base_unit"] != "ct" else "ct"
        qty = f"{base:g} {qty_unit}" if qty_unit != "ct" else f"{int(base)} ct"
        name = f"{brand} {core}"
        while True:
            pfx = brand_prefix(brand + "x")
            u = upc12(pfx, rng.randint(1, 99999))
            key = gtin14(u)[0]
            if key not in wm_upcs and key not in used:
                used.add(key)
                break
        price = round(r["unit_price"] * base * pack, 2)
        conf = "high" if score >= 0.7 else "medium" if score >= 0.55 else "low"
        stats[f"matched_{conf}"] += 1
        out.append({"upc": key, "name": name, "brand": brand, "quantity": qty, "base_qty": base, "base_unit": r["base_unit"],
                    "pack": pack, "est_price": max(price, 0.12), "basis_id": r["id"], "basis_name": r["name"], "basis_price": r["price"],
                    "confidence": conf, "score": round(score, 3)})
    return out, dict(stats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "app" / "build" / "fixture-store"))
    ap.add_argument("--items", type=int, default=760_000)
    ap.add_argument("--equivalents", type=int, default=60_000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    t0 = time.time()
    store = Path(a.store)
    cats = build_catalog()
    total_w = sum(WEIGHTS.values())
    weights = {k: v / total_w for k, v in WEIGHTS.items()}

    rows = sentinel_rows()
    rejects = Counter()
    # generate in rounds until the target is reached (duplicate names are dropped, so rounds vary in yield)
    target = a.items + len(SENTINEL_ITEMS)
    chunk, start, job_no = 20_000, 10_000_000, 0
    seen_names = {r["name"].lower() for r in rows}
    with Pool(a.workers) as pool:
        while len(rows) < target:
            need = target - len(rows)
            n_jobs = max(1, min(3 * a.workers, math.ceil(need * 1.3 / chunk)))
            jobs = []
            for _ in range(n_jobs):
                jobs.append((a.seed * 1000 + job_no, chunk, cats, weights, start))
                start += chunk; job_no += 1
            for got, rej in pool.imap_unordered(gen_chunk, jobs):
                rejects.update(rej)
                for r in got:
                    k = r["name"].lower()
                    if k in seen_names:
                        rejects["duplicate_name"] += 1
                        continue
                    seen_names.add(k)
                    rows.append(r)
                print(f"  {len(rows):,} rows kept  ({time.time() - t0:.0f}s)", end="\r", flush=True)
            if job_no > 400:
                raise SystemExit("name space exhausted before reaching the target; add vocabulary")
    rows = rows[: a.items + len(SENTINEL_ITEMS)]
    print(f"\ngenerated {len(rows):,} rows; rejects: {dict(rejects)}")

    upcs = mark_primary(rows)
    rows.sort(key=lambda r: int(r["id"]))
    pub = store / "build" / "published"
    n = write_jsonl_gz(pub / "items.jsonl.gz", rows)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # The version is a hash of everything that shapes the fixture, so rebuilding unchanged inputs yields the
    # same snapshot version and phones that already have it download nothing.
    h = hashlib.sha1()
    for f in [Path(__file__), Path(__file__).with_name("fixture_vocab.py"), Path(__file__).with_name("sentinel_items.py"),
              ROOT / "crawler" / "normalize.py", ROOT / "crawler" / "identify.py", ROOT / "data" / "categories.json", ROOT / "data" / "sentinels.json"]:
        h.update(f.read_bytes() if f.exists() else b"")
    h.update(str(args.items).encode()); h.update(str(args.seed).encode() if hasattr(args, "seed") else b"")
    run_id = "fixture-" + h.hexdigest()[:10]
    stats = {"built": stamp, "run_id": run_id, "plan": "full", "items": n, "upcs": upcs, "carried_over": 0,
             "raw_by_department": dict(Counter(r["dept"] for r in rows)),
             "kept_by_category": dict(Counter(r["cat"] for r in rows)), "kept_by_department": dict(Counter(r["dept"] for r in rows)),
             "rejects_by_department": {"all": dict(rejects)}, "flags": dict(Counter(f for r in rows for f in r["flags"])),
             "upc_price_conflicts": 0, "upc_price_conflict_examples": [], "fixture": True}
    (pub / "stats.json").write_text(json.dumps(stats, indent=2, sort_keys=True))
    manifest = {"version": run_id, "published": stamp, "items": n, "upcs": upcs, "gates_passed": True, "approved_manually": False,
                "file": "items.jsonl.gz", "fixture": True,
                "note": "SYNTHETIC FIXTURE for app development and performance proof. Not real prices."}
    (pub / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))

    eq, eq_stats = make_equivalents(rows, a.equivalents, a.seed)
    write_jsonl_gz(store / "identify" / "equivalents.jsonl.gz", eq)
    (store / "identify" / "equivalents_stats.json").write_text(json.dumps(eq_stats, indent=2, sort_keys=True))
    (store / "state").mkdir(exist_ok=True)
    (store / "state" / "run.json").write_text(json.dumps({"run_id": run_id, "plan": "full", "status": "published", "fixture": True}, indent=2))
    print(f"wrote {n:,} items, {upcs:,} UPCs, {len(eq):,} equivalents to {store} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
