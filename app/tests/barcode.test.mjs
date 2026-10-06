import { test } from "node:test";
import assert from "node:assert/strict";
import { checkDigit, toGtin14, upcEToUpcA, decodeStoreLabel, priceVerifier4, priceVerifier5, parsePlu, classifyCode, formatGtin } from "../public/js/barcode.js";

test("GS1 check digit matches the crawler's gtin14()", () => {
  assert.equal(checkDigit("07874205426"), 1);           // Great Value corn 078742054261
  assert.equal(checkDigit("0007874205426"), 1);         // same digits, padded body
  assert.equal(toGtin14("078742054261").gtin14, "00078742054261");
  assert.equal(toGtin14("078742054261").checkOk, true);
  assert.equal(toGtin14("078742054262").checkOk, false);
  assert.equal(toGtin14("07874205426").gtin14, "00078742054261");   // 11 digits typed: check digit added
  assert.equal(toGtin14("5000112637922").type, "EAN-13");
  assert.equal(toGtin14("5000112637922").gtin14, "05000112637922");
});

test("UPC-E expands to UPC-A", () => {
  assert.equal(upcEToUpcA("04252614"), "042100005264");   // classic example (last digit 8 -> pattern 5-9)
  assert.equal(upcEToUpcA("01234565"), "012345000065");
  assert.equal(toGtin14("04252614", "UPC_E").gtin14, "00042100005264");
});

test("price verifier reproduces the GS1 worked examples", () => {
  assert.equal(priceVerifier4("2875"), 9);
  assert.equal(priceVerifier5("14685"), 6);
});

test("store-printed label decodes item ref and price", () => {
  // 2 + item 01234 + verifier(2875)=9 + 2875 + check
  const body = "2" + "01234" + "9" + "2875";
  const code = body + checkDigit(body);
  const r = decodeStoreLabel(code);
  assert.equal(r.itemRef, "01234");
  assert.equal(r.priceCents, 2875);
  assert.equal(r.verified, true);
  const ean = decodeStoreLabel("0" + code);
  assert.equal(ean.priceCents, 2875);
  // wrong verifier -> falls back to the 5-digit reading, flagged
  const bad = "2" + "01234" + "0" + "2875";
  const r2 = decodeStoreLabel(bad + checkDigit(bad));
  assert.equal(r2.verified, false);
  assert.equal(r2.priceCents, 2875);   // "02875" -> 2875 cents
  assert.equal(decodeStoreLabel("078742054261"), null);
});

test("PLU codes", () => {
  assert.deepEqual(parsePlu("4011"), { plu: 4011, organic: false, prefix: null });
  assert.deepEqual(parsePlu("94011"), { plu: 4011, organic: true, prefix: "9" });
  assert.equal(parsePlu("1234"), null);
  assert.equal(parsePlu("5011"), null);
});

test("classifyCode routes to the right resolver", () => {
  assert.equal(classifyCode("4011").kind, "plu");
  assert.equal(classifyCode("078742054261").kind, "gtin");
  assert.equal(classifyCode("201234928757").kind, "store-label");
  assert.equal(classifyCode("peanut butter").kind, "text");
  assert.equal(classifyCode("16 oz").kind, "text");
  assert.equal(classifyCode("2% milk").kind, "text");
});

test("formatGtin groups digits for reading", () => {
  assert.equal(formatGtin("00078742054261"), "0 78742 05426 1");
  assert.equal(formatGtin("05000112637922"), "5 000112 637922");
});
