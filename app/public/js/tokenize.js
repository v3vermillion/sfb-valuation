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

/** Sorted unique tokens (what the index stores per item). */
export function uniqueTokens(s) {
  return Array.from(new Set(tokenize(s))).sort();
}
