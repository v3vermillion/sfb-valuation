"""What an item is: its store category, whether it is carried at all, and whether its listing names a product.

docs/CATEGORIES.md is the labelling guide; tests/fixtures/category-gold.jsonl is the hand-labelled sample these rules are
measured against (tests/test_classify.py). Walmart's category path is a hint, never the answer: its feed files clothing
under Meat & Seafood, cookbooks under Baking and CDs under Beverages.

How a category is chosen:
  1. exclusions (apparel, footwear, pet beds, alcohol, tobacco, media) on the name, brand and path;
  2. the product noun: the lexicon match that ends last in the title's head (English product names end with the noun:
     "Peanut Butter Cookies" is cookies), searched in the text before the first comma, then in the whole name;
  3. Walmart's path, mapped by data/categories.json path rules (the most specific fragment wins);
  4. a strong noun wins over the path; a weak noun (one that depends on how it is sold: corn, chicken, beans) takes
     its form from the name ("frozen", "canned", "dried") or else from the path; the department default is the last resort.
"""
import re

FOOD_CATS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 28, 29}


def _alt(words):
    return "|".join(words)


def _wrx(words, flags=re.I):
    return re.compile(r"(?<![a-z0-9])(?:" + _alt(words) + r")(?![a-z])", flags)


# ---------------------------------------------------------------------------------------------- not carried at all
GARMENTS = [
    r"t-?shirts?", r"tee\s?shirts?", r"tees", r"tee", r"shirts?", r"blouses?", r"tank\s?tops?", r"crop\s?tops?", r"tube\s?tops?",
    r"tunics?", r"sweaters?", r"sweatshirts?", r"sweatsuits?", r"hoodies?", r"hoody", r"hooded\s+(?:sweatshirt|jacket|towel\s+poncho)",
    r"cardigans?", r"jackets?", r"parkas?", r"blazers?", r"(?:winter|rain|pea|trench|puffer|dog|cat|pet|fleece|wool|down|sport)\s?coats?",
    r"raincoats?", r"ponchos?", r"vests?", r"pants", r"trousers?", r"jeans", r"denim\s+(?:shorts|skirt|jacket)", r"leggings?",
    r"jeggings?", r"jogger\s+pants", r"sweatpants", r"shorts", r"skirts?", r"skorts?", r"dress", r"dresses", r"gowns?", r"nightgowns?",
    r"pajamas?", r"pyjamas?", r"pj\s?sets?", r"pjs", r"onesies?", r"bodysuits?", r"rompers?", r"jumpsuits?", r"overalls",
    r"coveralls?", r"footed\s+sleepers?", r"sleep\s*(?:and|&|n)\s*play", r"sleepwear", r"loungewear", r"nightshirts?",
    r"underwear", r"panty", r"panties", r"boxers?", r"boxer\s+briefs?", r"briefs", r"bras?", r"bralettes?", r"sports?\s+bras?",
    r"lingerie", r"camisoles?", r"undershirts?", r"thermal\s+(?:underwear|tops?|bottoms?)", r"long\s+johns",
    r"socks?", r"stockings?", r"tights", r"hosiery", r"pantyhose", r"swimsuits?", r"swimwear", r"swim\s+trunks", r"bikinis?",
    r"rash\s?guards?", r"hats?", r"beanies?", r"baseball\s+caps?", r"trucker\s+caps?", r"knit\s+caps?", r"snapback", r"visors?",
    r"bucket\s+hats?", r"mittens?", r"scarf", r"scarves", r"neckties?", r"bandanas?", r"costumes?",
    r"uniforms?", r"scrub\s+(?:tops?|pants|sets?)", r"medical\s+scrubs", r"robes?", r"bathrobes?", r"kimonos?", r"tutus?",
    r"leotards?", r"outfits?", r"layette", r"sweater\s+vests?", r"windbreakers?", r"turtle\s?necks?", r"polos?", r"henleys?",
    r"capri\s+(?:pants|leggings)", r"culottes?", r"slips", r"garters?", r"suspenders", r"balaclavas?", r"neck\s+gaiters?",
    r"gloves?", r"belts?", r"wigs?", r"cape", r"capes", r"tiaras?", r"scrunchie", r"hoods?", r"pup\s+tanks?",
]
APPAREL_RX = _wrx(GARMENTS)
# worn but not clothing, or a garment word inside another product's name
APPAREL_EXEMPT_RX = re.compile(
    r"(?:disposable|nitrile|latex|vinyl|exam(?:ination)?|cleaning|dish(?:washing)?|kitchen|oven|grill(?:ing)?|bbq|garden(?:ing)?|"
    r"work|utility|mechanic|boxing|batting|golf|baseball|softball|football|goalie|weight\s?lifting|cycling|gardening|"
    r"heat\s+resistant|chemical|rubber|household|latex-free|powder-free|food\s+service|surgical|medical\s+exam)\s+gloves?|"
    r"gloves?\s+(?:box|dispenser)|seat\s?belts?|belt\s+(?:sander|clip)|(?:lumbar|back|support|maternity|gait|transfer|hernia|"
    r"posture|sacroiliac|si|trochanter|rib|abdominal|waist\s+trimmer|weight(?:lifting)?|tool|timing|serpentine|drive|fan|v-)\s?belts?|"
    r"belt\s+(?:bag|pack)|"
    r"(?<!reusable\s)(?<!washable\s)(?:incontinence|disposable|protective|postpartum|maternity\s+disposable|absorbent)\s+"
    r"(?:underwear|briefs|panty|panties)|"
    r"(?:depend|assurance|always\s+discreet|tena|prevail|attends|poise|certainty|wellness)\b.*\b(?:underwear|briefs|pants)|"
    r"(?:adult|bariatric)\s+briefs|pull-?ups|training\s+pants|swim\s+(?:diapers?|pants)|easy\s?ups|goodnites|"
    r"christmas\s+stockings?|stocking\s+(?:stuffers?|holders?|hangers?)|holiday\s+stockings?|stockings?\s+(?:with|of)\b|"
    r"\bstocking\b.*\b(?:toys?|candy|treats?|ornaments?)|(?:toys?|candy|treats?)\b.*\bstocking\b|"
    r"hat\s+(?:rack|box|stand|hook)|top\s+hat\s+(?:candy|cake)|"
    r"dress(?:ing|er)|shirt\s+(?:stays|folder)|sock\s+(?:monkey|puppet)|(?:hose|socket)|sleeve\s+(?:protectors?|labels?)|"
    r"(?:dog|cat|pet)\s+harness|harness|leash|collar|(?:wig\s+(?:cap|stand|head|glue|tape|grip|brush|shampoo|spray|"
    r"conditioner|adhesive)|wig\s+care)|(?:hair|lace)\s+(?:wigs?\s+)?(?:glue|adhesive)|"
    r"robe\s+hooks?|vest\s+(?:extender)|life\s+(?:vests?|jackets?)|(?:safety|reflective|hi-?vis)\s+vests?|"
    r"pants?\s+(?:hanger|rack)|bra\s+(?:wash|bag|extender|pads?|inserts?)|nursing\s+(?:pads?|bra\s+pads)|"
    r"cape\s+cod|capes?\s+(?:cod|town)|polo\s+(?:shirt\s+)?(?:fragrance|cologne|perfume|eau)|ralph\s+lauren\s+polo|"
    r"slips?\s+(?:resistant|on\b)|non-?slip|anti-?slip|socks?\s+(?:aid|assist)|sock\s+aid|compression\s+sleeves?|"
    r"belts?\s+(?:for\s+(?:back|posture))|ear\s?muffs?\s+(?:hearing|noise|safety)|(?:hearing|noise|safety|shooting)\b.*\bear\s?muffs?|"
    r"(?:shower|bath|swim|hair)\s+caps?|cap\s+(?:gun|lock)|(?:bottle|gas|valve|lens|end|hub|toe|knee|wheel|cake)\s+caps?|"
    r"dress\s+(?:up\s+)?(?:doll|play)|tee\s+(?:ball|set|time)|golf\s+tees?|scrunchie\s+(?:hair\s+ties)|"
    r"diffuser\s+socks?|magnifying\s+visor|capri\s+sun|(?:range|stove|vent|exhaust|hair\s+dryer|dryer)\s+hoods?|"
    r"hood\s+(?:vent|filter|ornament)|hooded\s+towel|(?:wig|lace)\s+caps?|sock\s+(?:it|garland)",
    re.I)
HAIR_WIG_RX = re.compile(r"\b(?:human\s+hair|synthetic\s+hair|lace\s+front|wig\b(?!.*costume)|wigs\b(?!.*costume))", re.I)
COSTUME_RX = re.compile(r"\bcostumes?\b|\bcosplay\b|\bdress[- ]up\b(?!\s+doll)", re.I)
FOOTWEAR_RX = _wrx([
    r"shoes?", r"sneakers?", r"boots?", r"booties", r"sandals?", r"slippers?", r"flip[- ]?flops?", r"clogs?", r"loafers?",
    r"high\s+heels", r"heels", r"pumps?\s+(?:shoes|heels)", r"cleats?", r"moccasins?", r"mules", r"oxfords?", r"slides",
    r"water\s+shoes", r"footwear", r"espadrilles?", r"wedges\s+(?:sandals|shoes)", r"crib\s+shoes", r"slip-?ons?",
])
FOOTWEAR_EXEMPT_RX = re.compile(
    r"shoe\s+(?:polish|cleaner|laces?|horns?|racks?|organizers?|trees?|bags?|covers?|deodori[sz]er|inserts?|insoles?|"
    r"stretchers?|shine|brush|cabinet|storage|bench|dryer|spray|whitener|goo|repair|glue|dye|cream|wax|freshener)|"
    r"insoles?|inserts?|orthotics?|arch\s+supports?|heel\s+(?:cups?|pads?|liners?|grips?|balm|cream|smoother|protectors?|"
    r"cushions?|spurs?)|cracked\s+heels?|bunion|corn\s+(?:pads|cushions)|boot\s+(?:trays?|scraper|dryer|jack|shaper|racks?|"
    r"camp)|booster|bootcamp|pump\s+(?:sprayer|dispenser|bottle)|breast\s+pumps?|slides?\s+(?:for\s+microscope|projector)|"
    r"slippery|horseshoe|(?:dog|pet|paw)\s+(?:boots|booties|shoes)\s+(?:wax|balm)|paw\s+wax|"
    r"(?:moisturi[sz]ing|spa|gel|exfoliating|heated|microwav\w*)\s+(?:socks?|booties|boots|slippers)|"
    r"(?:shoe|boot)\s*-?\s*shaped|shoe\s+string\s+(?:potatoes|fries)|shoestring|sandal\s?wood|sandalwood|"
    r"clog\s+(?:remover|free)|drain\s+clogs?|unclog|anti-?clog|slipper\s+(?:orchid|socks\s+gripper)|"
    r"high\s+heels?\s+(?:cake|candy|chocolate|cookie)|wedges?\s+(?:potato|lemon|lime|cheese)", re.I)
PET_RX = re.compile(r"\b(?:dogs?|cats?|pets?|puppy|puppies|kittens?|canine|feline|k-?9)\b", re.I)
PET_BED_RX = re.compile(
    r"\b(?:pet|dog|cat|puppy|kitten|k-?9)\b[^,]{0,40}\b(?:beds?|cots?|nests?|cuddlers?|bolsters?|loungers?|sleepers?|"
    r"sofas?|couch(?:es)?|cushions?|mattress(?:es)?|pillows?|igloos?|caves?)\b|"
    r"\b(?:crate|kennel)\s+(?:pads?|mats?|beds?|liners?)\b|"
    r"\b(?:beds?|cots?|mats?|pads?|cushions?|pillows?)\b[^,]{0,25}\bfor\s+(?:small\s+|medium\s+|large\s+)?(?:dogs?|cats?|pets?)\b|"
    r"\bpet\s+(?:bed|sofa|cot|mat)\b|\b(?:heated|self-?warming|orthopedic|calming|donut)\b[^,]{0,30}\b(?:bed|pad)\b",
    re.I)
PET_BED_EXEMPT_RX = re.compile(r"\b(?:bed\s*bugs?|flea|tick|spray|shampoo|wipes?|food|treats?|litter|pee|potty|"
                               r"training\s+pads?|puppy\s+pads?|wee-?wee|cooling\s+mat|feeding\s+mat|placemat|lick\s+mat|"
                               r"snuffle\s+mat|elevated\s+(?:feeder|bowl))\b", re.I)
PET_BED_PATHS = ("/dog beds", "/cat beds", "/pet beds", "/crate mats", "/crate pads", "/dog crate mats")

ALCOHOL_STRONG_RX = re.compile(
    r"\b(?:vodka|whiske?y|bourbon|tequila|mezcal|liqueurs?|cognac|schnapps|hard\s+(?:seltzer|cider|lemonade|tea|kombucha|"
    r"soda|iced\s+tea)|lager|ipa|pale\s+ale|merlot|cabernet|chardonnay|pinot\s+(?:noir|grigio|gris)|sauvignon\s+blanc|"
    r"moscato|prosecco|riesling|zinfandel|malbec|sangria|champagne|spiked|white\s+claw|truly\s+hard)\b|"
    r"\d+(?:\.\d+)?\s*%\s*(?:abv|alc)|\balc\.?\s*/?\s*vol\b|\babv\b|\b(?:red|white|rose|rosé|sparkling|table|boxed|"
    r"dessert|fruit)\s+wines?\b|\bwines?\s*,?\s*\d+(?:\.\d+)?\s*(?:ml|l)\b|\b(?:craft\s+)?beers?\s*,?\s*\d+\s*(?:pk|pack)\b|"
    r"\b\d+\s*(?:ml|l)\s+(?:bottle\s+)?of\s+(?:wine|rum|gin)\b|\b(?:rum|gin)\s*,?\s*(?:750|375|1\.75)\s*ml\b", re.I)
NONALCOHOLIC_RX = re.compile(
    r"\bnon-?alcoholic\b|\balcohol[- ]free\b|\b0[.,]0\b|\bzero\s+(?:alcohol|proof)\b|\bmocktails?\b|\bmixers?\b|\bmix\b|"
    r"\bbitters\b|\bsyrups?\b|\bjuices?\b|\bsoda\b|\bwater\b|\bgrenadine\b|\bmargarita\s+salt\b|\brimming\b|"
    r"\b(?:sparkling|apple)\s+cider\b|\bcider\s+(?:vinegar|donuts?|mix)\b|\bcooking\s+wines?\b|\bwine\s+vinegar\b|"
    r"\b(?:wine|beer|cocktail|shot|martini|pint|pilsner)\s+(?:glass(?:es)?|opener|rack|chiller|stopper|aerator|"
    r"tumbler|cooler|bottle\s+opener|koozie|holder|charms?)\b|\broot\s+beer\b|\bginger\s+(?:beer|ale)\b|\bbirch\s+beer\b|"
    r"\bbeer\s+(?:bread|batter|brats?|cheese|nuts|can\s+chicken)\b|\bcherr(?:y|ies)\b|\bolives?\b|\bice\b|"
    r"\b(?:rum|brandy|bourbon|amaretto|wine|champagne|whiske?y)\s+(?:extract|flavou?r(?:ed|ing)?|cakes?|balls|sauce|"
    r"glaze|cream\s+cake|raisin|jelly|truffles?|gummies|candy)\b|\bhomebrew|\bbrewing\s+(?:kit|supplies)\b", re.I)
TOBACCO_RX = re.compile(r"\b(?:cigarettes?|cigars?|cigarillos?|chewing\s+tobacco|pipe\s+tobacco|smokeless\s+tobacco|"
                        r"snuff|snus|e-?cigs?|e-?cigarettes?|vapes?|vaping|e-?liquids?|e-?juice|nicotine\s+pouch(?:es)?|"
                        r"rolling\s+papers?|hookah\s+tobacco|shisha)\b", re.I)
STOP_SMOKING_RX = re.compile(r"\b(?:nicotine\s+(?:gum|patch(?:es)?|lozenges?|mini\s+lozenges?|polacrilex|transdermal)|"
                             r"stop\s+smoking|quit\s+smoking|smoking\s+cessation|candy\s+cigarettes?|bubble\s+gum\s+cigars?)\b",
                             re.I)
MEDIA_RX = re.compile(
    r"\((?:paperback|hardcover|other|audio\s*cd|cd|vinyl|dvd|blu-ray|board\s+book|mass\s+market\s+paperback|library\s+binding|"
    r"spiral[- ]bound|kindle|audiobook|cassette|vhs|lp|book|full\s+frame|widescreen)\)|,\s*\((?:paperback|hardcover)|"
    r"\b97[89]\d{10}\b|\baudio\s?cd\b|\bvinyl\s+(?:lp|record|album)\b|\bdvd\b|\bblu-?ray\b|\bmusic\s+&\s+performance\b|"
    r"\b(?:original\s+)?(?:motion\s+picture\s+)?soundtrack\b|\bvarious\s+artists\b|\s-\s(?:cd|vinyl|lp|dvd)\s*$|"
    r"\((?:19|20)\d\d\)\s*$|\(season\s+\d+|\bbook\s+\d+\b|\bcookbook\b|\brecipes?\s*:|:\s*(?:\d+\s+)?(?:easy\s+|delicious\s+|"
    r"simple\s+|healthy\s+|quick\s+)*recipes\b|\brecipes\s+(?:for|from)\b|\bnovel\b|\b(?:a|an)\s+\w+\s+mystery\b|"
    r"\bhardcover\b|\bpaperback\b|\bboard\s+book\b|\bpicture\s+book\b|\bcoloring\s+book\b(?=.*\bby\b)", re.I)
MEDIA_EXEMPT_RX = re.compile(r"\b(?:dvd\s+(?:player|case|rack|storage|holder)|blu-ray\s+player|cd\s+(?:player|case|rack|"
                             r"holder|storage)|recipe\s+(?:box|cards?|card\s+box|holder|book\s+stand|binder))\b", re.I)
PUBLISHER_RX = re.compile(r"\b(?:publishing|publishers|press|books|cookbooks|records|music|entertainment|umgd|sony\s+music|"
                          r"warner|pictures|studios|films?|media|editions)\b", re.I)
PUBLISHER_EXEMPT_RX = re.compile(r"\b(?:french\s+press|garlic\s+press|press\s+(?:on|n)|pressed|press-?on|panini\s+press|"
                                 r"tortilla\s+press|cider\s+press)\b", re.I)
EXPLICIT_NA_RX = re.compile(r"\bnon-?alcoholic\b|\balcohol[- ]free\b|\b0[.,]0\b|\bzero\s+(?:alcohol|proof)\b|\bmocktails?\b", re.I)
UNIT_RX = re.compile(r"\b\d+(?:\.\d+)?\s*-?\s*(?:oz|ounces?|fl\s*oz|lbs?|pounds?|g|kg|ml|l|ct|count|pack|pk|pcs?|pieces?)\b", re.I)
# Walmart's own apparel brands and the big basics labels: a listing under one with no product noun is clothing
APPAREL_BRANDS = {"no boundaries", "faded glory", "george", "time and tru", "athletic works", "wonder nation",
                  "garanimals", "terra & sky", "white stag", "secret treasures", "joyspun", "free assembly", "avia",
                  "hanes", "fruit of the loom", "gildan", "jockey", "scoop", "simply southern", "russell", "starter",
                  "danskin", "dickies", "wrangler", "levi's", "carhartt"}
# a book: a title with a subtitle, a person as the brand, and no size or count in the name
SUBTITLE_RX = re.compile(r"^[^,(]{3,}:\s+[A-Z][^,]{8,}")
PERSON_BRAND_RX = re.compile(r"^(?:[A-Z][a-z]+\.?\s+){1,2}[A-Z][a-z'\-]+(?:\s+(?:Jr|Sr|II|III)\.?)?$|;")

# ---------------------------------------------------------------------------------------------- placeholders
PLACEHOLDER_RX = re.compile(
    r"^\W*(?:merchandise|item|items|product|products|test(?:ing)?(?:\s+(?:item|product))?|sample|n/?a|unknown|"
    r"misc(?:ellaneous)?|general\s+merchandise|new\s+item|placeholder|tbd|do\s+not\s+use|not\s+for\s+sale|assorted|"
    r"various|default|cosmetic|cosmetics|pet\s+food|food|grocery|show|-|\.|coming\s+soon|discontinued(?:\s+item)?"
    r"(?:\s+by\s+(?:supplier|manufacturer|vendor))?|discontinued\s+by\s+\w+)\W*$|"
    r"\bcoming\s+soon\b|\bsigning\s+test\b|\bstress\s+test\b|\btest\s+(?:item|product|brand|listing|sku)\b|"
    r"\bdo\s+not\s+(?:use|sell|order|buy|purchase)\b|\bnot\s+for\s+(?:sale|resale)\b(?!\s+in\b)|\bdisplay\s+unit\b|^\W*delete\b|"
    r"\*+\s*to\s+be\s+deleted\s*\*+|\bcvp\b.*\bitem\b|\bnon-tax\b.*\bitem\b|^\W*\*+[^*]*\*+\s*\w+\s*$|"
    r"\bfy\d\d\s+wk\d+\b|^\W*shop\s+[\w-]+(?:\s+[\w-]+){0,3}\s+(?:nutrition|products|brand)\s*$|"
    r"\bmerchandise\s*$|^\d+\s*pc\s*\d+\s*pk\b|\b\d+\s*pc\b.*\b(?:tray|display|assortment)\b|"
    r"\*+\s*(?:holiday|parent|pdq)\b|^\W*(?:\*+[^*]*\*+\s*)+\w*\s*$|\bdummy\s+(?:item|test|product|sku)\b|"
    r"^\W*services?\b.*\bprogram\b|\bextended\s+(?:warranty|service)\b|\bprotection\s+plan\b",
    re.I)
# store display units (PDQ trays, shippers, pallets, planogram modules): a whole display priced as one listing. Only a
# display with a piece count or a display-sized price counts ("Tones T Grnd Sage Pdq" at $1.20 is one jar of sage)
DISPLAY_RX = re.compile(r"\bpdq\d*\b|\bshippers?\b|\bpallets?\b|\bplt\b|\bprd\b|\bw\d+\s*p\d+\b|\b\d{3,}\s*pcs?(?:\b|[a-z])", re.I)
# a store fixture is never a donation, whatever its price ("Nova 2.0 Retail Display" at $0.01)
FIXTURE_RX = re.compile(r"\b(?:retail|store|counter|floor)\s+display\b|\bdisplay\s+(?:only|box|stand|unit|tray)\b|\bendcap\b|"
                        r"\bfixture\b|\bmerchandising\s+tray\b|\bsidekick\s+display\b|\bpowerwing\b", re.I)
PIECE_COUNT_RX = re.compile(r"\b\d{2,}\s*pcs?(?:\b|[a-z])", re.I)
DISPLAY_PRICE_MIN = 30.0
CODE_NAME_RX = re.compile(r"^[A-Z0-9]{8,},[A-Z0-9-]+,[A-Z0-9-]+")          # "BAYCAUCA20WALDGN,P009376-LC001,..."
INGREDIENT_LIST_RX = re.compile(r"^(?:\(\d+\s*[Pp]ack\)\s*)*(?:[A-Z][A-Z ]+,\s*){4,}")   # an all-caps ingredient list
DISCONTINUED_RX = re.compile(r"\*+\s*discontinu\w*(?:\s+(?:by|kehe|item)[^*]*)?\*+|\(?\bdiscontinued\s+by\s+"
                             r"(?:manufacturer|supplier|vendor)\)?|^\W*discontinued\b\W*", re.I)
MARKER_RX = re.compile(r"\*{2,}[^*]{0,40}\*{2,}|\[incomplete\s+data\]\s*", re.I)


# ---------------------------------------------------------------------------------------------- product nouns
# (category, strength, phrases). strength "w" = weak: the form (fresh, frozen, canned, dried) decides the aisle.
LEXICON = [
    # --- produce (weak: fresh unless the name or path says otherwise)
    (1, "w", ["apples?", "bananas?", "oranges?", "lemons?", "limes?", "grapefruits?", "grapes", "strawberr(?:y|ies)",
              "blueberr(?:y|ies)", "raspberr(?:y|ies)", "blackberr(?:y|ies)", "cherries", "peach(?:es)?", "pears?", "plums?",
              "nectarines?", "apricots?", "mangos?", "mangoes", "pineapples?", "kiwis?", "kiwifruit", "papayas?", "melons?",
              "watermelons?", "cantaloupes?", "honeydews?", "avocados?", "tomato(?:es)?", "potato(?:es)?", "sweet\\s+potato(?:es)?",
              "yams?", "onions?", "shallots?", "garlic", "carrots?", "celery", "broccoli", "cauliflower", "cabbages?", "lettuce",
              "spinach", "kale", "collard\\s+greens", "greens", "arugula", "romaine", "salad\\s+kits?", "salad\\s+mix",
              "spring\\s+mix", "cucumbers?", "zucchini", "squash", "pumpkins?", "peppers?", "bell\\s+peppers?", "jalape[nñ]os?",
              "mushrooms?", "asparagus", "brussels\\s+sprouts", "green\\s+beans", "snap\\s+peas", "sugar\\s+snap\\s+peas",
              "corn\\s+on\\s+the\\s+cob", "sweet\\s+corn", "corn", "peas", "radish(?:es)?", "beets?", "turnips?", "parsnips?",
              "ginger\\s+root", "herbs", "cilantro", "parsley", "basil", "mint", "dill", "rosemary", "thyme", "leeks?",
              "eggplants?", "okra", "artichokes?", "fruit\\s+tray", "veggie\\s+tray", "vegetable\\s+tray", "fruit\\s+bowl",
              "fruit\\s+cups?\\s+fresh", "clementines?", "mandarins?", "tangerines?", "pomegranates?", "figs?", "dates",
              "coconuts?", "plantains?", "jicama", "bok\\s+choy", "sprouts", "microgreens", "fruit", "vegetables?", "veggies",
              "berries", "cranberries", "mixed\\s+vegetables", "stir\\s+fry\\s+vegetables"]),
    (1, "s", ["fresh\\s+(?:fruit|vegetables?|produce|herbs?)", "bagged\\s+salad", "salad\\s+kit", "bouquet\\s+garni"]),
    # --- dairy & eggs
    (2, "s", ["cream\\s+cheese\\s+spread", "melting\\s+cheese", "rice\\s+drink", "oat\\s+drink", "almond\\s+drink", "soy\\s+drink", "rice\\s+milk", "cashew\\s?milk", "plant[- ]based\\s+milk", "milk", "whole\\s+milk", "2%\\s+milk", "skim\\s+milk", "almond\\s?milk", "oat\\s?milk", "soy\\s?milk",
              "coconut\\s+milk\\s+beverage", "lactose[- ]free\\s+milk", "buttermilk", "half\\s*(?:&|and)\\s*half", "heavy\\s+cream",
              "whipping\\s+cream", "sour\\s+cream", "cream\\s+cheese", "cottage\\s+cheese", "butter", "margarine",
              "buttery\\s+spread", "yogurts?", "yoghurts?", "greek\\s+yogurt", "kefir", "eggs?", "egg\\s+whites",
              "egg\\s+substitutes?", "liquid\\s+eggs", "egg\\s+beaters", "coffee\\s+creamers?", "creamers?",
              "whipped\\s+(?:cream|topping)", "cool\\s+whip", "cheese\\s+sticks?", "string\\s+cheese", "shredded\\s+cheese",
              "cheese\\s+slices",
              "ricotta", "queso\\s+fresco", "biscuits?\\s+dough",
              "crescent\\s+rolls", "refrigerated\\s+dough", "cookie\\s+dough", "pie\\s+crust\\s+dough", "chocolate\\s+milk",
              "ghee", "custard", "dairy\\s+drink", "probiotic\\s+(?:drink|dailies)", "lassi", "snack\\s+cheese"]),
    # --- meat & seafood (weak: fresh unless canned, frozen, deli, jerky)
    (3, "w", ["chicken", "chicken\\s+breasts?", "chicken\\s+thighs?", "chicken\\s+wings?", "drumsticks?", "beef",
              "ground\\s+beef", "steaks?", "roasts?", "brisket", "ribs", "spareribs", "pork", "pork\\s+chops?", "pork\\s+loin",
              "tenderloin", "ham", "turkey", "ground\\s+turkey", "lamb", "veal", "bison", "venison", "sausages?", "bratwursts?",
              "brats", "kielbasa", "chorizo", "hot\\s+dogs?", "franks", "frankfurters?", "wieners?", "bacon", "salmon", "tuna",
              "cod", "tilapia", "catfish", "pollock", "haddock", "halibut", "trout", "swai", "mahi\\s+mahi", "shrimp", "crab",
              "crab\\s+legs", "lobster", "scallops?", "clams?", "oysters?", "mussels?", "crawfish", "fish", "fish\\s+fillets?",
              "seafood", "meatballs", "patties", "burgers?", "duck", "cornish\\s+hens?", "whole\\s+chicken", "rotisserie\\s+chicken",
              "pulled\\s+pork", "carnitas", "short\\s+ribs", "meat", "sardines", "anchovies", "spam", "vienna\\s+sausages?",
              "potted\\s+meat", "corned\\s+beef", "chicken\\s+breast\\s+chunks", "lunch\\s+meat"]),
    # --- deli & prepared
    (4, "s", ["deli\\s+(?:meat|sliced|ham|turkey|cheese)", "sliced\\s+(?:turkey|ham|chicken)\\s+breast", "salami", "bologna",
              "pastrami", "pepperoni\\s+slices", "prosciutto", "summer\\s+sausage", "charcuterie", "hummus", "lunchables",
              "lunch\\s+kits?", "lunchmakers", "snack\\s+trays?", "party\\s+trays?", "potato\\s+salad", "macaroni\\s+salad",
              "pasta\\s+salad", "coleslaw", "chicken\\s+salad", "egg\\s+salad", "tuna\\s+salad", "guacamole", "sandwich(?:es)?",
              "wraps?\\s+sandwich", "sushi", "rotisserie", "fried\\s+chicken", "deli", "pimento\\s+cheese", "bean\\s+salad",
              "spinach\\s+dip", "tzatziki", "pinwheels", "meal\\s+bundle", "fresh\\s+pasta", "refrigerated\\s+pasta",
              "tamales", "pierogies"]),
    # --- frozen (strong words)
    (5, "s", ["ice\\s+cream", "frozen\\s+yogurt", "gelato", "sorbet", "sherbet", "popsicles?", "ice\\s+pops?", "freezer\\s+pops",
              "fruit\\s+bars\\s+frozen", "ice\\s+cream\\s+(?:bars|sandwiches|cones)", "frozen\\s+\\w+", "tv\\s+dinners?",
              "frozen\\s+meals?", "pot\\s+pies?", "pizza\\s+rolls", "frozen\\s+pizza", "waffles\\s+frozen", "eggo",
              "hot\\s+pockets", "lean\\s+cuisine", "stouffer'?s", "banquet", "marie\\s+callender'?s", "healthy\\s+choice",
              "smart\\s+ones", "totino'?s", "jeno'?s", "tater\\s+tots", "french\\s+fries", "fries", "hash\\s+browns",
              "onion\\s+rings", "egg\\s+rolls", "potstickers", "dumplings", "chicken\\s+nuggets", "nuggets", "fish\\s+sticks",
              "corn\\s+dogs?", "pizza", "frozen\\s+novelt(?:y|ies)", "drumsticks\\s+cones", "klondike", "push\\s+pops?\\s+ice",
              "italian\\s+ice", "slush", "uncrustables", "juice\\s+bars", "fruit\\s+bars", "ice\\s+cream\\s+cake",
              "whipped\\s+topping\\s+frozen", "burritos?", "enchiladas", "lasagna", "chimichangas?", "taquitos",
              "breakfast\\s+sandwich(?:es)?", "pancakes?\\s+frozen", "frozen\\s+fruit", "edamame"]),
    # --- canned & jarred
    (6, "s", ["microwave\\s+(?:cups?|meals?|bowls?)", "fruit\\s+cups?", "jackfruit", "green\\s+chiles", "brine", "kraut", "luncheon\\s+meat", "gefilte\\s+fish", "whole\\s+oysters", "smoked\\s+oysters", "canned\\s+protein", "chunk\\s+(?:light|white)\\s+\\w+", "canned\\s+\\w+", "soups?", "broth", "stock", "bouillon", "bone\\s+broth", "chili", "stew", "beef\\s+stew",
              "chowder", "bisque", "gumbo", "ravioli\\s+can", "spaghettios", "chef\\s+boyardee", "beanie\\s+weenies",
              "baked\\s+beans", "refried\\s+beans", "pork\\s+and\\s+beans",
              "butter\\s+beans",
              "applesauce", "apple\\s+sauce", "fruit\\s+cups?",
              "mandarin\\s+oranges", "fruit\\s+cocktail", "pie\\s+filling\\s+can", "diced\\s+tomatoes", "crushed\\s+tomatoes",
              "tomato\\s+paste", "tomato\\s+sauce", "stewed\\s+tomatoes", "whole\\s+kernel\\s+corn", "creamed\\s+corn",
              "cream\\s+style\\s+corn", "sauerkraut", "hominy", "yams\\s+in\\s+syrup", "pumpkin\\s+puree", "canned\\s+pumpkin",
              "tuna\\s+pouch", "chunk\\s+light\\s+tuna", "albacore", "canned\\s+chicken", "chunk\\s+chicken", "deviled\\s+ham",
              "hash", "corned\\s+beef\\s+hash", "evaporated\\s+fruit", "coconut\\s+milk", "coconut\\s+cream", "water\\s+chestnuts",
              "bamboo\\s+shoots", "hearts\\s+of\\s+palm", "artichoke\\s+hearts", "condensed\\s+soup", "cream\\s+of\\s+\\w+",
              "ramen\\s+cups?\\s+soup", "soup\\s+cups?", "microwave\\s+meals?", "compleats", "dinty\\s+moore", "kid'?s\\s+kitchen",
              "spaghetti\\s+and\\s+meatballs", "beefaroni", "mixed\\s+fruit", "sliced\\s+peaches", "pear\\s+halves",
              "pineapple\\s+chunks", "pineapple\\s+tidbits", "crushed\\s+pineapple", "fruit\\s+in\\s+(?:juice|syrup)"]),
    # --- pasta, rice & dry goods
    (7, "s", ["noodle\\s+soup\\s+cups?", "instant\\s+noodle\\s+soup", "cup\\s+of\\s+noodles", "ramen\\s+noodle\\s+soup", "shells\\s*(?:&|and)\\s*cheese", "scratch\\s+kit", "lentejas", "dal", "tortilla\\s+mix", "breading", "breading\\s+mix", "batter\\s+mix", "fish\\s+fry", "seafood\\s+fry\\s+mix", "fry\\s+mix", "shake\\s+'?n\\s+bake", "coating\\s+mix", "seasoned\\s+coating", "pasta", "spaghetti", "penne", "rotini", "macaroni", "elbows", "linguine", "fettuccine", "lasagna\\s+noodles",
              "egg\\s+noodles", "noodles", "ramen", "instant\\s+noodles", "cup\\s+noodles", "udon", "soba", "orzo", "couscous",
              "rigatoni", "ziti", "farfalle", "bow\\s+ties\\s+pasta", "shells\\s+pasta", "angel\\s+hair", "vermicelli", "gnocchi",
              "rice", "brown\\s+rice", "white\\s+rice", "jasmine\\s+rice", "basmati", "wild\\s+rice", "rice\\s+mix", "rice-a-roni",
              "quinoa", "barley", "farro", "bulgur", "millet", "lentils", "split\\s+peas", "dried\\s+beans", "dry\\s+beans",
              "bean\\s+soup\\s+mix", "15\\s+bean\\s+soup", "mac\\s*(?:&|and|n)\\s*cheese", "macaroni\\s*(?:&|and)\\s*cheese",
              "macaroni\\s+and\\s+cheese\\s+dinner", "hamburger\\s+helper", "tuna\\s+helper", "helper", "pasta\\s+sides",
              "rice\\s+sides", "side\\s+dish(?:es)?", "instant\\s+potatoes", "mashed\\s+potatoes", "potato\\s+flakes",
              "scalloped\\s+potatoes", "au\\s+gratin", "stuffing", "stuffing\\s+mix", "taco\\s+shells?", "tostadas?",
              "taco\\s+dinner\\s+kit", "dinner\\s+kits?", "meal\\s+kits?", "bread\\s+crumbs", "breadcrumbs", "panko",
              "soup\\s+mix", "sopa", "cornmeal", "grits\\s+mix", "polenta", "masa", "tortilla\\s+mix", "risotto", "paella",
              "pad\\s+thai", "lo\\s+mein", "chow\\s+mein\\s+noodles", "rice\\s+noodles", "rice\\s+cakes\\s+korean",
              "dried\\s+pasta", "boxed\\s+dinner", "potatoes\\s+box", "idahoan", "knorr\\s+sides", "pasta\\s+roni"]),
    # --- bread & bakery
    (8, "s", ["bread", "loaf", "buns", "rolls", "dinner\\s+rolls", "hamburger\\s+buns", "hot\\s+dog\\s+buns", "bagels?",
              "english\\s+muffins?", "muffins?", "croissants?", "tortillas?", "flour\\s+tortillas", "corn\\s+tortillas", "pita",
              "naan", "flatbreads?", "wraps", "sourdough", "brioche", "ciabatta", "baguettes?", "cakes?", "cupcakes?", "pies?",
              "donuts?", "doughnuts?", "danish(?:es)?", "pastr(?:y|ies)", "cinnamon\\s+rolls", "honey\\s+buns", "snack\\s+cakes?",
              "little\\s+debbie", "hostess", "tastykake", "zebra\\s+cakes", "twinkies", "cheesecake", "brownies?",
              "coffee\\s+cake", "pound\\s+cake", "bundt\\s+cake", "sheet\\s+cake", "angel\\s+food", "cream\\s+puffs",
              "eclairs?", "scones?", "biscotti", "crumpets", "bakery\\s+cookies", "cookie\\s+cake", "kolaches?", "crispbread",
              "breadsticks", "garlic\\s+bread", "texas\\s+toast", "stuffing\\s+bread", "challah", "rye", "pumpernickel",
              "hoagie\\s+rolls", "sub\\s+rolls", "slider\\s+buns", "kaiser\\s+rolls", "pretzel\\s+buns", "bread\\s+bowls?"]),
    # --- snacks & candy
    (9, "s", ["milk\\s+chocolate", "dark\\s+chocolate", "hemp\\s+(?:seeds?|hearts)", "energy\\s+balls", "protein\\s+bites", "energy\\s+bites", "superfood\\s+bites", "bar\\s+bites", "protein\\s+balls", "crisps", "chickpeas?\\s+(?:honey\\s+)?roasted", "roasted\\s+chickpeas", "popcorners", "chips", "potato\\s+chips", "tortilla\\s+chips", "pita\\s+chips", "veggie\\s+chips", "pork\\s+rinds",
              "cracklins", "pretzels?", "popcorn", "crackers?", "graham\\s+crackers", "cookies?", "oreos?", "wafers?",
              "nuts", "peanuts", "almonds", "cashews", "pistachios", "walnuts", "pecans", "macadamias?", "mixed\\s+nuts",
              "trail\\s+mix", "seeds", "sunflower\\s+seeds", "pumpkin\\s+seeds", "dried\\s+fruits?", "raisins", "craisins",
              "dried\\s+(?:cranberries|mango|apricots|apples|cherries|blueberries|pineapple|figs|dates|plums)", "prunes",
              "fruit\\s+snacks", "fruit\\s+leather", "fruit\\s+roll-?ups", "gushers", "jerky", "meat\\s+sticks?", "beef\\s+sticks?",
              "snack\\s+sticks?", "slim\\s+jim", "protein\\s+bars?", "snack\\s+bars?", "nutrition\\s+bars?", "energy\\s+bars?",
              "bars", "pudding\\s+cups?", "pudding", "gelatin\\s+cups?", "jello\\s+cups?", "jell-o\\s+cups?", "snack\\s+mix",
              "chex\\s+mix", "goldfish", "cheez-?its?", "cheese\\s+puffs", "cheese\\s+curls", "puffs", "cheetos", "doritos",
              "fritos", "pringles", "funyuns", "takis", "rice\\s+cakes", "rice\\s+crisps", "veggie\\s+straws", "snacks?",
              "candy", "candies", "chocolates?", "chocolate\\s+bars?", "candy\\s+bars?", "truffles", "gummies", "gummy\\s+\\w+",
              "gummy", "jelly\\s+beans", "licorice", "lollipops?", "suckers", "hard\\s+candy", "taffy", "caramels?", "toffee",
              "fudge", "brittle", "marshmallow\\s+(?:eggs|peeps|cones)", "peeps", "mints", "breath\\s+mints", "gum",
              "chewing\\s+gum", "bubble\\s+gum", "gumballs", "m&m'?s", "kisses", "peanut\\s+butter\\s+cups", "skittles",
              "starburst", "twizzlers", "jolly\\s+ranchers?", "sour\\s+patch", "nerds", "airheads", "laffy\\s+taffy",
              "tootsie\\s+rolls?", "candy\\s+corn", "cotton\\s+candy", "rock\\s+candy", "chocolate\\s+covered\\s+\\w+",
              "bark", "nut\\s+clusters", "turtles", "bonbons", "pralines", "nougat", "halva", "mochi", "pocky",
              "seaweed\\s+snacks?", "roasted\\s+seaweed", "plantain\\s+chips", "corn\\s+nuts", "sweet\\s+treats?",
              "rice\\s+krispies\\s+treats", "snack\\s+packs?", "variety\\s+pack\\s+snacks", "gift\\s+basket", "goodies\\s+basket",
              "cookie\\s+tin", "sampler", "nut\\s+mix", "nut\\s+butter\\s+filled", "fruit\\s+crisps", "apple\\s+chips",
              "banana\\s+chips", "coconut\\s+chips", "kettle\\s+corn", "caramel\\s+corn", "cracker\\s+jack", "animal\\s+crackers",
              "teddy\\s+grahams", "pirouline", "biscuits\\s+cookies", "shortbread", "macarons?", "meringues?"]),
    # --- beverages
    (10, "s", ["creamer[\\w\\s]{0,20}powder(?:ed)?", "powdered\\s+(?:coffee\\s+)?creamer", "coffee\\s+creamer\\s+powder", "aloe\\s+vera\\s+(?:drink|juice|king)", "probiotic\\s+shots?", "wellness\\s+shots?", "capuchino", "iced\\s+coffee", "soda\\s+syrup", "coffee\\s+flavoring", "flavored\\s+syrup", "drink\\s+syrup", "snow\\s+cone\\s+syrup", "game\\s+fuel", "coffee\\s+capsules", "espresso\\s+capsules", "nespresso", "single\\s+serve\\s+coffee", "coffee\\s+for\\s+keurig", "instant\\s+tea", "tea\\s+powder", "drink\\s+mix\\s+powder", "smoothie\\s+powder", "flavoring\\s+straws", "water", "spring\\s+water", "purified\\s+water", "distilled\\s+water", "sparkling\\s+water", "seltzer",
               "mineral\\s+water", "coconut\\s+water", "soda", "sodas", "soda\\s+pop", "pop", "cola", "colas", "coke", "pepsi",
               "sprite", "root\\s+beer", "ginger\\s+ale", "ginger\\s+beer", "tonic\\s+water", "club\\s+soda", "lemonade",
               "limeade", "punch", "juices?", "juice\\s+drinks?", "juice\\s+boxes", "nectars?", "cider", "apple\\s+cider",
               "smoothies?", "sports\\s+drinks?", "gatorade", "powerade", "electrolyte\\s+drink", "energy\\s+drinks?",
               "energy\\s+shots?", "red\\s+bull", "monster\\s+energy", "coffee", "ground\\s+coffee", "whole\\s+bean\\s+coffee",
               "instant\\s+coffee", "k-?cups?", "coffee\\s+pods?", "pods", "cold\\s+brew", "espresso", "latte", "cappuccino",
               "iced\\s+coffee", "frappuccino", "tea", "teas", "tea\\s+bags", "green\\s+tea", "black\\s+tea", "herbal\\s+tea",
               "iced\\s+tea", "sweet\\s+tea", "chai", "matcha", "kombucha", "hot\\s+cocoa", "hot\\s+chocolate", "cocoa\\s+mix",
               "drink\\s+mix", "drink\\s+mixes", "powdered\\s+drink", "water\\s+enhancers?", "liquid\\s+water\\s+enhancer",
               "mio", "kool-?aid", "tang", "crystal\\s+light", "country\\s+time", "drink\\s+packets", "protein\\s+shakes?",
               "nutrition\\s+shakes?", "nutritional\\s+drinks?", "meal\\s+replacement\\s+shakes?", "ensure", "boost", "glucerna",
               "premier\\s+protein", "shakes?", "milkshakes?", "cocktail\\s+mixers?", "margarita\\s+mix", "bloody\\s+mary\\s+mix",
               "pina\\s+colada\\s+mix", "mixers?", "bitters", "sparkling\\s+cider", "drinks?", "beverages?", "vitamin\\s+water",
               "flavored\\s+water", "creamer\\s+powder", "powdered\\s+creamer", "coffee-?mate\\s+powder", "coffee\\s+syrups?",
               "flavored\\s+syrups?", "horchata", "agua\\s+fresca", "aloe\\s+vera\\s+drink", "yerba\\s+mate", "malt\\s+beverage\\s+non",
               "slushie\\s+mix", "frappe\\s+mix", "cocoa"]),
    # --- condiments, sauces & spreads
    (11, "s", ["pimientos", "pimento\\s+peppers", "roasted\\s+(?:red\\s+|yellow\\s+|red\\s+(?:&|and)\\s+yellow\\s+)?peppers", "marinated\\s+\\w+(?:\\s+(?:&|and)\\s+\\w+)?\\s+peppers", "dipping\\s+sauce", "stir\\s+fry\\s+sauce", "gourmaise", "sloppy\\s+joe\\s+sauce", "salmon\\s+spread", "pepper\\s+paste", "chili\\s+paste", "chile\\s+paste", "tomato\\s+cooking\\s+base", "sofrito", "giardiniera", "bruschetta", "ajvar", "gravy\\s+(?:seasoning\\s+)?mix", "liquid\\s+smoke", "sandwich\\s+toppers", "cooking\\s+base", "ketchup", "catsup", "mustard", "mayonnaise", "mayo", "miracle\\s+whip", "relish", "salad\\s+dressings?",
               "dressings?", "ranch", "vinaigrette", "barbecue\\s+sauce", "bbq\\s+sauce", "hot\\s+sauce", "sriracha",
               "soy\\s+sauce", "teriyaki", "worcestershire", "steak\\s+sauce", "a1", "tartar\\s+sauce", "cocktail\\s+sauce",
               "buffalo\\s+sauce", "wing\\s+sauce", "pasta\\s+sauce", "spaghetti\\s+sauce", "marinara", "alfredo", "pesto",
               "pizza\\s+sauce", "salsa", "picante", "queso", "cheese\\s+dip", "bean\\s+dip", "dips?", "gravy", "gravy\\s+mix",
               "marinades?", "sauces?", "enchilada\\s+sauce", "taco\\s+sauce", "hoisin", "fish\\s+sauce", "oyster\\s+sauce",
               "chili\\s+sauce", "sweet\\s+and\\s+sour", "duck\\s+sauce", "horseradish", "aioli", "chutney", "tahini",
               "pickles?", "dill\\s+pickles", "pickle\\s+spears", "pickled\\s+\\w+", "olives?", "capers", "pepperoncini",
               "banana\\s+peppers", "roasted\\s+red\\s+peppers", "jalapeno\\s+slices", "sauerkraut\\s+jar", "peanut\\s+butter",
               "almond\\s+butter", "nut\\s+butters?", "sunflower\\s+butter", "cookie\\s+butter", "nutella", "hazelnut\\s+spread",
               "jam", "jams", "jelly", "jellies", "preserves", "marmalade", "fruit\\s+spread", "apple\\s+butter", "honey",
               "spreads?", "sandwich\\s+spread", "marshmallow\\s+cr[eè]me", "fluff", "lemon\\s+curd", "chocolate\\s+syrup",
               "caramel\\s+sauce", "ice\\s+cream\\s+toppings?", "dessert\\s+toppings?", "sundae\\s+syrup", "molasses",
               "agave", "taco\\s+seasoning\\s+sauce", "harissa", "chimichurri", "mole", "adobo\\s+sauce", "curry\\s+paste",
               "gochujang", "miso", "wasabi", "ponzu", "kimchi", "salad\\s+toppings?", "croutons", "bacon\\s+bits"]),
    # --- baking, spices & oils
    (28, "s", ["apple\\s+cider\\s+vinegar", "sesame\\s+seeds?", "baking\\s+bits", "popcorn\\s+seasoning", "jerky\\s+spice", "(?:cake|buns?|bread|cookie|brownie|muffin|cupcake)\\s+(?:baking\\s+)?(?:kit|mix)", "baking\\s+kit", "mix\\s+brownie", "sweetened\\s+condensed\\s+milk", "condensed\\s+milk", "ground\\s+(?:white|black)\\s+pepper", "white\\s+pepper", "pepper\\s+supreme", "adobo", "sauce\\s+mix", "quick\\s+process\\s+mix", "pickl(?:e|ing)\\s+mix", "seasoning\\s+grinder", "cacao\\s+powder", "saffron", "chiles?\\s+(?:de\\s+)?arbol", "arbol\\s+chiles?", "sweetn?ers?", "vegit", "seasoning\\s+blend", "rice\\s+bowl\\s+topping", "baking\\s+chips?", "chile\\s+pods", "chili\\s+pods", "dried\\s+chil(?:es|is|e|i)", "pizza\\s+crust\\s+mix", "crust\\s+mix", "pizza\\s+dough\\s+mix", "old\\s+bay", "tarragon", "marjoram", "sage", "bay\\s+leaf", "dried\\s+garlic", "dehydrated\\s+\\w+", "garlic\\s+granules", "flour", "all[- ]purpose\\s+flour", "bread\\s+flour", "self[- ]rising\\s+flour", "almond\\s+flour", "sugar",
               "brown\\s+sugar", "powdered\\s+sugar", "cane\\s+sugar", "sweeteners?", "splenda", "stevia", "sugar\\s+substitute",
               "baking\\s+soda", "baking\\s+powder", "yeast", "cornstarch", "corn\\s+starch", "cake\\s+mix", "brownie\\s+mix",
               "muffin\\s+mix", "cookie\\s+mix", "cornbread\\s+mix", "biscuit\\s+mix", "bisquick", "baking\\s+mix", "frosting",
               "icing", "sprinkles", "food\\s+colou?r(?:ing)?", "gel\\s+colou?r", "extracts?", "vanilla\\s+extract", "flavoring",
               "chocolate\\s+chips", "morsels", "baking\\s+chocolate", "baking\\s+bar", "cocoa\\s+powder",
               "baking\\s+cocoa", "coconut\\s+flakes", "shredded\\s+coconut", "pie\\s+filling", "pie\\s+crusts?", "graham\\s+cracker\\s+crust",
               "evaporated\\s+milk", "condensed\\s+milk", "powdered\\s+milk", "dry\\s+milk",
               "gelatin", "jell-?o", "pudding\\s+mix", "instant\\s+pudding", "marshmallows", "mini\\s+marshmallows",
               "cake\\s+decorations?", "edible\\s+\\w+", "fondant", "candy\\s+melts", "decorating\\s+icing", "cooking\\s+oil",
               "vegetable\\s+oil", "canola\\s+oil", "olive\\s+oil", "extra\\s+virgin", "coconut\\s+oil", "avocado\\s+oil",
               "peanut\\s+oil", "sesame\\s+oil", "oils?", "shortening", "crisco", "lard", "cooking\\s+spray", "pam", "vinegar",
               "salt", "sea\\s+salt", "kosher\\s+salt", "pepper\\s+ground", "black\\s+pepper", "peppercorns", "spices?",
               "seasonings?", "seasoning\\s+mix", "taco\\s+seasoning", "spice\\s+rubs?", "rubs?", "herbs\\s+dried", "dried\\s+herbs",
               "oregano", "cumin", "paprika", "chili\\s+powder", "cinnamon", "nutmeg", "cloves", "allspice", "ginger\\s+ground",
               "garlic\\s+powder", "onion\\s+powder", "garlic\\s+salt", "curry\\s+powder", "turmeric", "bay\\s+leaves",
               "red\\s+pepper\\s+flakes", "crushed\\s+red\\s+pepper", "cayenne", "italian\\s+seasoning", "poultry\\s+seasoning",
               "lemon\\s+pepper", "seasoned\\s+salt", "msg", "accent", "meat\\s+tenderizer", "cream\\s+of\\s+tartar",
               "corn\\s+syrup", "karo",
               "pectin", "baking\\s+cups\\s+edible", "nonpareils", "cake\\s+flour", "masa\\s+harina", "cornmeal\\s+mix",
               "ice\\s+cream\\s+cones?", "waffle\\s+cones?", "sugar\\s+cones?", "pie\\s+shells?", "phyllo", "puff\\s+pastry",
               "baking\\s+essentials", "dough\\s+enhancer", "vital\\s+wheat\\s+gluten", "xanthan", "arrowroot", "tapioca",
               "bouillon\\s+cubes", "sazon", "adobo\\s+seasoning", "everything\\s+bagel\\s+seasoning", "seasoning\\s+packets?",
               "marinade\\s+mix", "ranch\\s+seasoning", "dip\\s+mix", "chili\\s+seasoning"]),
    # --- breakfast & cereal
    (29, "s", ["pancake\\s+syrup", "waffle\\s+syrup", "table\\s+syrup", "chewy\\s+(?:granola\\s+)?bars?", "oatmeal", "cereals?", "granola", "muesli", "oatmeal", "oats", "rolled\\s+oats", "steel\\s+cut\\s+oats", "instant\\s+oatmeal",
               "grits", "cream\\s+of\\s+wheat", "malt-?o-?meal", "hot\\s+cereal", "pancake\\s+mix", "waffle\\s+mix",
               "pancake\\s+(?:and|&)\\s+waffle\\s+mix", "pancake\\s+syrup", "maple\\s+syrup", "syrup", "toaster\\s+pastr(?:y|ies)",
               "pop-?tarts?", "toaster\\s+strudel", "granola\\s+bars?", "cereal\\s+bars?", "breakfast\\s+bars?",
               "oat\\s+bars?", "nutri-?grain", "belvita", "breakfast\\s+biscuits", "chewy\\s+bars", "fruit\\s+and\\s+grain\\s+bars?",
               "cheerios", "corn\\s+flakes", "frosted\\s+flakes", "raisin\\s+bran", "rice\\s+krispies", "froot\\s+loops",
               "lucky\\s+charms", "cinnamon\\s+toast\\s+crunch", "honey\\s+bunches", "special\\s+k", "wheaties", "chex",
               "life\\s+cereal", "cap'?n\\s+crunch", "breakfast\\s+essentials", "wheat\\s+germ", "flax", "chia\\s+seeds",
               "overnight\\s+oats", "breakfast\\s+cookies"]),
    # --- baby
    (13, "s", ["diapers?", "baby\\s+wipes", "wipes\\s+baby", "infant\\s+formula", "baby\\s+formula", "formula", "similac",
               "enfamil", "baby\\s+food", "baby\\s+cereal", "puffs\\s+baby", "teethers?", "teething", "pacifiers?", "baby\\s+bottles?",
               "sippy\\s+cups?", "nipples", "bibs?", "burp\\s+cloths?", "baby\\s+(?:lotion|shampoo|wash|oil|powder|bath)",
               "diaper\\s+(?:rash|cream|bag|pail)", "crib", "cribs", "bassinets?", "playards?", "pack\\s+'?n\\s+play", "strollers?",
               "car\\s+seats?", "booster\\s+seats?", "high\\s?chairs?", "baby\\s+monitors?", "baby\\s+gates?", "baby\\s+carriers?",
               "swaddles?", "swaddle\\s+blankets?", "receiving\\s+blankets?", "crib\\s+(?:sheets?|bedding|mattress)",
               "changing\\s+(?:pads?|tables?)", "nursing\\s+(?:pillows?|pads?|covers?)", "breast\\s+pumps?", "baby\\s+(?:toys?|gym|swing|bouncer|walker)",
               "infant", "newborn", "toddler\\s+(?:snacks|meals)", "baby\\s+snacks", "yogurt\\s+melts", "gerber",
               "pedialyte", "electrolyte\\s+solution", "training\\s+pants", "pull-?ups", "potty\\s+(?:seat|chair|training)",
               "sleep\\s+sacks?", "wearable\\s+blankets?", "sleepsack", "baby\\s+bathtub", "baby\\s+nail", "nasal\\s+aspirator",
               "rash\\s+cream", "teether", "activity\\s+center", "exersaucer", "jumper", "rocker", "mobile"]),
    # --- health & medicine
    (14, "s", ["face\\s+masks?\\s+(?:disposable|surgical|3-?ply)", "3-?ply", "ear\\s+loops?", "mouth\\s+masks?", "face\\s+covers?", "protective\\s+masks?", "lice\\s+(?:comb|treatment|shampoo)", "electrode\\s+pads", "urostomy", "ostomy", "breathalyzers?", "prescription\\s+(?:glasses|eyeglasses|sunglasses)", "dietary\\s+supplements?", "wound\\s+dressings?", "lens\\s+solution", "contact\\s+solution", "protein\\s+supplement", "vitamins?", "multivitamins?", "supplements?", "dietary\\s+supplement", "softgels?", "capsules?", "tablets?",
               "caplets?", "gummies\\s+vitamin", "probiotics?", "fish\\s+oil", "omega-?3", "melatonin", "biotin", "collagen\\s+(?:peptides|powder|supplement)",
               "protein\\s+powder", "whey", "creatine", "pre-?workout", "bcaa", "amino\\s+acids?", "electrolytes\\s+powder",
               "pain\\s+relief", "pain\\s+reliever", "ibuprofen", "acetaminophen", "aspirin", "naproxen", "advil", "tylenol",
               "aleve", "motrin", "excedrin", "cold\\s+(?:and|&)\\s+flu", "cough\\s+(?:syrup|drops|suppressant|medicine)",
               "decongestant", "allergy\\s+(?:relief|medicine|tablets)", "antihistamine", "nasal\\s+spray", "eye\\s+drops",
               "ear\\s+drops", "antacids?", "heartburn", "laxatives?", "stool\\s+softener", "fiber\\s+supplement", "anti-?diarrheal",
               "sleep\\s+aid", "first\\s+aid", "bandages?", "band-?aids?", "gauze", "medical\\s+tape", "antiseptic", "antibiotic\\s+ointment",
               "hydrocortisone", "thermometers?", "blood\\s+pressure\\s+monitor", "glucose\\s+(?:meter|test\\s+strips|tablets)",
               "test\\s+strips", "lancets?", "pill\\s+organi[sz]er", "heating\\s+pads?", "ice\\s+packs?", "hot\\s+cold\\s+pack",
               "braces?", "knee\\s+brace", "ankle\\s+brace", "wrist\\s+brace", "back\\s+brace", "support\\s+belt", "compression\\s+sleeves?",
               "walkers?", "rollators?", "canes?", "wheelchairs?", "crutches", "shower\\s+chairs?", "bath\\s+bench", "grab\\s+bars?",
               "raised\\s+toilet\\s+seat", "reading\\s+glasses", "readers", "contact\\s+lens(?:es)?\\s+solution", "contact\\s+lens(?:es)?",
               "saline", "massagers?", "massage\\s+(?:gun|chair|cushion)", "tens\\s+unit", "insoles?", "arch\\s+supports?",
               "foot\\s+(?:cream|care|powder|spray|soak)", "corn\\s+remover", "callus", "bunion", "athlete'?s\\s+foot", "antifungal",
               "wart\\s+remover", "cold\\s+sore", "hemorrhoid", "pregnancy\\s+tests?", "ovulation\\s+tests?", "covid\\s+test",
               "nicotine\\s+(?:gum|patch(?:es)?|lozenges?)", "medicine", "medication", "relief", "remedy", "homeopathic",
               "lozenges", "throat\\s+drops", "vapor\\s+rub", "vaporub", "humidifiers?", "vaporizers?", "nebulizers?",
               "pulse\\s+oximeter", "stethoscope", "wound\\s+care", "burn\\s+cream", "scar\\s+gel", "itch\\s+relief", "calamine",
               "rubbing\\s+alcohol", "isopropyl\\s+alcohol", "hydrogen\\s+peroxide", "epsom\\s+salt", "essential\\s+oils?",
               "aromatherapy", "elderberry", "zinc", "vitamin\\s+[a-e]\\d*", "iron\\s+supplement", "calcium", "magnesium",
               "potassium", "turmeric\\s+curcumin", "apple\\s+cider\\s+vinegar\\s+gummies", "keto\\s+pills", "weight\\s+loss",
               "diet\\s+pills", "appetite", "energy\\s+supplement", "immune\\s+support", "nasal\\s+strips", "snoring",
               "hearing\\s+aids?", "eye\\s+vitamins", "prenatal", "glucosamine", "joint\\s+support", "muscle\\s+rub",
               "pain\\s+relieving\\s+(?:cream|gel|patch(?:es)?)", "lidocaine", "biofreeze", "icy\\s+hot", "bengay", "salonpas",
               "kinesiology\\s+tape", "athletic\\s+tape", "elastic\\s+bandage", "ace\\s+bandage", "splint", "sling",
               "cervical\\s+collar", "posture\\s+corrector", "mobility\\s+scooter", "transport\\s+chair", "bedside\\s+commode",
               "commode", "urinal", "bed\\s+pan", "reacher", "pill\\s+crusher", "syringes?", "alcohol\\s+(?:pads|swabs|prep)",
               "face\\s+masks?\\s+(?:disposable|surgical)", "kn95", "n95",
               "disposable\\s+gloves", "exam\\s+gloves", "nitrile\\s+gloves", "hand\\s+sanitizer", "eye\\s+wash",
               "contact\\s+lens", "blue\\s+light\\s+glasses", "eyeglasses", "eyewear", "sunglasses\\s+readers"]),
    # --- personal care
    (15, "s", ["soap", "bar\\s+soap", "body\\s+wash", "shower\\s+gel", "hand\\s+soap", "hand\\s+wash", "body\\s+lotion",
               "hand\\s+cream", "hand\\s+lotion", "body\\s+butter", "body\\s+cream", "body\\s+oil",
               "deodorant", "antiperspirant", "toothpaste", "toothbrush(?:es)?", "electric\\s+toothbrush", "dental\\s+floss",
               "floss", "flossers", "floss\\s+picks", "mouthwash", "mouth\\s+rinse", "denture\\s+(?:adhesive|cleanser|cream|tablets)",
               "polident", "poligrip", "teeth\\s+whitening", "whitening\\s+strips", "razors?", "razor\\s+blades?", "cartridges",
               "shaving\\s+(?:cream|gel|foam|soap)", "shave\\s+(?:gel|cream)", "aftershave", "after\\s+shave", "trimmers?",
               "beard\\s+(?:oil|balm|trimmer)", "electric\\s+shavers?", "shavers?", "hair\\s+removal", "wax\\s+strips",
               "depilatory", "nair", "veet", "tampons?", "pads", "maxi\\s+pads", "panty\\s?liners?", "liners", "feminine\\s+wash",
               "feminine\\s+wipes", "menstrual\\s+cups?", "incontinence", "adult\\s+diapers?", "bladder\\s+control",
               "underpads", "chux", "condoms?", "lubricants?", "personal\\s+lubricant", "pregnancy", "cotton\\s+balls",
               "cotton\\s+swabs", "q-?tips", "cotton\\s+rounds", "body\\s+powder", "talc", "baby\\s+powder\\s+adult",
               "personal\\s+wipes", "flushable\\s+wipes", "bath\\s+salts", "bubble\\s+bath", "bath\\s+bombs?", "loofahs?",
               "bath\\s+sponges?", "shower\\s+(?:puff|poufs?)", "washcloths\\s+disposable", "foot\\s+spa", "pumice",
               "men'?s\\s+grooming", "grooming\\s+kit", "nose\\s+hair\\s+trimmer", "ear\\s+wax", "tongue\\s+scraper",
               "water\\s+flosser", "orthodontic", "mouth\\s+guard", "breath\\s+spray", "lip\\s+balm\\s+men", "intimate\\s+wash",
               "douche", "vaginal", "yeast\\s+infection", "monistat", "summer'?s\\s+eve", "body\\s+scrub", "hand\\s+sanitizing\\s+wipes"]),
    # --- beauty
    (30, "s", ["body\\s+spray", "body\\s+mist", "hair\\s+(?:&|and)\\s+body\\s+mist", "fragrance\\s+body\\s+spray", "body\\s+splash", "shampoo", "conditioner", "2-in-1", "dry\\s+shampoo", "hair\\s+(?:spray|gel|mousse|serum|oil|mask|cream|"
               "color|colour|dye|treatment|tonic|wax|pomade|paste|clay|lotion|milk|butter|food|relaxer|growth|vitamins|"
               "dryer|straightener|curler|clips?|ties|bands|pins|accessories|brush|comb|extensions?|pieces?|bows?|rollers|net)",
               "hairspray", "styling\\s+(?:gel|cream|foam|product)", "leave-?in", "edge\\s+control", "curl\\s+(?:cream|defin\\w+)",
               "flat\\s+iron", "curling\\s+(?:iron|wand)", "blow\\s+dryer", "hot\\s+brush", "hot\\s+rollers", "headbands?",
               "scrunchies?", "barrettes?", "bobby\\s+pins", "claw\\s+clips?", "jaw\\s+clips?", "wigs?", "weave", "braiding\\s+hair",
               "lace\\s+front", "makeup", "make-?up", "foundation", "concealer", "powder", "setting\\s+(?:powder|spray)", "primer",
               "blush", "bronzer", "highlighter", "contour", "eyeshadow", "eye\\s+shadow", "eyeliner", "eye\\s+liner",
               "mascara", "brow\\s+(?:pencil|gel|pomade|powder)", "eyebrow", "lipstick", "lip\\s+gloss", "lip\\s+liner",
               "lip\\s+stain", "lip\\s+balm", "lip\\s+(?:oil|plumper|mask|scrub)", "chapstick", "carmex", "blistex",
               "false\\s+eyelashes", "lashes", "lash\\s+glue", "makeup\\s+(?:brush(?:es)?|sponges?|remover|bag)",
               "beauty\\s+blender", "makeup\\s+wipes", "nail\\s+polish", "nail\\s+lacquer", "nail\\s+(?:polish\\s+remover|"
               "file|clippers?|art|tips|glue|kit|strengthener|treatment|stickers|wraps)", "press-?on\\s+nails", "gel\\s+polish",
               "top\\s+coat", "base\\s+coat", "manicure", "pedicure\\s+kit", "cuticle", "fragrance", "perfume", "cologne",
               "eau\\s+de\\s+(?:parfum|toilette|cologne)", "body\\s+splash", "parfum", "face\\s+wash", "facial\\s+cleanser",
               "cleanser", "micellar", "toner", "serum", "face\\s+serum", "moisturizer", "face\\s+cream", "night\\s+cream",
               "eye\\s+cream", "anti-?aging", "retinol", "acne", "pimple\\s+patch", "face\\s+mask", "sheet\\s+masks?",
               "facial\\s+mask", "peel", "exfoliat\\w+", "sunscreen", "sunblock", "spf\\s+\\d+", "sun\\s+care", "self[- ]tanner",
               "bronzing\\s+lotion", "tanning\\s+lotion", "after\\s+sun", "aloe\\s+vera\\s+gel", "skin\\s+care", "skincare",
               "beauty\\s+tools?", "tweezers", "eyelash\\s+curler", "makeup\\s+mirror", "compact\\s+mirror", "facial\\s+roller",
               "jade\\s+roller", "gua\\s+sha", "facial\\s+steamer", "cosmetic\\s+bag", "vanity\\s+case", "beauty\\s+kit",
               "gift\\s+set\\s+fragrance", "fragrance\\s+gift\\s+set", "body\\s+mist\\s+gift", "hair\\s+care", "detangler",
               "texturizer", "perm", "relaxer", "bleach\\s+kit", "toning", "purple\\s+shampoo", "lotion\\s+spf", "bb\\s+cream",
               "cc\\s+cream", "tinted\\s+moisturizer", "nail\\s+care", "hair\\s+removal\\s+(?:device|laser)",
               "dermaplaning", "lip\\s+care", "beauty\\s+supplement", "lip\\s+kit", "eyeshadow\\s+palette", "palette"]),
    # --- household supplies
    (16, "s", ["odor\\s+absorbers?", "fridge-n-freezer", "paper\\s+towels?", "toilet\\s+paper", "bath\\s+tissue", "facial\\s+tissues?", "tissues", "kleenex",
               "napkins", "paper\\s+plates?", "plastic\\s+(?:cups|plates|cutlery|forks|spoons|utensils)", "disposable\\s+(?:plates|cups|cutlery|bowls|tableware)",
               "solo\\s+cups", "aluminum\\s+foil", "foil", "plastic\\s+wrap", "cling\\s+wrap", "wax\\s+paper", "parchment\\s+paper",
               "freezer\\s+paper", "zip(?:per)?\\s*(?:lock|top)?\\s+bags", "ziploc", "storage\\s+bags", "sandwich\\s+bags",
               "freezer\\s+bags", "snack\\s+bags", "trash\\s+bags?", "garbage\\s+bags?", "kitchen\\s+bags", "lawn\\s+bags",
               "coffee\\s+filters?", "laundry\\s+detergent", "detergent", "fabric\\s+softener", "dryer\\s+sheets", "bleach",
               "stain\\s+remover", "laundry\\s+pods", "tide", "gain", "downy", "oxiclean", "dish\\s+soap", "dishwashing\\s+liquid",
               "dish\\s+detergent", "dishwasher\\s+(?:detergent|pods|tablets|rinse)", "cascade", "dawn", "sponges?", "scrubbers?",
               "scrub\\s+brush", "steel\\s+wool", "cleaners?", "all[- ]purpose\\s+cleaner", "disinfect\\w*", "lysol", "clorox",
               "cleaning\\s+wipes", "disinfecting\\s+wipes", "glass\\s+cleaner", "windex", "toilet\\s+bowl\\s+cleaner",
               "bathroom\\s+cleaner", "floor\\s+cleaner", "mop", "mops", "swiffer", "brooms?", "dustpans?", "dusters?",
               "vacuum\\s+bags", "air\\s+fresheners?", "febreze", "glade", "odor\\s+eliminator", "plug-?ins", "wax\\s+melts",
               "scented\\s+oils", "candles?", "matches", "lighters?", "batteries", "battery", "light\\s+bulbs?", "led\\s+bulbs?",
               "insect\\s+(?:killer|repellent|spray)", "bug\\s+spray", "pest\\s+control", "roach", "ant\\s+(?:killer|bait|traps?)",
               "mouse\\s+traps?", "rat\\s+traps?", "fly\\s+(?:traps?|swatter|paper)", "mosquito", "repellent", "weed\\s+killer",
               "drain\\s+(?:cleaner|opener)", "drano", "rubber\\s+gloves", "cleaning\\s+gloves", "cleaning\\s+cloths?",
               "microfiber\\s+cloths?", "paper\\s+bowls", "cups\\s+disposable", "straws", "toothpicks", "cupcake\\s+liners\\s+paper",
               "aluminum\\s+pans", "foil\\s+pans", "baking\\s+cups\\s+paper", "lint\\s+roller", "shoe\\s+polish", "bleach\\s+tablets",
               "septic", "water\\s+softener\\s+salt", "ice\\s+melt", "charcoal", "lighter\\s+fluid", "firelogs?", "fire\\s+starters?",
               "hand\\s+warmers", "dehumidifier\\s+refill", "damprid", "moth\\s+balls", "cedar\\s+blocks", "carpet\\s+cleaner",
               "furniture\\s+polish", "pledge", "magic\\s+eraser", "scouring\\s+pads?", "dish\\s+rack", "laundry\\s+baskets?",
               "clothes\\s?pins", "hangers", "ironing\\s+board", "iron\\s+steam", "starch\\s+spray", "wrinkle\\s+release"]),
    # --- kitchen & dining
    (17, "s", ["cake\\s+set", "bake\\s+(?:&|and)\\s+decorate", "bag\\s+clips?", "chip\\s+clips?", "piping\\s+tips", "keurig\\s+(?:coffee\\s+maker|brewer)", "cookware", "pots?", "pans", "frying\\s+pans?", "skillets?", "saucepans?", "dutch\\s+ovens?", "stock\\s?pots?",
               "bakeware", "baking\\s+(?:sheets?|pans?|dish(?:es)?)", "cake\\s+pans?", "muffin\\s+(?:pans?|tins?)", "cupcake\\s+liners",
               "baking\\s+cups", "cookie\\s+sheets?", "casserole\\s+dish", "pie\\s+pans?", "loaf\\s+pans?", "cooling\\s+racks?",
               "rolling\\s+pins?", "mixing\\s+bowls?", "measuring\\s+(?:cups|spoons)", "utensils?", "spatulas?", "whisks?",
               "ladles?", "tongs", "can\\s+openers?", "peelers?", "graters?", "colanders?", "strainers?", "cutting\\s+boards?",
               "cheese\\s+boards?", "charcuterie\\s+boards?", "serving\\s+(?:boards?|trays?|platters?|bowls?)", "platters?",
               "knives", "knife\\s+(?:set|block)", "chef'?s\\s+knife", "cutlery\\s+set", "flatware", "silverware", "dinnerware",
               "plates", "bowls", "mugs?", "cups\\s+(?:set|ceramic|glass)", "drinkware", "glassware", "tumblers?", "water\\s+bottles?",
               "travel\\s+mugs?", "pitchers?", "carafes?", "wine\\s+glasses", "food\\s+storage\\s+containers?", "containers?",
               "tupperware", "pyrex", "lunch\\s+(?:box(?:es)?|bags?)", "thermos", "coffee\\s+makers?", "coffee\\s+maker",
               "espresso\\s+machine", "french\\s+press", "kettles?", "toasters?", "toaster\\s+ovens?", "blenders?",
               "food\\s+processors?", "mixers?\\s+stand", "stand\\s+mixer", "hand\\s+mixer", "slow\\s+cookers?", "crock-?pot",
               "pressure\\s+cookers?", "instant\\s+pot", "air\\s+fryers?", "rice\\s+cookers?", "microwaves?", "griddles?",
               "waffle\\s+makers?", "juicers?", "can\\s+opener\\s+electric", "kitchen\\s+scale", "timers?", "trivets?",
               "pot\\s+holders?", "oven\\s+mitts?", "aprons?", "dish\\s+towels?", "kitchen\\s+towels?", "placemats?",
               "table\\s?cloths?", "napkin\\s+rings", "water\\s+filters?", "filter\\s+pitcher", "brita", "pur\\s+filter",
               "ice\\s+cube\\s+trays?", "popsicle\\s+molds?", "cookie\\s+cutters?", "piping\\s+(?:bags|tips)", "cake\\s+stand",
               "cake\\s+decorating\\s+(?:tools|kit|tips)", "candy\\s+molds?", "chocolate\\s+molds?", "silicone\\s+molds?",
               "baking\\s+mats?", "kitchen\\s+gadgets?", "spice\\s+racks?", "canisters?", "bread\\s+box", "butter\\s+dish",
               "salt\\s+and\\s+pepper\\s+shakers", "grinders?", "mortar", "corkscrew", "bottle\\s+opener", "jar\\s+opener",
               "mason\\s+jars?", "canning\\s+(?:jars|lids|supplies)", "lids", "reusable\\s+(?:bags|straws|containers)",
               "bento", "chopsticks", "skewers", "grill\\s+tools", "thermometer\\s+meat", "meat\\s+thermometer", "baster",
               "funnel", "sifter", "zester", "mandoline", "garlic\\s+press", "pizza\\s+(?:cutter|stone|pan)", "tortilla\\s+warmer",
               "egg\\s+cooker", "popcorn\\s+(?:maker|machine|popper)", "ice\\s+cream\\s+maker", "soda\\s?stream", "dispensers?",
               "kitchen\\s+appliances?", "small\\s+appliances?", "cake\\s+carrier", "pie\\s+carrier", "serveware", "teapot",
               "tea\\s+infuser", "tea\\s+kettle", "coffee\\s+grinder", "creamer\\s+pitcher", "gravy\\s+boat", "ramekins?",
               "kitchen\\s+linens", "dish\\s+cloths?", "cupcake\\s+stand", "dessert\\s+stand", "candy\\s+dish", "cookie\\s+jar",
               "bowl\\s+set", "plate\\s+set", "dinnerware\\s+set"]),
    # --- home
    (18, "s", ["bedding", "comforters?", "quilts?", "bed\\s+sheets?", "sheet\\s+sets?", "pillowcases?", "pillows?",
               "throw\\s+pillows?", "blankets?", "throws?", "duvets?", "mattress(?:es)?", "mattress\\s+(?:pads?|toppers?)",
               "bath\\s+towels?", "towels?", "towel\\s+sets?", "washcloths?", "bath\\s+mats?", "bath\\s+rugs?", "shower\\s+curtains?",
               "rugs?", "area\\s+rugs?", "doormats?", "curtains?", "drapes", "blinds", "window\\s+(?:panels?|treatments?)",
               "wall\\s+(?:art|decor|decals?|clocks?|shelf|shelves|mirror)", "mirrors?", "picture\\s+frames?", "frames",
               "vases?", "decor", "home\\s+decor", "decorative\\s+\\w+", "figurines?", "lamps?", "lighting", "string\\s+lights",
               "night\\s?lights?", "furniture", "chairs?", "tables?", "sofas?", "couch(?:es)?", "futons?", "dressers?",
               "nightstands?", "bookcases?", "bookshelves", "shelves", "shelving", "cabinets?", "desks?", "ottomans?",
               "benches", "stools?", "bed\\s+frames?", "headboards?", "storage\\s+(?:bins?|boxes?|baskets?|cubes?|totes?|containers?|ottoman)",
               "baskets?", "bins", "organizers?", "closet\\s+(?:organizer|system)", "hooks", "coat\\s+racks?", "shoe\\s+racks?",
               "laundry\\s+hampers?", "hampers?", "wastebaskets?", "trash\\s+cans?", "clocks?", "plush\\s+throw",
               "pillow\\s+inserts?", "cushions?", "slipcovers?", "table\\s+runners?", "candle\\s+holders?", "lanterns?",
               "wreaths?", "artificial\\s+(?:plants?|flowers?)", "faux\\s+(?:plants?|flowers?)", "fans?", "space\\s+heaters?",
               "heaters?", "air\\s+purifiers?", "dehumidifiers?", "vacuums?", "vacuum\\s+cleaners?", "steam\\s+mops?",
               "irons", "sewing\\s+machines?", "bed\\s+rails?", "toddler\\s+beds?", "beds", "bunk\\s+beds?", "day\\s?beds?",
               "crib\\s+bumpers", "nursery\\s+decor", "growth\\s+charts?", "wall\\s+decals?", "decals", "canopy",
               "tapestr(?:y|ies)", "bath\\s+accessories", "soap\\s+dispensers?", "toothbrush\\s+holders?", "tissue\\s+box\\s+covers?",
               "shower\\s+caddy", "towel\\s+bars?", "toilet\\s+brush", "plunger", "step\\s+stools?", "safes?", "doorstops?"]),
    # --- hardware & tools
    (31, "s", ["tools?", "tool\\s+sets?", "tool\\s+kits?", "drills?", "drill\\s+bits?", "screwdrivers?", "wrenches?", "hammers?",
               "pliers", "saws?", "sanders?", "socket\\s+sets?", "tape\\s+measures?", "levels?", "utility\\s+knives?", "box\\s+cutters?",
               "tool\\s+box(?:es)?", "workbench", "ladders?", "paint", "paint\\s+brushes?", "rollers\\s+paint", "primer\\s+paint",
               "caulk", "spackle", "sandpaper", "glue\\s+gun", "super\\s+glue", "epoxy", "duct\\s+tape", "electrical\\s+tape",
               "screws", "nails\\s+(?:box|common|finishing)", "bolts", "nuts\\s+and\\s+bolts", "anchors", "hinges?", "door\\s+knobs?",
               "locks?", "padlocks?", "deadbolts?", "extension\\s+cords?", "power\\s+strips?", "surge\\s+protectors?", "outlets?",
               "light\\s+switch(?:es)?", "wire", "flashlights?", "headlamps?", "work\\s+lights?", "smoke\\s+detectors?",
               "carbon\\s+monoxide", "fire\\s+extinguishers?", "plumbing", "faucets?", "shower\\s+heads?", "pipe", "fittings",
               "hearing\\s+protection", "earmuffs\\s+safety", "safety\\s+glasses", "work\\s+gloves", "rubber\\s+flooring",
               "flooring", "tiles?", "lumber", "plywood", "weather\\s+strip(?:ping)?", "insulation", "air\\s+filters?",
               "furnace\\s+filters?", "hvac", "generators?", "air\\s+compressors?", "pressure\\s+washers?", "shop\\s+vac",
               "wet\\s+dry\\s+vac", "stud\\s+finder", "multimeter", "hardware", "mailboxes?", "house\\s+numbers"]),
    # --- lawn, garden & floral
    (32, "s", ["garden", "gardening", "lawn", "lawn\\s+mowers?", "mowers?", "trimmers?\\s+string", "string\\s+trimmers?",
               "leaf\\s+blowers?", "hedge\\s+trimmers?", "hoses?", "garden\\s+hose", "sprinklers?", "nozzles?", "planters?",
               "pots\\s+plant", "flower\\s+pots?", "potting\\s+soil", "soil", "mulch", "fertilizers?", "plant\\s+food", "seeds\\s+garden",
               "seed\\s+packets?", "grass\\s+seed", "bird\\s?seed", "bird\\s+feeders?", "birdhouses?", "patio", "outdoor\\s+furniture",
               "patio\\s+(?:chairs?|tables?|sets?|umbrellas?|furniture|cushions?)", "outdoor\\s+(?:cushions?|pillows?|rugs?|lights?|decor)",
               "grills?", "smokers?", "fire\\s+pits?", "chimineas?", "hammocks?", "gazebos?", "canopies", "umbrellas?\\s+patio",
               "shovels?", "rakes?", "hoes?", "pruners?", "shears", "wheelbarrows?", "garden\\s+gloves", "live\\s+plants?",
               "plants?", "succulents?", "flowers", "bouquets?", "roses", "fresh\\s+flowers", "floral\\s+arrangements?",
               "orchids?", "bonsai", "trees?", "shrubs?", "bulbs\\s+flower", "flower\\s+bulbs", "pool\\s+(?:supplies|chemicals|toys|floats)",
               "pools?", "pool\\s+floats?", "solar\\s+lights?", "landscape", "edging", "pavers", "weed\\s+barrier", "trellis",
               "greenhouses?", "compost", "rain\\s+barrels?", "snow\\s+shovels?", "snow\\s+blowers?", "deer\\s+repellent"]),
    # --- pet
    (19, "s", ["dog\\s+food", "cat\\s+food", "puppy\\s+food", "kitten\\s+food", "pet\\s+food", "wet\\s+(?:dog|cat)\\s+food",
               "dry\\s+(?:dog|cat)\\s+food", "dog\\s+treats?", "cat\\s+treats?", "pet\\s+treats?", "rawhide", "dental\\s+chews",
               "bully\\s+sticks", "chew\\s+toys?", "dog\\s+toys?", "cat\\s+toys?", "pet\\s+toys?", "cat\\s+litter", "litter",
               "litter\\s+box(?:es)?", "scratching\\s+posts?", "cat\\s+trees?", "leashes?", "collars?", "harness(?:es)?",
               "dog\\s+bowls?", "pet\\s+bowls?", "feeders?", "waterers?", "pet\\s+fountains?", "crates?", "kennels?", "carriers?\\s+pet",
               "pet\\s+carriers?", "pet\\s+gates?", "dog\\s+houses?", "flea\\s+(?:and|&)\\s+tick", "flea", "tick\\s+prevention",
               "dewormer", "pet\\s+(?:shampoo|wipes|grooming|brush|nail\\s+clippers?|stain|odor|supplies|vitamins|medication)",
               "puppy\\s+pads", "training\\s+pads", "pee\\s+pads", "poop\\s+bags", "waste\\s+bags", "pooper\\s+scooper",
               "aquariums?", "fish\\s+tanks?", "fish\\s+food", "aquarium\\s+\\w+", "bird\\s+food", "bird\\s+cages?",
               "hamster", "guinea\\s+pig", "rabbit\\s+food", "small\\s+animal", "reptile", "terrarium", "hay", "chew\\s+sticks",
               "catnip", "pet\\s+(?:gate|door|ramp|stairs|steps)", "dog\\s+(?:ramp|stairs|steps|gate|door)", "milk\\s+replacer",
               "kitty", "meow\\s+mix", "friskies", "purina", "pedigree", "iams", "fancy\\s+feast", "milk-?bone", "greenies",
               "beggin", "ol'\\s+roy", "special\\s+kitty", "vibrant\\s+life", "blue\\s+buffalo", "rachael\\s+ray\\s+nutrish",
               "temptations", "whiskas", "tidy\\s+cats", "fresh\\s+step", "arm\\s+&\\s+hammer\\s+litter"]),
    # --- school, office & crafts
    (20, "s", ["pens?", "pencils?", "markers?", "highlighters", "crayons?", "colored\\s+pencils", "erasers?", "notebooks?",
               "composition\\s+books?", "binders?", "folders?", "paper\\s+(?:copy|printer|construction|loose\\s+leaf)",
               "copy\\s+paper", "printer\\s+paper", "construction\\s+paper", "index\\s+cards", "sticky\\s+notes", "post-?it",
               "staplers?", "staples", "scissors", "glue\\s+sticks?", "school\\s+glue", "tape\\s+dispenser", "scotch\\s+tape",
               "rulers?", "calculators?", "backpacks?", "pencil\\s+(?:cases?|pouch|sharpeners?)", "planners?", "calendars?",
               "journals?", "envelopes", "labels", "label\\s+maker", "printer\\s+ink", "ink\\s+cartridges?", "toner\\s+cartridge",
               "desk\\s+organizer", "file\\s+folders?", "filing", "clipboards?", "whiteboards?", "dry\\s+erase", "chalk",
               "craft\\s+(?:paint|supplies|kit|paper|foam|sticks)", "acrylic\\s+paint", "paint\\s+set", "watercolors?",
               "canvas", "easels?", "yarn", "crochet", "knitting", "sewing\\s+(?:kit|thread|supplies|pattern)", "thread",
               "fabric", "quilting", "embroidery", "cross\\s+stitch", "beads", "beading", "stickers", "scrapbook\\w*",
               "stamps", "stencils?", "glitter", "pom\\s+poms", "pipe\\s+cleaners", "felt", "ribbon", "craft\\s+wire",
               "modeling\\s+clay", "polymer\\s+clay", "play-?doh", "slime\\s+kit", "coloring\\s+books?", "sketch(?:book|pad)",
               "drawing\\s+paper", "art\\s+set", "paint\\s+brushes\\s+art", "rubber\\s+stamps", "hot\\s+glue", "glue\\s+gun\\s+sticks",
               "paper\\s+clips", "binder\\s+clips", "push\\s+pins", "thumbtacks", "rubber\\s+bands", "shipping\\s+(?:boxes|supplies)",
               "bubble\\s+mailers", "packing\\s+tape", "office\\s+chair", "desk\\s+lamp", "shredder", "laminator"]),
    # --- toys, books & games
    (21, "s", ["toys?", "dolls?", "action\\s+figures?", "figures?", "playsets?", "play\\s+sets?", "lego", "legos",
               "building\\s+(?:blocks|sets?|bricks)", "blocks", "puzzles?", "jigsaw", "board\\s+games?", "card\\s+games?", "games?",
               "plush", "plushies", "stuffed\\s+(?:animals?|toys?)", "teddy\\s+bears?", "ride-?ons?", "ride\\s+on", "tricycles?",
               "scooters?", "balls?\\s+toy", "play\\s+kitchen", "dollhouse", "toy\\s+cars?", "die-?cast", "hot\\s+wheels",
               "matchbox", "trains?\\s+toy", "train\\s+sets?", "rc\\s+cars?", "remote\\s+control", "drones?", "nerf", "water\\s+guns?",
               "bubbles", "bubble\\s+machine", "kites?", "slime", "play\\s+dough", "kinetic\\s+sand", "sandbox", "swing\\s+sets?",
               "trampolines?", "playhouses?", "play\\s+tents?", "ball\\s+pits?", "educational\\s+toys?", "learning\\s+toys?",
               "stem\\s+(?:kit|toy)", "science\\s+kit", "magic\\s+kit", "pretend\\s+play", "dress-?up\\s+(?:set|trunk)",
               "costume\\s+accessories", "fidget", "yo-?yos?", "rubik", "trading\\s+cards", "pokemon\\s+cards", "barbie",
               "funko", "squishmallows?", "fisher-?price", "little\\s+tikes", "step2", "melissa\\s*&\\s*doug", "vtech",
               "leapfrog", "baby\\s+einstein", "shape\\s+sorter", "stacking\\s+(?:cups|rings)", "rattles?", "musical\\s+toys?",
               "toy\\s+box", "play\\s+mats?", "activity\\s+(?:table|cube|toy)", "bath\\s+toys?", "pull\\s+toys?", "push\\s+toys?",
               "walker\\s+toy", "rocking\\s+horse", "wagons?", "sleds?", "pool\\s+toys", "sidewalk\\s+chalk", "books?",
               "storybooks?", "novels?", "board\\s+books?", "comics?", "graphic\\s+novels?", "magazines?"]),
    # --- seasonal & party
    (22, "s", ["party\\s+supplies", "party\\s+favors?", "balloons?", "banners?", "streamers", "confetti", "party\\s+(?:plates|cups|napkins|decorations?|hats|bags)",
               "pinatas?", "gift\\s+wrap", "wrapping\\s+paper", "gift\\s+bags?", "gift\\s+boxes?", "gift\\s+tags", "tissue\\s+paper",
               "bows", "greeting\\s+cards?", "birthday\\s+cards?", "cards\\s+greeting", "birthday\\s+candles?", "cake\\s+toppers?",
               "cupcake\\s+toppers?", "candle\\s+numbers?", "christmas\\s+(?:tree|ornaments?|lights|decorations?|decor|village)",
               "ornaments?", "tree\\s+toppers?", "tinsel", "garland", "halloween\\s+(?:decorations?|decor)", "easter\\s+(?:baskets?|grass|decor)",
               "easter\\s+eggs\\s+plastic", "plastic\\s+eggs", "egg\\s+dye\\s+kit", "valentine'?s\\s+(?:cards|decor)",
               "st\\.?\\s+patrick'?s\\s+decor", "fourth\\s+of\\s+july\\s+decor", "thanksgiving\\s+decor", "seasonal\\s+decor",
               "holiday\\s+(?:decor|decorations?|village)", "nativity", "advent\\s+calendar\\s+decor", "menorah", "luminaries",
               "inflatables?", "yard\\s+(?:signs?|decor|stakes)", "light-?up\\s+\\w+\\s+(?:village|figure)", "village\\s+(?:pieces?|houses?)",
               "gnomes?", "plush\\s+gnomes?", "photo\\s+booth\\s+props", "party\\s+packs", "loot\\s+bags", "invitations",
               "thank\\s+you\\s+cards", "piñatas?", "fireworks", "sparklers", "noisemakers", "leis", "tiaras\\s+party",
               "tablecover", "table\\s+covers?\\s+plastic", "centerpieces?", "wedding\\s+(?:decor|favors?)", "baby\\s+shower\\s+decor",
               "graduation\\s+(?:decor|party)"]),
    # --- auto
    (24, "s", ["motor\\s+oil", "oil\\s+filters?", "antifreeze", "coolant", "windshield\\s+(?:washer|wipers?)", "wiper\\s+blades?",
               "car\\s+(?:wash|wax|care|battery|batteries|charger|seat\\s+covers?|mats|air\\s+freshener|accessories|cover|vacuum|polish)",
               "floor\\s+mats\\s+car", "tires?", "tire\\s+(?:inflator|gauge|shine)", "jumper\\s+cables", "jump\\s+starter",
               "spark\\s+plugs?", "brake\\s+(?:fluid|pads?)", "transmission\\s+fluid", "power\\s+steering", "fuel\\s+(?:treatment|additive|injector)",
               "gas\\s+cans?", "automotive", "headlights?\\s+(?:bulbs?|restoration)", "tail\\s+lights?", "trailer\\s+hitch",
               "hitch", "tow\\s+straps?", "ratchet\\s+straps", "cargo\\s+(?:carrier|net)", "steering\\s+wheel\\s+cover",
               "dash\\s+cam", "license\\s+plate\\s+frame", "leather\\s+conditioner", "detailing", "armor\\s+all", "auto\\s+parts?",
               "glider\\s+hitch", "fifth\\s+wheel", "rv\\s+(?:supplies|accessories)"]),
    # --- electronics
    (25, "s", ["tvs?", "televisions?", "smart\\s+tv", "laptops?", "computers?", "tablets?\\s+(?:android|ipad|kindle)", "ipads?",
               "monitors?\\s+computer", "computer\\s+monitors?", "keyboards?", "mouse\\s+(?:wireless|gaming|optical)", "mice",
               "headphones", "earbuds", "earphones", "airpods", "speakers?", "bluetooth\\s+speakers?", "soundbars?",
               "chargers?", "charging\\s+(?:cables?|cords?|stations?|pads?)", "usb\\s+(?:cables?|drives?|hubs?|chargers?|adapters?)",
               "cables?", "hdmi", "adapters?", "power\\s+banks?", "portable\\s+chargers?", "phone\\s+cases?", "cases\\s+phone",
               "screen\\s+protectors?", "cell\\s+phones?", "smartphones?", "prepaid\\s+phones?", "iphones?", "phones?", "smartwatch(?:es)?",
               "fitness\\s+trackers?", "cameras?", "webcams?", "printers?", "routers?", "modems?", "hard\\s+drives?", "ssd",
               "memory\\s+cards?", "sd\\s+cards?", "flash\\s+drives?", "video\\s+game\\s+consoles?", "gaming\\s+(?:headset|controller|console|chair)",
               "controllers?", "xbox", "playstation", "nintendo", "streaming\\s+(?:device|stick)", "roku", "fire\\s+tv",
               "chromecast", "alexa", "echo\\s+dot", "smart\\s+(?:speaker|plug|bulb|home)", "radios?", "walkie\\s+talkies?",
               "projectors?", "e-?readers?", "kindle", "headsets?", "microphones?", "batteries\\s+rechargeable", "electronics",
               "tripods?", "selfie\\s+sticks?", "car\\s+mounts?\\s+phone", "phone\\s+(?:mounts?|holders?|stands?)",
               "surge\\s+protector\\s+usb", "ink\\s+printer", "sound\\s+machine", "white\\s+noise\\s+machine", "alarm\\s+clocks?",
               "digital\\s+(?:frame|recorder)", "dvd\\s+player", "blu-ray\\s+player", "record\\s+player", "turntables?"]),
    # --- jewelry & accessories
    (26, "s", ["necklaces?", "bracelets?", "earrings?", "rings?\\s+(?:sterling|gold|silver|diamond|band|engagement|wedding)",
               "pendants?", "charms?", "anklets?", "jewelry", "jewellery", "watches", "wristwatch(?:es)?", "watch\\s+bands?",
               "sunglasses", "handbags?", "purses?", "wallets?", "clutch(?:es)?", "tote\\s+bags?", "totes?", "crossbody",
               "backpack\\s+purse", "keychains?", "key\\s+rings?", "jewelry\\s+(?:box|organizer|cleaner)", "brooch(?:es)?",
               "cufflinks", "tie\\s+clips?", "body\\s+jewelry", "nose\\s+rings?", "chains?\\s+(?:gold|silver|sterling)"]),
    # --- sports & outdoors
    (27, "s", ["exercise\\s+(?:bikes?|equipment|mats?|balls?|bands)", "yoga\\s+(?:mats?|blocks?|straps?)", "dumbbells?",
               "kettlebells?", "weights?", "weight\\s+(?:bench|set|plates)", "resistance\\s+bands?", "treadmills?",
               "ellipticals?", "rowing\\s+machines?", "jump\\s+ropes?", "pull-?up\\s+bars?", "fitness\\s+equipment", "foam\\s+rollers?",
               "bikes?", "bicycles?", "bike\\s+(?:helmets?|locks?|lights?|pumps?|accessories)", "helmets?", "skateboards?",
               "roller\\s+skates?", "inline\\s+skates", "basketballs?", "footballs?", "soccer\\s+balls?", "volleyballs?",
               "baseballs?", "softballs?", "bats", "golf\\s+(?:balls|clubs|bags?)", "tennis\\s+(?:balls|rackets?)", "pickleball",
               "badminton", "ping\\s+pong", "table\\s+tennis", "frisbees?", "cornhole", "camping", "tents?", "sleeping\\s+bags?",
               "sleeping\\s+pads?", "camp\\s+chairs?", "coolers?", "ice\\s+chests?", "lanterns?\\s+camping", "camp\\s+stoves?",
               "backpacking", "hiking", "fishing", "fishing\\s+(?:rods?|reels?|line|lures?|tackle|poles?)", "rods?\\s+and\\s+reels?",
               "reels?", "lures?", "tackle", "bait", "hunting", "ammunition", "ammo", "archery", "bows?\\s+(?:archery|compound|recurve)",
               "arrows?", "targets?", "binoculars?", "scopes?", "knives?\\s+(?:pocket|hunting|folding)", "pocket\\s+knives?",
               "multi-?tools?", "kayaks?", "paddles?", "life\\s+jackets?", "boating", "swim\\s+(?:goggles|caps?\\s+swim|fins)",
               "snorkel", "boxing\\s+gloves", "punching\\s+bags?", "mma", "sports\\s+(?:equipment|bags?)", "gym\\s+bags?",
               "water\\s+bottles?\\s+sports", "shaker\\s+bottles?", "trekking\\s+poles?", "compass", "hand\\s+warmers\\s+outdoor",
               "game\\s+tables?", "air\\s+hockey", "foosball", "dartboards?", "darts", "billiards?", "pool\\s+(?:cues?|tables?)",
               "arcade\\s+games?", "basketball\\s+hoops?", "goals?", "nets?", "ice\\s+skates?", "ski(?:s|ing)?", "snowboards?"]),
    (2, "w", ["cheddar", "mozzarella", "parmesan", "provolone", "swiss\\s+cheese", "colby", "monterey\\s+jack", "pepper\\s+jack", "feta", "gouda", "brie", "cheese", ]),
    (6, "w", ["beans", "black\\s+beans", "pinto\\s+beans", "kidney\\s+beans", "navy\\s+beans", "great\\s+northern\\s+beans", "cannellini", "garbanzo\\s+beans", "chickpeas", "butter\\s+beans", "lima\\s+beans", "black[- ]eyed\\s+peas", "field\\s+peas", "lentils?", "urad", "mung\\s+beans", ]),
]


_META_CHARS = set("\\[(?*+|{.^$")


def _literal_prefix(fragment):
    out = []
    for ch in fragment:
        if ch in _META_CHARS:
            break
        out.append(ch)
    # a quantifier after the last literal makes it optional ("tees?"): drop that character
    if len(out) < len(fragment) and fragment[len(out)] in "?*{":
        out = out[:-1]
    return "".join(out)


def _compile_lexicon():
    """Phrases indexed by their first two literal letters, so a name is matched by trying only the phrases that can
    start at each word (one big alternation tried at every character costs ~5 ms per name)."""
    entries = []
    for cat, strength, phrases in LEXICON:
        for p in phrases:
            entries.append((p, cat, strength))
    entries.sort(key=lambda e: -len(e[0]))                  # longest first: "peanut butter cups" before "peanut butter"
    index, short = {}, []
    for p, cat, strength in entries:
        rx = re.compile(r"(?:" + p + r")(?![a-z])")
        meta = (cat, strength, p)
        pre = _literal_prefix(p)
        if len(pre) >= 2:
            index.setdefault(pre[:2], []).append((rx, meta))
        else:
            short.append((rx, meta, pre[:1]))
    return index, short


LEX_INDEX, LEX_SHORT = _compile_lexicon()
WORD_START_RX = re.compile(r"(?<![a-z0-9])[a-z0-9]")

FROZEN_RX = re.compile(r"\bfrozen\b|\bfreezer\s+(?:meals?|bags\s+of)\b|\(frozen\)", re.I)
NOT_FROZEN_RX = re.compile(r"\bfreeze[- ]dried\b|\bdisney\b|\bfrozen\s+(?:ii|2|elsa|anna|olaf|movie|themed|party|doll|toy|"
                           r"birthday|cake\s+topper|plates|cups|napkins|balloons?)\b|\bnon[- ]frozen\b", re.I)
CANNED_RX = re.compile(r"\bcanned\b|\bin\s+a\s+can\b|\b\d+(?:\.\d+)?\s*(?:oz|ounce)\.?\s+cans?\b|\bcans?\b(?!dy|ister|ola|"
                       r"opener)|\bjarred\b|\bjars?\b|\bshelf[- ]stable\b|\bpouch\b(?=.*\b(?:tuna|chicken|salmon)\b)", re.I)
DRIED_RX = re.compile(r"\bdried\b|\bdry\b|\bdehydrated\b", re.I)
DELI_RX = re.compile(r"\bdeli\b|\bsliced\b|\blunch\s*meat\b|\bshaved\b", re.I)
HERB_RX = re.compile(r"herbs|cilantro|parsley|basil|mint|dill|rosemary|thyme", re.I)
JARRED_CONDIMENT_RX = re.compile(r"peppers|jalap|garlic|onions|olives|artichokes", re.I)
HEAD_SPLIT_RX = re.compile(r",|\s[-–|]\s|\s\(|;|\s(?:with|w/|for|featuring|plus|includes?|bundled)\s", re.I)
WRAPPER_PREFIX_RX = re.compile(r"^\s*(?:\(\d+\s*-?\s*(?:pack|pk|count|ct)\)\s*)+", re.I)
# "Sardines in Olive Oil", "Cherries in Extra Heavy Syrup": what follows "in" is the packing, not the product
MEDIUM_RX = re.compile(r"\s+in\s+(?:[\w%'.&-]+\s+){0,3}?(?:olive\s+oil|oil|water|brine|juices?|syrup|sauce|gravy|broth)\b.*$",
                       re.I)
# claims are not products: "No Salt Added Corn", "Sugar Free Gelatin", "10g Protein Per Serving"
CLAIMS_RX = re.compile(r"\b(?:no\s+salt\s+added|low\s+sodium|reduced\s+sodium|lightly\s+salted|no\s+sugar\s+added|"
                       r"sugar[- ]free|zero\s+sugar|reduced\s+sugar|gluten[- ]free|dairy[- ]free|nut[- ]free|fat[- ]free|"
                       r"caffeine[- ]free|zero\s+added\s+sugar|no\s+added\s+sugar|non-?gmo|keto[- ]friendly|whole\s*30|\d+\s*g\s+protein(?:\s+per\s+serving)?)\b", re.I)
# lexicon phrases (as written in LEXICON) that name a form ("Coffee Capsules", "Peanut Butter Powder") or a flavour
# ("Instant Pudding Special Dark Chocolate"): they give way to the product noun next to them
FORM_PHRASES = {"capsules?", "tablets?", "caplets?", "softgels?", "pods", "k-?cups?", "bars", "snacks?", "drinks?",
                "beverages?", "powder", "cleaners?", "supplements?", "vitamins?", "toys?", "games?", "tools?",
                "containers?", "treats?", "mixers?", "shakes?", "dispensers?", "kits?", "sampler"}
FLAVOR_PHRASES = {"sea\\s+salt", "salt", "chocolates?", "caramels?", "honey", "cocoa", "butter", "sugar", "peanut\\s+butter",
                  "oils?", "olive\\s+oil", "coconut\\s+oil", "ranch", "cinnamon", "extracts?", "vinegar", "mustard", "ketchup",
                  "sriracha", "mint", "cheese", "cheddar", "parmesan", "mozzarella", "bacon", "syrup", "jam", "jelly", "salsa",
                  "queso", "pesto", "fudge", "toffee", "lemon\\s+pepper", "black\\s+pepper", "garlic", "onions?",
                  "jalape[nñ]os?", "peppers?", "apples?", "berries", "strawberr(?:y|ies)", "blueberr(?:y|ies)",
                  "raspberr(?:y|ies)", "cherries", "lemons?", "limes?", "oranges?", "mangos?", "coconuts?", "peach(?:es)?",
                  "watermelons?", "pineapples?", "bananas?", "cranberries", "pumpkins?", "chili", "maple\\s+syrup",
                  "cream\\s+cheese", "vanilla\\s+extract", "cookie\\s+butter", "dark\\s+chocolate", "milk\\s+chocolate"}
# product lines whose name decides the aisle whatever else the title says ("Hormel Compleats Chicken & Mashed Potatoes")
PRODUCT_LINES = {
    "compleats": 6, "dintymoore": 6, "chefboyardee": 6, "spaghettios": 6, "campbells": 6, "lunchables": 4,
    "hotpockets": 5, "leancuisine": 5, "uncrustables": 5, "eggo": 5, "poptarts": 29, "quakerchewy": 29,
    "naturevalley": 29, "nutrigrain": 29, "hamburgerhelper": 7, "chickenhelper": 7, "tunahelper": 7, "ricearoni": 7,
    "pastaroni": 7, "kraftmac": 7, "velveetashells": 7, "ensure": 10, "glucerna": 10, "pedialyte": 13, "gatorade": 10,
    "powerade": 10, "propel": 10, "torani": 10, "davinci": 10, "nespresso": 10, "shakenbake": 7, "oldbay": 28,
    "slapyamama": 28,
}
PRODUCT_LINE_RX = re.compile(r"\b(?:compleats|dinty\s+moore|chef\s+boyardee|spaghettios|campbell'?s|lunchables|"
                             r"hot\s+pockets|lean\s+cuisine|uncrustables|eggo|pop-?tarts|quaker\s+chewy|nature\s+valley|"
                             r"nutri-?grain|hamburger\s+helper|chicken\s+helper|tuna\s+helper|rice-a-roni|pasta\s+roni|"
                             r"kraft\s+mac|velveeta\s+shells|ensure|glucerna|pedialyte|gatorade|powerade|propel|torani|"
                             r"da\s?vinci|nespresso|shake\s+'?n\s+bake|"
                             r"old\s+bay|slap\s+ya\s+mama)\b", re.I)
# non-food words that are also scents, shapes or food packaging; inside the Food department they never outrank the path
FOOD_AMBIGUOUS_PHRASES = {"coolers?", "powder", "masks?", "cream", "oils?", "mists?", "pads", "platters?", "games?", "toys?",
                          "dispensers?", "trays?", "plush", "keychains?", "decor", "lamps?", "plates", "bowls", "sets?",
                          "kits?", "microwaves?", "grinders?", "frames", "bins", "baskets?", "towels?", "boxes", "candles?",
                          "pillows?", "blankets?", "mugs?", "tumblers?", "pitchers?", "containers?", "cups\\s+(?:set|ceramic|glass)",
                          "peel", "toner", "serum", "fragrance", "perfume", "lotion", "body\\s+butter", "soap", "lip\\s+balm",
                          "bark", "shells\\s+pasta"}
PRODUCE_PATH_RX = re.compile(r"/(?:fresh\s+)?produce|/fresh\s+(?:fruit|vegetables)", re.I)

# path fragments (lower case) mapped to a category; data/categories.json "path_rules" is the source, compiled here
_PATH_CACHE = {}


def _path_rules(cfg):
    key = id(cfg)
    if key not in _PATH_CACHE:
        rules = sorted(((frag.lower(), int(cat)) for frag, cat in cfg.get("path_rules", [])), key=lambda r: -len(r[0]))
        _PATH_CACHE[key] = rules
    return _PATH_CACHE[key]


def path_category(path, cfg):
    p = "/" + (path or "").lower().split("/", 1)[-1]          # drop "Home Page"
    for frag, cat in _path_rules(cfg):
        if frag in p:
            return cat
    return None


def _lexicon_matches(text):
    """Every product-noun match in text, left to right, non-overlapping: [(end, (category, strength, phrase))]."""
    t = text.lower()
    out, pos = [], 0
    for w in WORD_START_RX.finditer(t):
        i = w.start()
        if i < pos:
            continue
        hit = None
        for rx, meta in LEX_INDEX.get(t[i:i + 2], ()):
            m = rx.match(t, i)
            if m:
                hit = (m.end(), meta)
                break
        if hit is None:
            for rx, meta, first in LEX_SHORT:
                if not first or t[i] == first:
                    m = rx.match(t, i)
                    if m:
                        hit = (m.end(), meta)
                        break
        if hit:
            out.append(hit)
            pos = hit[0]
    return out


def _pick(matches, strength):
    """The product noun among the matches of one strength. English titles end with the noun, with two exceptions: a
    flavour after the noun describes it ("Instant Pudding Special Dark Chocolate", "Melba Snacks Sea Salt"), and a
    form word gives way to the noun before it ("Peanut Butter Powder", "Coffee Capsules")."""
    found = [meta for _, meta in matches if meta[1] == strength]
    while len(found) > 1 and found[-1][2] in FLAVOR_PHRASES:
        found.pop()
    if not found:
        return None
    if len(found) > 1 and found[-1][2] in FORM_PHRASES:
        earlier = [m for m in found[:-1] if m[2] not in FORM_PHRASES]
        real = [m for m in earlier if m[2] not in FLAVOR_PHRASES]
        if real or earlier:
            return (real or earlier)[-1]
    return found[-1]


def product_noun(name):
    """The product noun: a product line that decides the aisle ("Compleats", "Gatorade"); else a strong noun beats a
    weak one ("Tea ... Blueberry" is tea, "Hot Pepper Paste" is a paste), looked for in the head of the title (before
    the first comma, dash or "with"/"for" clause), then in the whole name. Returns (category, strength, phrase)."""
    name = name.replace("\u2019", "'").replace("\u2018", "'")
    line = PRODUCT_LINE_RX.search(name)
    if line:
        key = re.sub(r"[^a-z]", "", line.group(0).lower())
        return PRODUCT_LINES.get(key, 23), "s", "product line " + key
    name = WRAPPER_PREFIX_RX.sub("", name)
    name = MEDIUM_RX.sub(" ", name)
    name = CLAIMS_RX.sub(" ", name)
    head = HEAD_SPLIT_RX.split(name, 1)[0]
    mh, mn = _lexicon_matches(head), _lexicon_matches(name)
    return _pick(mh, "s") or _pick(mh, "w") or _pick(mn, "s") or _pick(mn, "w")


def exclusion(name, brand, path, dept_name, upc=None):
    """Why the item is not carried at all, or None."""
    n, p, b = name or "", (path or "").lower(), brand or ""
    if not MEDIA_EXEMPT_RX.search(n):
        if MEDIA_RX.search(n) and dept_name != "Books":
            return "media"
        if dept_name != "Books" and (";" in b or (PUBLISHER_RX.search(b) and not PUBLISHER_EXEMPT_RX.search(b + " " + n))):
            pn = product_noun(n)
            if pn is None or pn[0] == 21 or pn[0] in FOOD_CATS:
                # a record label or publisher on a title that names no product, or only a food word ("Soul Sauce" by
                # UMGD is an album); a real product under such a brand (a Warner Bros. baby blanket) stays
                return "media"
        if dept_name != "Books" and upc and str(upc).lstrip("0").startswith(("978", "979")) and len(str(upc).lstrip("0")) == 13:
            return "media"
        if dept_name != "Books" and SUBTITLE_RX.search(n) and PERSON_BRAND_RX.search(b.strip()) and not UNIT_RX.search(n):
            return "media"                               # "High-Hanging Fruit: Build Something Great..." by Mark Rampolla
    if TOBACCO_RX.search(n) and not STOP_SMOKING_RX.search(n) or "/tobacco" in p:
        if not STOP_SMOKING_RX.search(n):
            return "tobacco"
    if not EXPLICIT_NA_RX.search(n):
        if "/alcohol" in p or "/wine" in p or "/beer" in p or "/spirits" in p:
            if ALCOHOL_STRONG_RX.search(n) or not NONALCOHOLIC_RX.search(n):
                return "alcohol"
        elif ALCOHOL_STRONG_RX.search(n) and not NONALCOHOLIC_RX.search(n):
            pn = product_noun(n)
            if pn is None or pn[0] == 10:                # "Bourbon BBQ Sauce", "Bourbon BBQ Jerky": a flavour, not a drink
                return "alcohol"
    if any(k in p for k in ("/clothing", "apparel", "/shoes", "/costumes")) and not PET_RX.search(n):
        return "footwear" if "/shoes" in p else "apparel"
    is_pet = bool(PET_RX.search(n)) or "/pets/" in p or p.startswith("pets/")
    if (PET_BED_RX.search(n) or any(k in p for k in PET_BED_PATHS)) and is_pet and not PET_BED_EXEMPT_RX.search(n):
        noun = product_noun(n)
        if not (noun and noun[0] == 19 and re.search(r"\b(?:food|treats?|toys?|bowls?|leash|collar|harness|crate)\b", noun[2])):
            return "pet_bed"
    if FOOTWEAR_RX.search(n) and not FOOTWEAR_EXEMPT_RX.search(n):
        return "footwear"
    if COSTUME_RX.search(n) and not re.search(r"\bcostume\s+(?:jewelry|accessories|makeup|make-up|kit\s+makeup)\b", n, re.I):
        return "apparel"
    if b.strip().lower() in APPAREL_BRANDS and product_noun(n) is None:
        return "apparel"                                 # "No Boundaries Nb Women Casual", "Garanimals Gr Bg Furry Fleece Hood"
    m = APPAREL_RX.search(n)
    if m and not APPAREL_EXEMPT_RX.search(n):
        word = m.group(0).lower()
        if word.startswith("wig") and not COSTUME_RX.search(n):
            return None                                            # wigs are Beauty unless part of a costume
        if word in ("gloves", "glove", "belts", "belt") and not re.search(r"\b(?:winter|knit|leather|fashion|dress|driving|"
                                                                          r"touchscreen|fleece|wool|mittens?|women'?s|men'?s|"
                                                                          r"kids'?|boys'?|girls'?|ladies)\b", n, re.I):
            return None
        if word.startswith("pup") and not is_pet:
            return None
        if word in ("hood", "hoods") and not re.search(r"\b(?:fleece|sherpa|furry|knit|winter|baby|kids?|girls?|boys?)\b", n, re.I):
            return None
        if word in ("cape", "capes", "tiara", "tiaras", "scrunchie") and not is_pet:
            return None
        if word in ("polo", "polos") and not re.search(r"\bshirts?\b", n, re.I):
            return None
        if word in ("visor", "visors") and re.search(r"\b(?:sun\s+visor\s+(?:car|organizer)|car|auto|handspring|lcd)\b", n, re.I):
            return None
        if word == "outfit" or word == "outfits":
            if re.search(r"\bdoll\b", n, re.I):
                return None
        if word in ("tee", "tees") and not re.search(r"\b(?:shirt|cotton|graphic|crew|sleeve|v-neck)\b|\bxs\b|\bxl\b", n, re.I) \
                and not is_pet:
            return None
        if word in ("dress",) and re.search(r"\bdress\s+(?:shirt|socks)\b", n, re.I) is None and \
                re.search(r"\b(?:salad|french|ranch)\b", n, re.I):
            return None
        noun = product_noun(n)
        if noun and noun[0] not in FOOD_CATS and noun[2] not in GARMENTS and noun[0] in (16, 17, 18, 20, 21, 22, 24, 25, 31, 32) \
                and not is_pet and noun[2] not in ("blankets?",):
            # "Hooded Towel", "Sweater Storage Bag", "Doll Dress": the head noun is not the garment
            return None
        return "apparel"
    return None


DISCONTINUED_STRIP_RX = re.compile(r"\s*\*+\s*discontinu\w*[^*]*\*+\s*|\s*\(?\bdiscontinued\s+by\s+(?:manufacturer|supplier|"
                                   r"vendor)\)?\s*", re.I)


def placeholder(name, brand, price=None):
    """True when the listing's name does not identify a product, or the listing is a store display unit."""
    n = (name or "").strip()
    core = re.sub(r"^\s*(?:\(\d+\s*pack\)\s*)+", "", n, flags=re.I).strip()
    if not core or PLACEHOLDER_RX.search(core) or INGREDIENT_LIST_RX.search(core) or CODE_NAME_RX.search(core):
        return True
    b = (brand or "").strip().lower().strip(" .")
    if b and core.lower().strip(" .") == b and not re.search(r"\d", core) and product_noun(core) is None:
        return True                                   # "HUGGIES", "MOTIONS": the brand alone names no product
    if FIXTURE_RX.search(core):
        return True
    if DISPLAY_RX.search(core) and (price is None or price >= DISPLAY_PRICE_MIN or PIECE_COUNT_RX.search(core)):
        return True                                   # "312PC RLETTE PALLET", "Crest 32pc Cr Snstv Pdq3", "C&B SS Shipper"
    return False


def clean_name(name):
    """Remove feed markers ("***Discontinued***", "[Incomplete Data]") from a real product name.
    Returns (name, discontinued)."""
    disc = bool(DISCONTINUED_RX.search(name or ""))
    n = DISCONTINUED_STRIP_RX.sub(" ", name or "")
    n = MARKER_RX.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip(" -")
    return (n or (name or "").strip()), disc


# durable goods: a price per ounce or per count means nothing for them, wherever Walmart files them (a Fitbit weighs
# 0.28 oz, a wastebasket holds 145 fl oz). Categories that are durable by nature, plus durable nouns inside the care
# departments.
DURABLE_CATS = {17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 31, 32}
DURABLE_RX = re.compile(
    r"\b(?:wheelchairs?|walkers?|rollators?|canes?|crutch(?:es)?|braces?|supports?\s+(?:belt|brace)|monitors?|thermometers?|"
    r"scales?|massagers?|massage\s+(?:chair|cushion|gun)|humidifiers?|vaporizers?|nebulizers?|purifiers?|heating\s+pads?|"
    r"gates?|strollers?|car\s+seats?|cribs?|high\s?chairs?|bassinets?|playards?|swings?|bouncers?|rockers?|walkers?|"
    r"mirrors?|hair\s+dryers?|blow\s+dryers?|flat\s+irons?|curling\s+(?:irons?|wands?)|straighteners?|hot\s+brush|"
    r"trimmers?|shavers?|clippers?|electric\s+toothbrush(?:es)?|water\s+flossers?|trackers?|smart\s?watch(?:es)?|"
    r"containers?|receptacles?|wastebaskets?|bins?|baskets?|organi[sz]ers?|caddy|pillows?|cushions?|mattress(?:es)?|"
    r"seats?|benches|rails?|grab\s+bars?|commodes?|bed\s+pans?|reachers?|bottles?\s+warmers?|sterili[sz]ers?|"
    r"breast\s+pumps?|pumps?\s+(?:kit|set)|bags?|cases?|totes?|backpacks?|lamps?|lights?|fans?|heaters?|mats?|rugs?|"
    r"brushes|combs?|sponges?\s+(?:applicator|blender)|cosmetic\s+bags?|makeup\s+bags?|frames?|glasses|sunglasses|"
    r"contact\s+lens\s+cases?|pill\s+organi[sz]ers?|pill\s+boxes?|first\s+aid\s+kits?)\b", re.I)


def durable(name, nn=None):
    """True when the item is a durable good, which never gets a per-unit price."""
    if nn and nn[0] in DURABLE_CATS:
        return True
    return bool(DURABLE_RX.search(HEAD_SPLIT_RX.split(WRAPPER_PREFIX_RX.sub("", name or ""), 1)[0]))


def noun(name, path, dept, cfg):
    """The category the name supports, with a confidence: 3 = a multi-word strong noun or a product line ("instant
    pudding", "Gatorade"), 2 = a one-word strong noun ("soup") or a weak noun whose form the name states ("canned
    corn"), 1 = a weak noun whose aisle came only from the path ("corn"). Returns (category, confidence, phrase)."""
    n = name or ""
    m = product_noun(n)
    if m is None:
        return None
    lcat, strength, phrase = m
    p = (path or "").lower()
    pcat = path_category(path, cfg)
    food_context = dept["name"] == "Food" or (pcat in FOOD_CATS)
    frozen = bool(FROZEN_RX.search(n) or "/frozen" in p) and not NOT_FROZEN_RX.search(n)
    if strength == "w":
        if not food_context:
            return None
        if frozen:
            return 5, 2, phrase
        if lcat == 3 and DELI_RX.search(n):
            return 4, 2, phrase
        if lcat == 6 and (DRIED_RX.search(n) or re.search(r"\bbag\b|\b\d+(?:\.\d+)?\s*-?\s*(?:lbs?|pounds?)\b", n, re.I)):
            return 7, 2, phrase                                     # dried beans and lentils
        if CANNED_RX.search(n):
            if lcat == 1 and JARRED_CONDIMENT_RX.search(phrase) and re.search(r"\bjars?\b|\bjarred\b", n, re.I):
                return 11, 2, phrase
            return 6, 2, phrase
        if lcat == 1 and DRIED_RX.search(n):
            return (28, 2, phrase) if HERB_RX.search(phrase) else (9, 2, phrase)
        if pcat in FOOD_CATS and pcat != 7:
            return pcat, 1, phrase
        if "/pantry" in p or pcat == 7:
            # shelf-stable: jarred peppers, olives and garlic are condiments, dried herbs are spices, the rest is canned
            if lcat == 1 and HERB_RX.search(phrase):
                return 28, 1, phrase
            if lcat == 1 and JARRED_CONDIMENT_RX.search(phrase):
                return 11, 1, phrase
            return 6, 1, phrase
        return lcat, 1, phrase
    conf = 3 if ("\\s" in phrase or " " in phrase) else 2      # phrases are regex text: "peanut\\s+butter"
    cat = lcat
    if cat in FOOD_CATS and cat != 5 and frozen and re.search(r"\bfrozen\b", n, re.I):
        cat = 5
    if dept["name"] == "Food" and re.search(r"\bcereal\b", n, re.I) and not re.search(r"\b(?:bowls?|dispensers?|containers?)\b", n, re.I):
        return 29, 3, phrase
    if PET_RX.search(n) and re.search(r"\b(?:dog|cat|pet|puppy|kitten)\s+(?:food|treats?|toys?|chews?|biscuits?|bones?)\b",
                                      n, re.I) and not re.search(r"\b(?:hot|corn)\s+dogs?\b", n, re.I):
        return 19, 3, phrase
    return cat, conf, phrase


class PathStats:
    """How coherent each Walmart path is: the share of its items whose name names one category (confidence >= 2).
    A path where most items agree is a reliable label for the items whose names are vague; a catch-all path
    ("Pantry meal essentials") is not. Built over the whole snapshot, so it adapts to new departments."""
    MIN_ITEMS = 20
    MIN_SHARE = 0.6

    def __init__(self):
        from collections import Counter, defaultdict
        self._c = defaultdict(Counter)

    @staticmethod
    def _prefixes(path):
        parts = [x.strip().lower() for x in (path or "").split("/")[1:] if x.strip()]
        return ["/".join(parts[:i]) for i in range(len(parts), 1, -1)]   # deepest first, never the bare department

    def add(self, path, nn):
        if nn and nn[1] >= 2:
            for pre in self._prefixes(path):
                self._c[pre][nn[0]] += 1

    def lookup(self, path):
        """(category, share) of the deepest prefix with enough labelled items, or (None, 0)."""
        for pre in self._prefixes(path):
            c = self._c.get(pre)
            if c:
                total = sum(c.values())
                if total >= self.MIN_ITEMS:
                    cat, k = c.most_common(1)[0]
                    return (cat, k / total) if k / total >= self.MIN_SHARE else (None, k / total)
        return None, 0.0


def decide(nn, path, dept, cfg, stats=None, name=None):
    """Final category from the name's noun and the path (see the module docstring)."""
    static = path_category(path, cfg)
    dept_default = int(dept["default_category"])
    pcat, share = stats.lookup(path) if stats else (None, 0.0)
    pcat = pcat or static
    if nn is None:
        return pcat or dept_default
    cat, conf, phrase = nn
    if dept["name"] == "Pets":
        return 19                      # everything carried from Pets is for an animal (its clothing and beds are excluded)
    if dept["name"] in SPECIALTY_DEPTS and cat in GENERAL_MERCHANDISE and not (cat == 18 and RUG_RX.search(name or "")):
        # a crib bumper, a wedge pillow, a makeup mirror, a fish-tank lamp: a general-merchandise noun sold in Baby,
        # Pets, Health or Beauty stays that department's item, unless it is plainly an ordinary household item (an
        # area rug or a throw pillow filed under Baby, with nothing about babies in its name or path)
        ctx = SPECIALTY_CONTEXT.get(dept["name"])
        if ctx is None or ctx.search(name or "") or any(k in (path or "").lower() for k in SPECIALTY_PATHS.get(dept["name"], ())):
            return pcat if pcat and pcat not in GENERAL_MERCHANDISE else dept_default
        return cat
    if pcat is None or cat == pcat:
        return cat
    if (cat in FOOD_CATS) != (pcat in FOOD_CATS):
        # a non-food item in Food (a cheese board under Deli, coffee filters under Coffee) is common, so there a clear
        # name wins; a food word in a non-food department is usually a scent or flavour ("Cocoa Butter Body Balm",
        # "Flavored Water-Based Lube"), so there the path wins unless the phrase is unmistakable non-food
        if dept["name"] == "Food":
            return cat if conf >= 2 and phrase not in FOOD_AMBIGUOUS_PHRASES else pcat
        return cat if conf >= 3 and cat not in FOOD_CATS else pcat
    if cat in CARE_CATS and pcat in CARE_CATS and conf < 3:
        return pcat                    # health, personal care and beauty overlap ("Body Wash with Vitamin E"): the path
    if conf >= 3 and share < 0.85:
        return cat
    if conf == 2 and share < MIN_TRUST:
        return cat
    return pcat


MIN_TRUST = 0.6
SPECIALTY_DEPTS = {"Baby", "Pets", "Health and Medicine", "Pharmacy", "Personal Care", "Beauty", "Premium Beauty"}
GENERAL_MERCHANDISE = {16, 17, 18, 20, 21, 22, 23, 25, 26, 31, 32}
CARE_CATS = {13, 14, 15, 30}
# Walmart paths that hold only baby gear, whatever the item's name says ("Status Milano Swivel Glider With Ottoman")
RUG_RX = re.compile(r"\b(?:area\s+)?rugs?\b|\bthrow\s+pillows?\b", re.I)
SPECIALTY_PATHS = {"Baby": ("/nursery & decor", "/nursery storage", "/feeding", "/diapering", "/health & safety", "/baby activities", "/car seats", "/strollers",
                            "/baby travel", "/gliders", "/wipe warmers", "/baby bath", "/baby cribs", "/changing",
                            "/bassinets", "/crib and baby mattresses", "/playards", "/baby carriers", "/high chairs",
                            "/baby bedding/crib", "/baby dressers")}
SPECIALTY_CONTEXT = {
    "Baby": re.compile(r"\b(?:bab(?:y|ies)|infants?|newborns?|nursery|cribs?|toddlers?|kids?|child(?:ren)?|bassinets?|"
                       r"potty|diapers?|nursing|maternity|teeth\w*|stroller|car\s+seat|mobile|swaddl\w*|layette|"
                       r"months?|ages?\s+\d|rattles?|teethers?|pacifiers?|sippy|nursing|bibs?)\b", re.I),
    "Pets": None,                      # everything in Pets is for an animal
}


def category(name, brand, path, dept, cfg, stats=None):
    """The store category id for a carried item."""
    return decide(noun(name, path, dept, cfg), path, dept, cfg, stats, name)
