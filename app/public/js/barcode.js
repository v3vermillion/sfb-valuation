// Barcode arithmetic shared by the app and its unit tests. Pure functions, no DOM.
//
// Covers: GS1 check digits, UPC-E expansion, any UPC/EAN -> GTIN-14 key (the crawler's gtin14()),
// store-printed variable-measure labels (UPC-A number system 2: item ref + price verifier + 4-digit price,
// per GS1 General Specifications §2.1.12.2 / §7.9.3, verified against the spec's worked examples),
// and IFPS produce PLU codes (4 digits 3000–4999; organic 9xxxx).

export const digitsOnly = (s) => String(s ?? "").replace(/\D/g, "");

/** GS1 mod-10 check digit for a body of digits (weights 3,1,3,1... from the right). */
export function checkDigit(body) {
  let total = 0;
  for (let i = 0; i < body.length; i++) {
    const d = body.charCodeAt(body.length - 1 - i) - 48;
    total += i % 2 === 0 ? d * 3 : d;
  }
  return (10 - (total % 10)) % 10;
}

export function hasValidCheckDigit(digits) {
  if (digits.length < 8) return false;
  return checkDigit(digits.slice(0, -1)) === Number(digits.at(-1));
}

/** Expand a UPC-E (8 digits incl. number system + check, or the 6 middle digits) to UPC-A (12 digits). */
export function upcEToUpcA(code) {
  let d = digitsOnly(code);
  if (d.length === 6) d = "0" + d + checkDigitForUpcE(d, "0");
  if (d.length === 7) d = d + checkDigitForUpcE(d.slice(1), d[0]);
  if (d.length !== 8 || (d[0] !== "0" && d[0] !== "1")) return null;
  const ns = d[0], x = d.slice(1, 7), c = d[7];
  const last = x[5];
  let mfr, prod;
  if (last === "0" || last === "1" || last === "2") { mfr = x.slice(0, 2) + last + "00"; prod = "00" + x.slice(2, 5); }
  else if (last === "3") { mfr = x.slice(0, 3) + "00"; prod = "000" + x.slice(3, 5); }
  else if (last === "4") { mfr = x.slice(0, 4) + "0"; prod = "0000" + x[4]; }
  else { mfr = x.slice(0, 5); prod = "0000" + last; }
  const body = ns + mfr + prod;
  const a = body + c;
  return checkDigit(body) === Number(c) ? a : body + checkDigit(body);
}

function checkDigitForUpcE(x, ns) {
  // check digit of a UPC-E equals the check digit of its UPC-A expansion
  const a = upcEToUpcA(ns + x + "0");   // placeholder check, recomputed below
  return a ? a.at(-1) : "0";
}

/**
 * Normalize a scanned/typed code to the database key.
 * @returns {{ gtin14: string, key: number, type: string, checkOk: boolean, digits: string } | null}
 */
export function toGtin14(raw, format) {
  let d = digitsOnly(raw);
  if (!d) return null;
  const fmt = String(format || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  let type = "GTIN";
  if (fmt === "UPCE" || (d.length === 8 && (d[0] === "0" || d[0] === "1") && fmt !== "EAN8")) {
    const a = upcEToUpcA(d);
    if (a) { d = a; type = "UPC-E"; }
  } else if (d.length === 8) type = "EAN-8";
  else if (d.length === 12) type = "UPC-A";
  else if (d.length === 13) type = d.startsWith("0") ? "UPC-A" : "EAN-13";
  else if (d.length === 14) type = "GTIN-14";
  else if (d.length === 11) { d = d + checkDigit(d); type = "UPC-A"; }   // UPC-A typed without its check digit
  if (d.length < 8 || d.length > 14) return null;
  const checkOk = hasValidCheckDigit(d);
  const gtin14 = d.padStart(14, "0");
  return { gtin14, key: Number(gtin14), type, checkOk, digits: d };
}

// ---- GS1 price verifier (variable measure, number system 2) ---------------------------------
const W2M = [0, 2, 4, 6, 8, 9, 1, 3, 5, 7];   // "2-" weighting
const W3 = [0, 3, 6, 9, 2, 5, 8, 1, 4, 7];    // "3" weighting
const W5P = [0, 5, 1, 6, 2, 7, 3, 8, 4, 9];   // "5+" weighting
const W5M = [0, 5, 9, 4, 8, 3, 7, 2, 6, 1];   // "5-" weighting
const inverse = (t) => { const inv = new Array(10); t.forEach((v, i) => (inv[v] = i)); return inv; };
const INV5P = inverse(W5P), INV5M = inverse(W5M);

/** Price verifier digit for a 4-digit price field (GS1 GenSpecs 7.9.3.1; example 2875 -> 9). */
export function priceVerifier4(p) {
  const [a, b, c, d] = String(p).padStart(4, "0").split("").map(Number);
  const sum = W2M[a] + W2M[b] + W3[c] + W5M[d];
  return INV5P[(sum * 3) % 10];
}

/** Price verifier digit for a 5-digit price field (GS1 GenSpecs 7.9.3.2; example 14685 -> 6). */
export function priceVerifier5(p) {
  const [a, b, c, d, e] = String(p).padStart(5, "0").split("").map(Number);
  const sum = W5P[a] + W2M[b] + W5M[c] + W5P[d] + W2M[e];
  return INV5M[(10 - (sum % 10)) % 10];
}

/**
 * Decode a store-printed price barcode (meat, deli, bakery scale labels).
 * Accepts UPC-A "2IIIIIVPPPPC" or its EAN-13 form "02IIIIIVPPPPC". Other 20–29 prefixes (non-US layouts)
 * are decoded as a 5-digit price without a verifier and flagged unverified.
 * @returns {null | { itemRef: string, priceCents: number, verified: boolean, layout: string, digits: string }}
 */
export function decodeStoreLabel(raw) {
  let d = digitsOnly(raw);
  if (d.length === 13 && d[0] === "0") d = d.slice(1);
  if (d.length === 12 && d[0] === "2") {
    const itemRef = d.slice(1, 6), v = Number(d[6]), price4 = d.slice(7, 11);
    if (priceVerifier4(price4) === v) return { itemRef, priceCents: Number(price4), verified: true, layout: "GS1 US · 4-digit price + verifier", digits: d };
    // some scales print a plain 5-digit price (no verifier digit)
    return { itemRef, priceCents: Number(d.slice(6, 11)), verified: false, layout: "5-digit price, no verifier", digits: d };
  }
  if (d.length === 13 && d[0] === "2") {
    // GS1 recommended 20–29 layouts vary by country; use the common "5-digit item · 5-digit value" reading
    return { itemRef: d.slice(2, 7), priceCents: Number(d.slice(7, 12)), verified: false, layout: "RCN-13 · 5-digit value, no verifier", digits: d };
  }
  return null;
}

/** IFPS produce PLU: 4 digits 3000–4999 (also 5-digit organic 9xxxx / GMO 8xxxx prefixes). */
export function parsePlu(raw) {
  const d = digitsOnly(raw);
  if (d.length === 4) {
    const n = Number(d);
    if (n >= 3000 && n <= 4999) return { plu: n, organic: false, prefix: null };
  }
  if (d.length === 5 && (d[0] === "9" || d[0] === "8")) {
    const n = Number(d.slice(1));
    if (n >= 3000 && n <= 4999) return { plu: n, organic: d[0] === "9", prefix: d[0] };
  }
  return null;
}

/** Classify any string the user typed or scanned. */
export function classifyCode(raw, format) {
  const d = digitsOnly(raw);
  const typed = String(raw ?? "").trim();
  if (!d || d.length !== typed.replace(/[\s-]/g, "").length) return { kind: "text" };   // letters present -> search
  const plu = parsePlu(d);
  if (plu && (d.length === 4 || d.length === 5)) return { kind: "plu", ...plu, digits: d };
  const label = decodeStoreLabel(d);
  if (label) return { kind: "store-label", ...label };
  const g = toGtin14(d, format);
  if (g) return { kind: "gtin", ...g };
  return { kind: "text" };
}

export function formatGtin(gtin14) {
  // show the familiar 12/13-digit form, grouped for reading
  const d = String(gtin14).replace(/^0+(?=\d{12})/, "");
  if (d.length === 12) return `${d[0]} ${d.slice(1, 6)} ${d.slice(6, 11)} ${d[11]}`;
  if (d.length === 13) return `${d[0]} ${d.slice(1, 7)} ${d.slice(7, 13)}`;
  return d;
}
