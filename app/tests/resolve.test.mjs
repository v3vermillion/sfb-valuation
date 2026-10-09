import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveCode, fromItem, kindLabel, splitTitle, titleOf, notesFor, livePlausible } from "../public/js/resolve.js";

const corn = { rank: 0, id: 1, brand: "Great Value", name: "Great Value Golden Sweet Whole Kernel Corn, Canned Corn, 15.25 oz Can", priceCents: 87, size: 15.25, unit: "oz", pack: 1, basis: "each", cat: 6, catName: "Canned & Jarred", upc: "00078742054261", retired: false, primary: true, storeBrand: true };
const retired = { ...corn, rank: 1, id: 2, retired: true, primary: false };
const mkDb = ({ ready = true } = {}) => ({
  calls: [],
  async lookupUpc(key) {
    this.calls.push(key);
    if (!ready) return { notReady: true };
    if (key === 78742054261) return { items: [corn, retired], equivalent: null };
    if (key === 4252614) return { items: [{ ...corn, id: 9, upc: "00000004252614" }], equivalent: null };   // keyed the crawler's way (zero-padded 8 digits)
    if (key === 4099100000000) return { items: [], equivalent: { brand: "Clancy's", name: "Potato Chips", quantity: "10 oz", estCents: 198, confidence: "high", basis: corn } };
    if (key === 4099100000017) return { items: [], equivalent: { brand: "Clancy's", name: "Pretzels", quantity: "16 oz", estCents: 150, confidence: "low", basis: null } };
    if (key === 212345000007) return { items: [{ ...corn, id: 7, name: "Great Value Ground Beef Tray", upc: "00212345000007" }], equivalent: null };
    return { items: [], equivalent: null };
  },
  async lookupPlu(code) { if (!ready) return { notReady: true }; return code === 4011 ? { plu: 4011, name: "Bananas", unit: "lb", price: 0.58, source: "snapshot", item: corn } : null; },
});

test("resolution order: exact item first, retired listings kept behind the primary", async () => {
  const db = mkDb();
  const r = await resolveCode(db, "078742054261");
  assert.equal(r.kind, "exact"); assert.equal(r.priceCents, 87); assert.equal(r.item.id, 1); assert.equal(r.others.length, 1);
  assert.equal(kindLabel(r), "Exact item");
  const r2 = await resolveCode(db, "0078742054261");           // EAN-13 form of the same UPC
  assert.equal(r2.gtin, "00078742054261");
  const r3 = await resolveCode(db, "07874205426");             // typed without the check digit
  assert.equal(r3.kind, "exact");
  const pref = await resolveCode(db, "078742054261", undefined, { preferId: 2 });   // a recent row remembers which listing it was
  assert.equal(pref.item.id, 2); assert.equal(pref.others[0].id, 1);
});

test("a UPC-E that the crawler keyed as 8 zero-padded digits is still found", async () => {
  const db = mkDb();
  const r = await resolveCode(db, "04252614", "upc_e", { scanned: true });
  assert.equal(r.kind, "exact"); assert.equal(r.item.id, 9); assert.equal(r.gtin, "00000004252614");
  assert.deepEqual(db.calls, [42100005264, 4252614]);
});

test("store-printed price labels decode without any database lookup; a zero price never shows as $0.00", async () => {
  const db = mkDb();
  const r = await resolveCode(db, "201234928751");
  assert.equal(r.kind, "store-label"); assert.equal(r.priceCents, 2875); assert.equal(r.label.verified, true);
  assert.equal(db.calls.length, 0);
  const zero = await resolveCode(db, "212345000007");          // price field 0000: a manufacturer variable-measure code
  assert.equal(zero.kind, "exact"); assert.equal(zero.item.id, 7);
  const zeroUnknown = await resolveCode(db, "212346000006");
  assert.equal(zeroUnknown.kind, "unknown"); assert.equal(zeroUnknown.priceCents, null); assert.equal(zeroUnknown.noPrice, true);
  assert.match(notesFor(zeroUnknown)[0].text, /carries no price/);
  const typo = await resolveCode(db, "201234928759");          // bad check digit
  assert.equal(typo.kind, "store-label"); assert.equal(typo.label.verified, false);
  assert.match(notesFor(typo).map((n) => n.text).join(" "), /check digit doesn't match/);
});

test("PLU codes price produce by the pound, organic 9-prefix included", async () => {
  const db = mkDb();
  const r = await resolveCode(db, "4011");
  assert.equal(r.kind, "plu"); assert.equal(r.unit, "lb"); assert.equal(r.priceCents, 58);
  const o = await resolveCode(db, "94011");
  assert.equal(o.title, "Organic Bananas");
  assert.equal((await resolveCode(db, "4999")).kind, "unknown");
  assert.equal((await resolveCode(db, "83000")).kind, "unknown");   // 8xxxx is its own code, not 3000
});

test("equivalent value is labeled and carries its basis item; a missing basis is flagged", async () => {
  const db = mkDb();
  const r = await resolveCode(db, "4099100000000");
  assert.equal(r.kind, "equivalent"); assert.equal(r.priceCents, 198); assert.equal(r.equiv.basis.id, 1);
  assert.match(notesFor(r).map((n) => n.text).join(" "), /closest Walmart equivalent/);
  const nb = await resolveCode(db, "4099100000017");
  assert.equal(nb.kind, "equivalent"); assert.equal(nb.equiv.basis, null);
  assert.match(notesFor(nb).map((n) => n.text).join(" "), /no longer listed/);
});

test("unknown barcodes are flagged, never silently priced; text is not a code; a loading pack says so", async () => {
  const db = mkDb();
  const r = await resolveCode(db, "012345678905");
  assert.equal(r.kind, "unknown"); assert.equal(r.priceCents, null); assert.equal(r.checkOk, true);
  assert.equal(await resolveCode(db, "peanut butter"), null);
  const cold = mkDb({ ready: false });
  assert.equal((await resolveCode(cold, "078742054261")).kind, "not-ready");
  assert.equal((await resolveCode(cold, "4011")).kind, "not-ready");
  assert.equal(kindLabel({ kind: "not-ready" }), "Prices still loading");
});

test("titles never repeat the brand", () => {
  assert.deepEqual(splitTitle(corn), { pre: "", brand: "Great Value", rest: " Golden Sweet Whole Kernel Corn, Canned Corn, 15.25 oz Can" });
  assert.deepEqual(splitTitle({ brand: "Great Value", name: "(2 pack) Great Value Peanut Butter, 28 oz" }), { pre: "(2 pack) ", brand: "Great Value", rest: " Peanut Butter, 28 oz" });
  assert.equal(titleOf({ brand: "Great Value", name: "(2 pack) Great Value Peanut Butter, 28 oz" }), "(2 pack) Great Value Peanut Butter, 28 oz");
  assert.equal(titleOf({ brand: "Jif", name: "Creamy Peanut Butter, 16 oz" }), "Jif Creamy Peanut Butter, 16 oz");
  assert.equal(titleOf({ brand: "", name: "Bananas" }), "Bananas");
  const closest = fromItem(corn, { closest: true, query: "corn 40 oz", dropped: ["40"] });
  assert.equal(kindLabel(closest), "Closest match");
  assert.match(notesFor(closest)[0].text, /“40” was ignored/);
});

// ---- price sanity (2026-10-08): a withheld Walmart price is never shown; the item is valued at an equivalent
const withheld = { ...corn, rank: 5, id: 50, upc: "00012345678905", priceCents: 129, priceWithheld: true, rawPriceCents: 1617000,
  valueConfidence: "high", valueBasis: corn, primary: true };
test("a withheld price resolves to an equivalent value with its basis, from a search tap or a scan", async () => {
  const r = fromItem(withheld);
  assert.equal(r.kind, "equivalent"); assert.equal(r.priceCents, 129); assert.equal(kindLabel(r), "Equivalent value");
  assert.equal(r.equiv.basis.id, 1); assert.equal(r.equiv.rawCents, 1617000);
  const note = notesFor(r).map((n) => n.text).join(" ");
  assert.match(note, /\$16,170\.00/); assert.match(note, /closest comparable Walmart item/);
  const db = { async lookupUpc(key) { return key === 12345678905 ? { items: [withheld], equivalent: null } : { items: [], equivalent: null }; } };
  const s = await resolveCode(db, "012345678905");
  assert.equal(s.kind, "equivalent"); assert.equal(s.priceCents, 129); assert.equal(s.gtin, "00012345678905");
});

test("a rough equivalent says how it was valued", () => {
  const r = fromItem({ ...withheld, valueBasis: null, valueConfidence: "rough" });
  assert.match(notesFor(r).map((n) => n.text).join(" "), /typical price of items in its category/);
});

test("a barcode with a plausible listing and a withheld one shows the plausible listing", async () => {
  const db = { async lookupUpc() { return { items: [withheld, { ...corn, id: 51 }], equivalent: null }; } };
  const r = await resolveCode(db, "078742054261");
  assert.equal(r.kind, "exact"); assert.equal(r.item.id, 51); assert.equal(r.others[0].id, 50);
});

test("a discontinued listing says so", () => {
  assert.match(notesFor(fromItem({ ...corn, discontinued: true })).map((n) => n.text).join(" "), /discontinued/);
});

test("a live price must be believable before it can be used", () => {
  assert.equal(livePlausible(296, 300), "ok");
  assert.equal(livePlausible(250, 4925), "ok");            // 19.7x below: still within the 20x line
  assert.equal(livePlausible(98, 4925), "far");            // Pampers 162 ct at $0.98 against a saved $49.25
  assert.equal(livePlausible(500000, 2000), "far");
  assert.equal(livePlausible(5, null), "implausible");      // under $0.10
  assert.equal(livePlausible(2_000_000, null), "implausible");
  assert.equal(livePlausible(NaN, 100), "implausible");
  assert.equal(livePlausible(1999, null), "ok");            // an unknown barcode: only the absolute range applies
});

test("an equivalent's title names the brand once", async () => {
  const db = { async lookupUpc() { return { items: [], equivalent: { brand: "Rachael Ray Nutrish", name: "Rachael Ray Nutrish Surfin' Turf Cat Food", quantity: "3 lb", estCents: 798, confidence: "medium", basis: null } }; } };
  const r = await resolveCode(db, "071190006114");
  assert.equal(r.kind, "equivalent");
  assert.equal(r.title, "Rachael Ray Nutrish Surfin' Turf Cat Food, 3 lb");
});
