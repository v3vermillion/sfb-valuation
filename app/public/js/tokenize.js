// Shared tokenizer: the DB builder (Node) and the app (browser worker) import this same module,
// so an index built offline always agrees with what is typed into the search box.

const DIACRITICS = /[̀-ͯ]/g;

// Normalize text to a lowercase ASCII-ish form. "Bush's" -> "bushs", "Pen+Gear" -> "pen gear",
// "16oz" stays a single chunk until splitLetterDigit() splits it into "16" and "oz".
export function normalizeText(s) {
  return String(s)
    .normalize("NFKD")
    .replace(DIACRITICS, "")
    .toLowerCase()
    .replace(/['’`]/g, "")          // bush's -> bushs, kellogg's -> kelloggs
    .replace(/(\d)\s*%/g, "$1 percent ")   // "2% milk" -> "2 percent milk": keeps the fat grade a real word
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9.]+/g, " ");   // every other separator (incl. + / , - x ×) becomes a space
}

// Split a chunk such as "16oz", "5w-30"(already split on -), "2pk", "15.25oz" into letter and digit runs.
// Numbers keep one decimal point ("15.25"); a trailing "." is dropped ("15." -> "15").
function* splitLetterDigit(chunk) {
  const re = /(\d+(?:\.\d+)?)|([a-z]+)/g;
  let m;
  while ((m = re.exec(chunk)) !== null) yield m[0];
}

/** Tokens of a product name or query, in order, duplicates kept. */
export function tokenize(s) {
  const out = [];
  for (const chunk of normalizeText(s).split(" ")) {
    if (!chunk) continue;
    for (const t of splitLetterDigit(chunk)) out.push(t);
  }
  return out;
}

// Hyphenated brand words are also indexed joined, the way people type them: "Jell-O" -> jello, "Cheez-It" ->
// cheezit, "Pop-Tarts" -> poptarts, "Kool-Aid" -> koolaid, "Rice-A-Roni" -> ricearoni, "Q-tips" -> qtips.
export function joinedTokens(s) {
  const t = String(s).normalize("NFKD").replace(DIACRITICS, "").toLowerCase().replace(/['’`]/g, "");
  return (t.match(/[a-z0-9]+(?:-[a-z0-9]+)+/g) || []).map((w) => w.replace(/-/g, "")).filter((w) => /^[a-z]/.test(w) && w.length >= 4);
}

/** Sorted unique tokens (what the index stores per item). */
export function uniqueTokens(s) {
  return Array.from(new Set([...tokenize(s), ...joinedTokens(s)])).sort();
}

// The item a listing is: the last word of the name before its first comma or dash, once trailing quantities are
// stripped ("Huggies Little Movers Baby Diapers, Size 4" -> diapers; "Huggies Day Pack Diaper Bag" -> bag;
// "Coca-Cola Soda Pop 12 fl oz 12 Pack Cans" -> pop). A container word is a quantity only after a number.
const MEASURE = new Set(["oz", "ounce", "ounces", "fl", "fluid", "lb", "lbs", "pound", "pounds", "g", "gram", "grams", "kg", "mg", "mcg", "ml",
  "l", "liter", "liters", "litre", "litres", "gal", "gallon", "gallons", "qt", "quart", "quarts", "pt", "pint", "pints", "ct", "cnt", "count",
  "pk", "each", "ea", "x", "of", "size", "sq", "ft", "inch", "inches", "in", "mm", "cm", "percent"]);
const CONTAINER = new Set(["can", "cans", "bag", "bags", "box", "boxes", "bottle", "bottles", "jar", "jars", "cup", "cups", "pouch", "pouches",
  "tub", "tubs", "carton", "cartons", "case", "pack", "packs", "pc", "pcs", "piece", "pieces", "rolls", "sheets", "bars", "packets"]);
const HEAD_SKIP = new Set(["value", "family", "original", "classic", "new", "assorted", "variety", "fresh", "fruit", "vegetable", "vegetables"]);
export function headNoun(name) {
  // "Melton Coat For Dogs" is a coat, "Shampoo with Argan Oil" a shampoo: what follows for/with/by describes it
  const first = String(name).split(/,| - | \| /)[0];
  const lead = first.split(/\s+(?:for|with|by|w\/)\s+/i)[0];
  const toks = tokenize(lead.trim() ? lead : first);
  while (toks.length) {
    const t = toks[toks.length - 1];
    const afterNumber = toks.slice(-4, -1).some((x) => /^\d/.test(x));
    if (/^\d/.test(t) || MEASURE.has(t) || HEAD_SKIP.has(t) || (CONTAINER.has(t) && afterNumber)) toks.pop();
    else break;
  }
  return toks.length ? toks[toks.length - 1] : null;
}
