"""Turn a raw Walmart item into a clean, searchable, priced row — or reject it with a reason.

Rules are deterministic and unit-tested (tests/test_normalize.py). Product name is the primary
source for size and pack because Walmart's `size` field is often wrong ("Each", "2", wrong oz).
"""
import re

from . import classify

UNIT_ALIASES = {
    "fl oz": "fl oz", "fl. oz": "fl oz", "fl.oz": "fl oz", "floz": "fl oz", "fluid ounce": "fl oz", "fluid ounces": "fl oz",
    "oz": "oz", "ounce": "oz", "ounces": "oz", "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "g": "g", "gram": "g", "grams": "g", "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml", "l": "l", "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "gal": "gal", "gallon": "gal", "gallons": "gal", "qt": "qt", "quart": "qt", "quarts": "qt", "pt": "pt", "pint": "pt", "pints": "pt",
    # abbreviations Walmart's truncated feed names use: "16.9 Fo", "22 Fz", "104 Gm", "150 grs", "1.5 Lt"
    "fz": "fl oz", "fo": "fl oz", "gm": "g", "gms": "g", "gr": "g", "grs": "g", "lt": "l", "ltr": "l", "ltrs": "l",
}
# convert to base: weight -> oz, volume -> fl oz
TO_BASE = {"oz": ("oz", 1), "lb": ("oz", 16), "g": ("oz", 0.035274), "kg": ("oz", 35.274),
           "fl oz": ("fl oz", 1), "ml": ("fl oz", 0.033814), "l": ("fl oz", 33.814), "gal": ("fl oz", 128),
           "qt": ("fl oz", 32), "pt": ("fl oz", 16), "ct": ("ct", 1)}

_UNIT_RX = (r"(fl\.?\s?oz|fluid\s+ounces?|fz|fo|ounces?|oz|lbs?|pounds?|kilograms?|kg|grams?|gms?|grs?|g|milliliters?|ml|"
            r"liters?|litres?|ltrs?|lt|l|gallons?|gal|quarts?|qt|pints?|pt)")
QTY = re.compile(r"(?<![\w.])(?<![a-z]-)(\d+(?:\.\d+)?|\.\d+)\s*-?\s*" + _UNIT_RX + r"(?![a-z])", re.I)   # not "FC-600L"
# a proper fraction of a unit: "1/2 oz", "1 1/2oz", "3/4 LT" (only halves, thirds, quarters and eighths: "6/16fo" is a pack)
FRACTION = re.compile(r"(?<![\w./])(?:(\d+)[\s-]+)?([1-7])/([2348])(?=\s*-?\s*" + _UNIT_RX + r"(?![a-z]))", re.I)
MULTI = re.compile(r"(?<![\w.])(\d+)\s*(?:x|-|×)\s*(\d+(?:\.\d+)?)\s*-?\s*" + _UNIT_RX + r"(?![a-z])", re.I)
PACK = [
    re.compile(r"\((\d+)\s*(?:-\s*)?(?:pack|pk|count|ct)\)", re.I),
    re.compile(r"(?<![\w.])(\d+)\s*-?\s*(?:pack|pk|packs)\b", re.I),
    re.compile(r"\b(?:pack|case|box|set)\s+of\s+(\d+)\b", re.I),
]
COUNT = re.compile(r"(?<![\w.])(\d+)\s*-?\s*(?:count|ct|cnt)\b\.?", re.I)
# extended counts, used only when neither the name nor the size field states a weight or volume:
# "20 Tea Bags", "12 Bars", "40 K-Cup Pods", "100 Each", "42 pc", "18 Packets", "24 Stems"
COUNT_EXT = re.compile(r"(?<![\w.])(\d+)\s*-?\s*(?:count|ct|cnt|ea|each|pcs?|pieces?|(?:tea\s+)?bags?|teabags|bg|bars?|"
                       r"(?:k-?cup\s+)?pods?|k-?cups?|capsules?|packets?|sticks?|sachets?|pouches|bottles?|cans|"
                       r"servings?|svgs|sheets?|drinks?|stems?|candles?)\b\.?", re.I)
# containers that multiply a stated weight or volume into a pack: "4 oz, 8 Bars", "0.5 oz, 12 Packets"
PACK_NOUNS = re.compile(r"(?<![\w.])(\d+)\s*-?\s*(?:count|ct|cnt|bars?|bottles?|cans|pouches|packets?|(?:k-?cup\s+)?pods?|"
                        r"k-?cups?|capsules?|sticks?|sachets?)\b\.?", re.I)
TOTAL = re.compile(r"(?<![\w.])(\d+)\s+total(?:\s+(?:count|ct|pieces?|pcs|wipes|packets?|pods|k-?cups|bars|bags|sticks|"
                   r"servings|capsules|cups|units?|drinks)\b|(?!\s*[a-z]))", re.I)      # "(144 Total Pieces)", "270 Total"
OF_EACH = re.compile(r"(?<![\w.])(\d+)\s*(?:packs?|boxes|bags|cartons|cases|pk)\s+(?:of|with)\s+(\d+)\b", re.I)
WRAPPER = re.compile(r"^\s*\((\d+)\s*pack\)", re.I)       # Walmart's multipack listing: "(6 pack) <one unit's name>"
DOZEN = re.compile(r"\b(?:(\d+|a|one|two|three|four|five|six)\s+)?dozen\b", re.I)
POUND_SIGN = re.compile(r"(?<![\w.#])(\d+(?:\.\d+)?)#(?![\w#])")                  # "Strawberries 1#" = 1 lb
BARE_VOLUME = re.compile(r"\b(half[\s-]+gallon|gallon|quart|pint)\b(?!\s+glass)", re.I)  # "Eggnog, Quart"
WORD_NUM = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "eleven": 11, "twelve": 12}
WORD_QTY = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?=(?:pounds?|lbs?|ounces?|"
                      r"gallons?|liters?|litres?)\b)", re.I)                    # not "two pint glasses"
# feed shorthands rewritten before parsing: "24. OZ", "16 Fl O" cut off at 40 characters, "27.4ozx6", "1 Fl Dram" (1/8 fl oz)
REWRITES = [
    (re.compile(r"(?<![\w.])([1-9]\d*)\.\s+(oz|fl)\b", re.I), lambda m: f"{m.group(1)} {m.group(2)}"),
    (re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*fl(?:\s*o)?\s*$", re.I), lambda m: f"{m.group(1)} fl oz"),
    # "28.2ozx14" is the supplier's case count; Walmart prices one box ($3-8 measured on the live crawl): size only
    (re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(oz|fl\s?oz)x\d+\b", re.I), lambda m: f"{m.group(1)} {m.group(2)}"),
    (re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:fl\.?\s*)?drams?\b", re.I), lambda m: f"{float(m.group(1)) / 8:g} fl oz"),
    (re.compile(r"(?<![\w.])(\d+)\s*Co(?:u|un)?\s*$", re.I), lambda m: f"{m.group(1)} Count"),   # "36 Co" cut at 40 chars
    # a body-weight range or a load rating is never the net quantity: "Diaper L 22-37 lbs" is not 22 x 37 lb, "Sling
    # Straps, 450 lb. Weight Capacity" does not weigh 450 lb
    (re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s*(?:-|\u2013|to)\s*\d+(?:\.\d+)?\s*(?:lbs?|pounds?)\b\.?", re.I), lambda m: " "),
    (re.compile(r"\b(?:up\s+to|holds?|supports?|capacity(?:\s+of)?|max(?:imum)?(?:\s+weight)?(?:\s+of)?)\s+\d+(?:\.\d+)?\s*"
                r"(?:lbs?|pounds?)\b\.?|(?<![\w.])\d+(?:\.\d+)?\s*(?:lbs?|pounds?)\.?\s*(?:weight\s+)?(?:capacity|max(?:imum)?|"
                r"limit|rated|rating)\b", re.I), lambda m: " "),
]
# "11.5z" for oz is read only in the extended pass (a stated size anywhere wins) and never above 200: "Nissan 350z"
Z_OUNCES = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d+)?)z\b", re.I)
Z_MAX = 200
LITRE_MAX = 10      # "1.5 Lt" is litres; "46 LT" is a hair-colour shade ("light")
LITRE_L_MAX = 25    # "20 L" water jugs exist; "600l" does not
# a name cut off inside its pack count ("Gefen Pink Salmon, 14.75 Oz, (pack", "Hapi Crackers, 6 Oz. (pac"): the price is
# for a case of unknown size, so the usual case counts are offered to process.resolve_packs()
TRUNCATED_PACK_RX = re.compile(r"\(\s*(?:p(?:a(?:c(?:k(?:\s+(?:o(?:f)?)?)?)?)?)?|c(?:a(?:s(?:e(?:\s+(?:o(?:f)?)?)?)?)?)?)?\s*$", re.I)
CASE_COUNTS = (2, 3, 4, 6, 8, 10, 12, 15, 16, 18, 20, 24, 30, 32, 36, 40, 48, 50, 60, 64, 72, 96, 100, 144)
NUTRIENT_AFTER = re.compile(r"\s*(?:of\s+)?(?:plant[- ]based\s+|added\s+|total\s+|net\s+)?(?:protein|fib(?:er|re)|sugars?|carbs?|"
                            r"carbohydrates?|fat|caffeine|collagen|whole\s+grains?|omega|bcaas?|electrolytes?)\b", re.I)
GRAM_ABBR_MIN = 10  # "165gr", "45 GM" are grams; "7GM" is a hair-colour shade (golden mahogany)
# sold per piece: the price is for one item and no net quantity applies (produce "each", store cakes, gifts, flowers)
EACH_RX = re.compile(r"(?:,|-|\()\s*(?:1\s+)?(?:each|ea)\s*\)?\s*$|\bper\s+each\b|\bsold\s+(?:by\s+the\s+)?each\b", re.I)
EACH_SIZE = {"each", "ea", "1ea", "1 ea", "1 each", "1 gift", "one gift", "1 bouquet", "1 cake", "1 plant"}
EACH_PATHS = ("/produce/", "fresh produce", "/fresh fruit", "/fresh vegetables", "flower shop", "/food gifts",
              "fruit & nut gifts", "coffee, cocoa, & tea gifts", "/cakes/", "custom cakes", "easter food gifts",
              "easter candy baskets")      # cake decorations count only by name (toppers, candles, kits), never by path
EACH_WORDS = re.compile(r"\b(?:gift\s+(?:basket|set|box|tower|tin|bag|crate)|basket|bouquet|cake\s+topper|toppers?|"
                        r"candles?|bonsai|live\s+plant|sheet\s+cake|smash\s+cake|bundt\s+cake|cupcake\s+cake|"
                        r"decorating\s+(?:kit|set)|cookie\s+cutters?|serving\s+(?:board|tray|pedestal)|cake\s+stand)\b", re.I)
PER_LB = re.compile(r"(?:per|/)\s*(?:lb|pound)\b|\bsold by (?:the )?(?:lb|pound|weight)\b", re.I)

VARIANT_WORDS = [
    "diet", "zero sugar", "zero", "sugar free", "sugar-free", "caffeine free", "decaf", "low sodium", "reduced sodium",
    "no salt added", "unsalted", "organic", "gluten free", "gluten-free", "whole grain", "whole wheat", "reduced fat",
    "fat free", "low fat", "2%", "1%", "skim", "whole milk", "lactose free", "light", "lite", "original", "classic",
    "creamy", "crunchy", "chunky", "extra crunchy", "natural", "unsweetened", "sweetened", "spicy", "mild", "hot",
    "regular", "family size", "party size", "king size", "variety pack", "sensitive", "unscented", "fragrance free",
    "infant", "toddler", "kids", "adult", "extra strength", "maximum strength", "children's",
]
STORE_BRANDS = {"great value", "equate", "mainstays", "parent's choice", "marketside", "freshness guaranteed",
                "sam's choice", "bettergoods", "ol' roy", "special kitty", "pure balance", "pen+gear", "hyper tough",
                "onn.", "spring valley", "clear american", "prima della", "member's mark", "time and tru"}


def gtin14(upc):
    """Normalize any UPC/EAN to a 14-digit key. Returns (key, retired, check_ok) or (None, retired, False)."""
    if not upc:
        return None, False, False
    s = str(upc)
    retired = s.lower().startswith("deleted_")
    digits = re.sub(r"\D", "", s)
    if not digits or len(digits) > 14:
        return None, retired, False
    if len(digits) == 11:                      # UPC-A missing its check digit
        digits += str(_check_digit(digits))
    key = digits.zfill(14)
    ok = int(key[-1]) == _check_digit(key[:-1])
    return key, retired, ok


def _check_digit(body: str) -> int:
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(body)))
    return (10 - total % 10) % 10


def _unit(u: str) -> str:
    u = re.sub(r"\s+", " ", u.lower().replace(".", "")).strip()
    u = u.replace("fl oz", "fl oz")
    if u.startswith("fl"):
        return "fl oz"
    return UNIT_ALIASES.get(u, UNIT_ALIASES.get(u.rstrip("s"), u))


def _fraction(m) -> str:
    whole = int(m.group(1) or 0)
    if int(m.group(2)) >= int(m.group(3)):
        return m.group(0)
    return f"{whole + int(m.group(2)) / int(m.group(3)):g}"


def _plausible(q) -> bool:
    """Reject numbers that cannot be the stated quantity: zero, and abbreviations that collide with shade codes."""
    n, u = float(q.group(1)), q.group(2).lower()
    if n <= 0:
        return False
    if u.startswith("lt") and n > LITRE_MAX:
        return False
    if u == "l" and n > LITRE_L_MAX:
        return False                                    # "600l" is a model number, not 600 litres
    if u in ("gm", "gms", "gr", "grs") and n < GRAM_ABBR_MIN:
        return False
    if _unit(u) == "g" and NUTRIENT_AFTER.match(q.string, q.end()):
        return False                                    # "10g Protein", "18g of Protein", "5g Fiber": not the net weight
    return True


def parse_quantity(text: str, extended: bool = True):
    """Return (size, unit, pack) from free text. pack is None when not stated.

    The basic pass reads a weight or volume ("29 oz", "1.5 Lt", "Two Pounds", "1#") or a plain count ("24 ct").
    With extended=True, when that finds nothing, count nouns ("20 Tea Bags", "12 Bars", "2 Dozen") and a bare
    "Quart" / "Pint" / "Half Gallon" are read as well. normalize() tries the size field's basic pass before the
    name's extended pass, so a stated weight always beats a piece count."""
    if not text:
        return None, None, None
    t = text.replace("\u00d7", "x")
    t = WORD_QTY.sub(lambda m: f"{WORD_NUM[m.group(1).lower()]} ", t)          # "Two Pounds" -> "2 Pounds"
    t = POUND_SIGN.sub(lambda m: f"{m.group(1)} lb", t)                         # "1#" -> "1 lb"
    t = FRACTION.sub(lambda m: _fraction(m), t)                                  # "1 1/2oz" -> "1.5oz"
    for rx, fn in REWRITES:
        t = rx.sub(fn, t)
    if extended:
        t = Z_OUNCES.sub(lambda m: f"{m.group(1)} oz" if float(m.group(1)) <= Z_MAX else m.group(0), t)
    pack = None
    m = MULTI.search(t)
    if m:
        return float(m.group(2)), _unit(m.group(3)), int(m.group(1))
    wrapper = WRAPPER.match(t)
    wrapped = bool(wrapper and int(wrapper.group(1)) > 0)
    pack_span = None
    for rx in PACK:
        pm = next((x for x in rx.finditer(t) if int(x.group(1)) > 0), None)   # "(0 pack)" is a feed artifact
        if pm:
            pack, pack_span = int(pm.group(1)), pm.span(); break
    sizes = [(float(q.group(1)), _unit(q.group(2))) for q in QTY.finditer(t) if _plausible(q)]
    # prefer metric-free US unit if both "11 oz (312 g)" present: first mention wins
    size, unit = (sizes[0] if sizes else (None, None))
    if size is not None:
        if pack is None:
            c = (PACK_NOUNS if extended else COUNT).search(t)
            if c and unit != "ct" and int(c.group(1)) > 0:
                pack = int(c.group(1))
        return size, unit, pack
    if not extended:
        # the long-standing reading: a plain count is the size only when no pack is stated beside it, so a pack's
        # size comes from the size field ("(12 Count)" drinks of "12 oz")
        c = COUNT.search(t)
        if c and pack is None and int(c.group(1)) > 0:
            return float(c.group(1)), "ct", None
        return None, None, pack
    for rx in (COUNT, COUNT_EXT):
        total = TOTAL.search(t)
        if total and rx is COUNT_EXT:
            # the stated total already includes inner packs; under a "(6 pack)" wrapper it is one unit's total
            return float(total.group(1)), "ct", (pack if wrapped else None)
        c = rx.search(t)
        if c and int(c.group(1)) > 0:
            n = int(c.group(1))
            if pack_span and pack_span[0] <= c.start() < pack_span[1]:
                # "(20 Count)" is the count, not a pack as well (this pass runs only when no weight or volume is
                # stated anywhere, so it is 20 pieces)
                if rx is COUNT:
                    return float(n), "ct", None
                pack = None
            if total and int(total.group(1)) == n and not wrapped:
                return float(n), "ct", None
            of = None if wrapped else OF_EACH.search(t)
            if of and int(of.group(1)) * int(of.group(2)) == n:
                return float(n), "ct", None                                    # "108 Count (6 Packs of 18)": n is the total
            return float(n), "ct", pack
    if extended:
        d = DOZEN.search(t)
        if d:
            k = d.group(1)
            return float(12 * (int(k) if k and k.isdigit() else WORD_NUM.get((k or "a").lower(), 1))), "ct", pack
        bare = BARE_VOLUME.search(t)
        if bare:
            word = re.sub(r"[\s-]+", " ", bare.group(1).lower())
            size, unit = (0.5, "gal") if word == "half gallon" else (1.0, _unit(word))
            if pack is None:
                c = PACK_NOUNS.search(t)
                pack = int(c.group(1)) if c and int(c.group(1)) > 0 else None
            return size, unit, pack
    return None, None, pack


PER_CONTAINER = re.compile(r"(?<![\w.])(\d+)\s*/\s*(?:carton|case|box|bx|cs|ctn|bag|pack|pk|pallet|plt)\b", re.I)   # "36/Carton", "2016/Pallet"
# further pack forms the feed uses, read only as candidates for process.build(): "15/12oz" (15 x 12 oz), "120pcspk",
# "24 Case", "12/" at the end, "Pack of, 12"
PACK_HINTS = [
    re.compile(r"(?<![\w./])(\d+)\s*/\s*\d+(?:\.\d+)?\s*-?\s*" + _UNIT_RX + r"(?![a-z])", re.I),
    re.compile(r"(?<![\w.])(\d+)\s*pcs?(?=[a-z])", re.I),
    re.compile(r"(?<![\w.])(\d+)\s*(?:case|cs|ctn|carton)\b", re.I),
    re.compile(r"(?<![\w./])(\d+)\s*/\s*$"),
    re.compile(r"\bpack\s+of,?\s*(\d+)\b", re.I),
    # inner counts with a word or two between the number and the container: "12 Snack Bars", "25 Individual Snack
    # Packs", "18 Powder Packet", "10 Popcorn Bags", "6 Count Packets", and containers PACK_NOUNS leaves out
    re.compile(r"(?<![\w.])(\d+)\s+(?:[a-z-]+\s+){0,2}(?:bars|cups|packs|packets?|packages|pouches|bags|sticks|stick\s?packs|"
               r"pods|bottles|cans|boxes|tubs|jars|cartons|envelopes|sleeves|servings|pieces|rolls|tins|bites|wraps)\b", re.I),
    re.compile(r"\b(?:carton|box|case|bag|tray|bundle|inner\s*pack|innerpack|set)\s+of\s+(\d+)\b", re.I),
    re.compile(r"(?<![\w.])(\d+)\s*-?\s*(?:pieces?|pcs?|count|ct)\s*/\s*(?:carton|case|box|bag|pack)\b", re.I),
    re.compile(r"(?<![\w.])(\d+)P\b"),                      # POS abbreviation: "BF MAYO GARLIC 72P 1.2Z"
]
# "(6x5 Ct)": six boxes of five, offered as both 5 and 30
MULTI_COUNT = re.compile(r"(?<![\w.])(\d+)\s*x\s*(\d+)\s*(?:ct|count|pk|pack|pcs?)\b", re.I)
PACK_MAX = 5000            # "2016/Pallet" is real


def pack_options(text: str):
    """Every pack count the text supports beside a stated weight or volume: 1 (the size is the whole listing), a
    "(6 pack)" wrapper, "Pack of 12", a piece count ("12 Count", "3 Packets", "(24 Cans)", "36/Carton") and the wrapper
    times an inner count. The name alone cannot say which one Walmart's price is for ("Pop-Tarts 58.6 oz, 32 Count" is
    one box; "KIND 1.4oz, 12 Count" is twelve bars); process.build() picks the reading that agrees with the category's
    unambiguous rows when the default reading is more than 10x off them."""
    t = (text or "").replace("\u00d7", "x")
    found, wrapper = set(), None
    w = WRAPPER.match(t)
    if w and 0 < int(w.group(1)) <= PACK_MAX:
        wrapper = int(w.group(1))
    for rx in (*PACK, PACK_NOUNS, COUNT_EXT, PER_CONTAINER, TOTAL, *PACK_HINTS):
        for m in rx.finditer(t):
            n = int(m.group(1))
            if 1 < n <= PACK_MAX:
                found.add(n)
    for m in MULTI_COUNT.finditer(t):
        a, b = int(m.group(1)), int(m.group(2))
        found |= {n for n in (a, b, a * b) if 1 < n <= PACK_MAX}
    if DOZEN.search(t):
        found.add(12)
    opts = {1} | found
    if wrapper:
        opts |= {wrapper * n for n in found if n != wrapper and wrapper * n <= PACK_MAX}
    return sorted(opts)


def sold_each(name: str, size_field, path) -> bool:
    """True when the listing is priced per piece with no net quantity to state: produce sold each, store-made cakes,
    gift baskets, flowers and plants, cake toppers and candles. Such a row is sized by its basis (one item), not a
    parse failure; packaged goods whose size is simply missing from the name are never matched here."""
    if EACH_RX.search(name or ""):
        return True
    sf = re.sub(r"\s+", " ", str(size_field or "")).strip().lower()
    if sf in EACH_SIZE:
        return True
    p = (path or "").lower()
    return any(k in p for k in EACH_PATHS) or bool(EACH_WORDS.search(name or ""))


def to_base(size, unit):
    if size is None or unit not in TO_BASE:
        return None, None
    base, f = TO_BASE[unit]
    return round(size * f, 4), base


def variants(name: str):
    n = name.lower()
    return sorted({w for w in VARIANT_WORDS if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", n)})


def junk_reason(item: dict, dept_name: str, cfg: dict):
    name = (item.get("name") or "").strip()
    path = (item.get("categoryPath") or "").lower()
    if not name or name in {"-", "."}:
        return "no_name"
    if item.get("marketplace") is True:
        return "marketplace"
    seller = item.get("sellerInfo")
    if seller and seller.strip().lower() != "walmart.com":
        return "third_party_seller"
    if not isinstance(item.get("salePrice"), (int, float)) or item["salePrice"] <= 0:
        return "no_price"
    for kw in cfg.get("exclude_path_keywords", []):
        if kw in path:
            return "excluded_category"
    # not carried at all: apparel, footwear, pet beds, alcohol, tobacco, media (docs/CATEGORIES.md)
    why = classify.exclusion(name, item.get("brandName"), item.get("categoryPath"), dept_name, item.get("upc"))
    if why:
        return why
    if dept_name == "Food" and not item.get("upc") and parse_quantity(name)[0] is None and not item.get("size"):
        return "food_without_upc_or_size"
    return None


def category(item: dict, dept: dict, cfg: dict) -> str:
    """Store category id (string) from the name and path alone; process.build() refines it with path statistics."""
    name, _ = classify.clean_name(item.get("name") or "")
    return str(classify.category(name, item.get("brandName"), item.get("categoryPath"), dept, cfg))


def normalize(item: dict, dept: dict, cfg: dict):
    """Return (row, None) for a kept item, or (None, reason) for a rejected one."""
    reason = junk_reason(item, dept["name"], cfg)
    if reason:
        return None, reason
    raw_name = re.sub(r"\s+", " ", item["name"]).strip()
    name, discontinued = classify.clean_name(raw_name)
    is_placeholder = classify.placeholder(raw_name, item.get("brandName"), item.get("salePrice"))
    key, retired, check_ok = gtin14(item.get("upc"))
    if is_placeholder and not (key and check_ok and not retired):
        return None, "placeholder_no_barcode"     # a placeholder is kept only for barcode lookup, so it needs a valid barcode
    # a stated weight or volume (name first, then the size field) beats a piece count or a bare "Pint"
    size, unit, pack = parse_quantity(name, extended=False)
    flags = []
    src = "name"
    fs, fu, fp = parse_quantity(item.get("size") or "", extended=False)
    if size is None and fs is None:
        size, unit, pack = parse_quantity(name)
        if size is None:
            fs, fu, fp = parse_quantity(item.get("size") or "")
    if size is None and fs is not None:
        size, unit, src = fs, fu, "size_field"
    elif size is not None and fs is not None:
        b1, d1 = to_base(size, unit); b2, d2 = to_base(fs, fu)
        if d1 == d2 and b1 and b2 and abs(b1 - b2) / max(b1, b2) > 0.05 and abs(b1 - b2 * (pack or 1)) / max(b1, 1e-9) > 0.05:
            flags.append("size_conflict")
    if pack is None:
        pack = fp or 1
    price = round(float(item["salePrice"]), 2)
    basis = "lb" if PER_LB.search(name) or PER_LB.search(item.get("size") or "") else "each"
    base, dim = to_base(size, unit)
    nn = classify.noun(name, item.get("categoryPath"), dept, cfg)
    # per-unit prices only for consumables (docs/DECISIONS.md, 2026-10-08): not in durable-goods departments, not for a durable good
    # inside a consumable department (a Fitbit weighs 0.28 oz), not for a single piece (its "unit price" is its price),
    # and not for a placeholder listing
    single_piece = dim == "ct" and base and base * (pack or 1) == 1
    per_unit = bool(base and pack and dept.get("consumable", True) and not is_placeholder and not single_piece
                    and not classify.durable(name, nn))
    unit_price = round(price / (base * pack), 4) if per_unit else None
    options = pack_options(name) if per_unit else []
    if per_unit and TRUNCATED_PACK_RX.search(raw_name):
        options = sorted(set(options) | {1} | set(CASE_COUNTS))
        flags.append("pack_truncated")
    if pack not in options:
        options = sorted(set(options) | {pack})
    if size is None:
        # sized by its basis instead: sold by weight (basis "lb") or sold per piece (flag "sold_each")
        if basis == "each" and sold_each(name, item.get("size"), item.get("categoryPath")):
            flags.append("sold_each")
        flags.append("no_size")
    if retired:
        flags.append("retired_upc")
    if key and not check_ok:
        flags.append("upc_check_digit")
    if any(item.get(k) for k in ("clearance", "flashDeal", "limitedTimeDeal")):
        flags.append("promo_price")
    if is_placeholder:
        flags.append("placeholder")               # barcode lookup only: kept out of typed search and the size-parse rate
    if discontinued:
        flags.append("discontinued")
    brand = item.get("brandName")
    row = {
        "id": item["itemId"], "upc": key, "name": name, "brand": brand,
        "size": size, "unit": unit, "pack": pack, "base_qty": base, "base_unit": dim,
        "price": price, "unit_price": unit_price, "basis": basis,
        "cat": str(classify.decide(nn, item.get("categoryPath"), dept, cfg, None, name)), "dept": dept["name"],
        "path": item.get("categoryPath"), "variants": variants(name),
        "store_brand": bool(brand and brand.strip().lower() in STORE_BRANDS),
        "stock": item.get("stock"), "online": item.get("availableOnline"),
        "offer": item.get("offerType"), "size_src": src, "flags": flags,
    }
    if len(options) > 1:
        row["pack_options"] = options          # resolved and removed by process.build()
    if nn:
        row["noun"] = list(nn)                 # the name's category evidence; process.build() decides with path stats
    return row, None
