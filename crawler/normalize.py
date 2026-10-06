"""Turn a raw Walmart item into a clean, searchable, priced row — or reject it with a reason.

Rules are deterministic and unit-tested (tests/test_normalize.py). Product name is the primary
source for size and pack because Walmart's `size` field is often wrong ("Each", "2", wrong oz).
"""
import re

UNIT_ALIASES = {
    "fl oz": "fl oz", "fl. oz": "fl oz", "fl.oz": "fl oz", "floz": "fl oz", "fluid ounce": "fl oz", "fluid ounces": "fl oz",
    "oz": "oz", "ounce": "oz", "ounces": "oz", "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "g": "g", "gram": "g", "grams": "g", "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml", "l": "l", "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "gal": "gal", "gallon": "gal", "gallons": "gal", "qt": "qt", "quart": "qt", "quarts": "qt", "pt": "pt", "pint": "pt", "pints": "pt",
}
# convert to base: weight -> oz, volume -> fl oz
TO_BASE = {"oz": ("oz", 1), "lb": ("oz", 16), "g": ("oz", 0.035274), "kg": ("oz", 35.274),
           "fl oz": ("fl oz", 1), "ml": ("fl oz", 0.033814), "l": ("fl oz", 33.814), "gal": ("fl oz", 128),
           "qt": ("fl oz", 32), "pt": ("fl oz", 16), "ct": ("ct", 1)}

_UNIT_RX = r"(fl\.?\s?oz|fluid\s+ounces?|ounces?|oz|lbs?|pounds?|kilograms?|kg|grams?|g|milliliters?|ml|liters?|litres?|l|gallons?|gal|quarts?|qt|pints?|pt)"
QTY = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?|\.\d+)\s*-?\s*" + _UNIT_RX + r"(?![a-z])", re.I)
MULTI = re.compile(r"(?<![\w.])(\d+)\s*(?:x|-|×)\s*(\d+(?:\.\d+)?)\s*-?\s*" + _UNIT_RX + r"(?![a-z])", re.I)
PACK = [
    re.compile(r"\((\d+)\s*(?:-\s*)?(?:pack|pk|count|ct)\)", re.I),
    re.compile(r"(?<![\w.])(\d+)\s*-?\s*(?:pack|pk|packs)\b", re.I),
    re.compile(r"\b(?:pack|case|box|set)\s+of\s+(\d+)\b", re.I),
]
COUNT = re.compile(r"(?<![\w.])(\d+)\s*-?\s*(?:count|ct|cnt)\b\.?", re.I)
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
MEDIA_RX = re.compile(r"\((?:paperback|hardcover|other|audio cd|cd|vinyl|dvd|blu-ray|board book|mass market paperback)\)|\b97[89]\d{10}\b|\baudio\s?cd\b|\bvinyl\b|\bdvd\b|\bblu-ray\b", re.I)
PUBLISHER_RX = re.compile(r"\b(publishing|publishers|press|books|cookbooks|records|music|entertainment|umgd|sony music|warner)\b", re.I)


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


def parse_quantity(text: str):
    """Return (size, unit, pack) from free text. pack is None when not stated."""
    if not text:
        return None, None, None
    t = text.replace("\u00d7", "x")
    pack = None
    m = MULTI.search(t)
    if m:
        return float(m.group(2)), _unit(m.group(3)), int(m.group(1))
    for rx in PACK:
        pm = rx.search(t)
        if pm:
            pack = int(pm.group(1)); break
    sizes = [(float(q.group(1)), _unit(q.group(2))) for q in QTY.finditer(t)]
    # prefer metric-free US unit if both "11 oz (312 g)" present: first mention wins
    size, unit = (sizes[0] if sizes else (None, None))
    if size is None:
        c = COUNT.search(t)
        if c:
            if pack is None:
                return float(c.group(1)), "ct", None
        return None, None, pack
    if pack is None:
        c = COUNT.search(t)
        if c and unit != "ct":
            pack = int(c.group(1))
    return size, unit, pack


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
    for kw in cfg["exclude_path_keywords"]:
        if kw in path:
            return "excluded_category"
    if dept_name != "Books":
        if MEDIA_RX.search(name):
            return "media_misfiled"
        brand = item.get("brandName") or ""
        if ";" in brand or PUBLISHER_RX.search(brand):
            return "media_misfiled"
    if dept_name == "Food" and not item.get("upc") and parse_quantity(name)[0] is None and not item.get("size"):
        return "food_without_upc_or_size"
    return None


def category(item: dict, dept: dict, cfg: dict) -> str:
    path = (item.get("categoryPath") or "").lower()
    for frag, cat in cfg["path_rules"]:
        if frag in path:
            return cat
    if dept["name"] == "Food":
        tail = path.split("/food/", 1)[-1]
        for kw, cat in cfg["keyword_rules_for_food"]:
            if kw in tail:
                return cat
    return dept["default_category"]


def normalize(item: dict, dept: dict, cfg: dict):
    """Return (row, None) for a kept item, or (None, reason) for a rejected one."""
    reason = junk_reason(item, dept["name"], cfg)
    if reason:
        return None, reason
    name = re.sub(r"\s+", " ", item["name"]).strip()
    key, retired, check_ok = gtin14(item.get("upc"))
    size, unit, pack = parse_quantity(name)
    flags = []
    src = "name"
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
    unit_price = round(price / (base * pack), 4) if base and pack else None
    if size is None:
        flags.append("no_size")
    if retired:
        flags.append("retired_upc")
    if key and not check_ok:
        flags.append("upc_check_digit")
    if any(item.get(k) for k in ("clearance", "flashDeal", "limitedTimeDeal")):
        flags.append("promo_price")
    brand = item.get("brandName")
    row = {
        "id": item["itemId"], "upc": key, "name": name, "brand": brand,
        "size": size, "unit": unit, "pack": pack, "base_qty": base, "base_unit": dim,
        "price": price, "unit_price": unit_price, "basis": basis,
        "cat": category(item, dept, cfg), "dept": dept["name"],
        "path": item.get("categoryPath"), "variants": variants(name),
        "store_brand": bool(brand and brand.strip().lower() in STORE_BRANDS),
        "stock": item.get("stock"), "online": item.get("availableOnline"),
        "offer": item.get("offerType"), "size_src": src, "flags": flags,
    }
    return row, None
