import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveCode, fromItem, kindLabel, splitTitle, titleOf, notesFor } from "../public/js/resolve.js";

const corn = { rank: 0, id: 1, brand: "Great Value", name: "Great Value Golden Sweet Whole Kernel Corn, Canned Corn, 15.25 oz Can", priceCents: 87, size: 15.25, unit: "oz", pack: 1, basis: "each", cat: 6, catName: "Canned & Jarred", upc: "00078742054261", retired: false, primary: true, storeBrand: true };
const retired = { ...corn, rank: 1, id: 2, retired: true, primary: false };
const fakeDb = {
  async lookupUpc(key) {
    if (key === 78742054261) return { items: [corn, retired], equivalent: null };
    if (key === 4099100000000) return { items: [], equivalent: { brand: "Clancy's", name: "Potato Chips", quantity: "10 oz", estCents: 198, confidence: "high", basis: corn } };
    return { items: [], equivalent: null };
  },
  async lookupPlu(code) { return code === 4011 ? { plu: 4011, name: "Bananas", unit: "lb", price: 0.58, source: "snapshot", item: corn } : null; },
};

test("resolution order: exact item first, retired listings kept behind the primary", async () => {
  const r = await resolveCode(fakeDb, "078742054261");
  assert.equal(r.kind, "exact"); assert.equal(r.priceCents, 87); assert.equal(r.item.id, 1); assert.equal(r.others.length, 1);
  assert.equal(kindLabel(r), "Exact item");
  const r2 = await resolveCode(fakeDb, "0078742054261");           // EAN-13 form of the same UPC
  assert.equal(r2.gtin, "00078742054261");
  const r3 = await resolveCode(fakeDb, "07874205426");             // typed without the check digit
  assert.equal(r3.kind, "exact");
});

test("store-printed price labels decode without any database lookup", async () => {
  const r = await resolveCode(fakeDb, "201234928759");
  assert.equal(r.kind, "store-label"); assert.equal(r.priceCents, 2875); assert.equal(r.label.verified, true);
});

test("PLU codes price produce by the pound, organic 9-prefix included", async () => {
  const r = await resolveCode(fakeDb, "4011");
  assert.equal(r.kind, "plu"); assert.equal(r.unit, "lb"); assert.equal(r.priceCents, 58);
  const o = await resolveCode(fakeDb, "94011");
  assert.equal(o.title, "Organic Bananas");
  assert.equal((await resolveCode(fakeDb, "4999")).kind, "unknown");
});

test("equivalent value is labeled and carries its basis item", async () => {
  const r = await resolveCode(fakeDb, "4099100000000");
  assert.equal(r.kind, "equivalent"); assert.equal(r.priceCents, 198); assert.equal(r.equiv.basis.id, 1);
  assert.match(notesFor(r).map((n) => n.text).join(" "), /closest Walmart equivalent/);
});

test("unknown barcodes are flagged, never silently priced; text is not a code", async () => {
  const r = await resolveCode(fakeDb, "012345678905");
  assert.equal(r.kind, "unknown"); assert.equal(r.priceCents, null); assert.equal(r.checkOk, true);
  assert.equal(await resolveCode(fakeDb, "peanut butter"), null);
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
