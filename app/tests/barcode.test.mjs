import { test } from "node:test";
import assert from "node:assert/strict";
import { checkDigit, toGtin14, upcEToUpcA, upcECheckOk, decodeStoreLabel, priceVerifier4, priceVerifier5, parsePlu, classifyCode, formatGtin } from "../public/js/barcode.js";

test("GS1 check digit matches the crawler's gtin14()", () => {
  assert.equal(checkDigit("07874205426"), 1);           // Great Value corn 078742054261
  assert.equal(checkDigit("0007874205426"), 1);         // same digits, padded body
  assert.equal(toGtin14("078742054261").gtin14, "00078742054261");
  assert.equal(toGtin14("078742054261").checkOk, true);
  assert.equal(toGtin14("078742054262").checkOk, false);
  assert.equal(toGtin14("07874205426").gtin14, "00078742054261");   // 11 digits typed: check digit added
  assert.equal(toGtin14("07874205426", undefined, { scanned: true }), null);   // never for a scan
  assert.equal(toGtin14("5000112637922").type, "EAN-13");
  assert.equal(toGtin14("5000112637922").gtin14, "05000112637922");
  assert.equal(toGtin14("123456789"), null);            // 9/10 digits are not product codes
  assert.equal(toGtin14("1234567890"), null);
});

test("UPC-E expands to UPC-A and keeps the EAN-8 reading as a fallback key", () => {
  assert.equal(upcEToUpcA("04252614"), "042100005264");   // classic example (last digit 1 -> pattern 0-2)
  assert.equal(upcEToUpcA("01234565"), "012345000065");
  assert.equal(upcECheckOk("04252614"), true);
  assert.equal(upcECheckOk("04252615"), false);
  const g = toGtin14("04252614", "UPC_E");
  assert.equal(g.gtin14, "00042100005264"); assert.equal(g.type, "UPC-E"); assert.equal(g.checkOk, true);
  assert.equal(g.altKey, 4252614);                        // the crawler keys 8-digit codes zero-padded
  assert.equal(toGtin14("04252615", "UPC_E").checkOk, false);   // mistyped check digit is reported, not repaired silently
  // a typed 8-digit code: UPC-E when its check validates, else EAN-8 when that one does
  assert.equal(toGtin14("04252614").type, "UPC-E");
  const ean8 = toGtin14("96385074");                      // valid EAN-8
  assert.equal(ean8.type, "EAN-8"); assert.equal(ean8.gtin14, "00000096385074"); assert.equal(ean8.checkOk, true);
  assert.equal(toGtin14("96385074", "EAN_8").type, "EAN-8");
});

test("price verifier reproduces the GS1 worked examples", () => {
  assert.equal(priceVerifier4("2875"), 9);
  assert.equal(priceVerifier5("14685"), 6);
});

test("store-printed label decodes item ref and price, and only counts as verified with a good check digit", () => {
  // 2 + item 01234 + verifier(2875)=9 + 2875 + check
  const body = "2" + "01234" + "9" + "2875";
  const code = body + checkDigit(body);
  const r = decodeStoreLabel(code);
  assert.equal(r.itemRef, "01234");
  assert.equal(r.priceCents, 2875);
  assert.equal(r.verified, true); assert.equal(r.checkOk, true);
  const ean = decodeStoreLabel("0" + code);
  assert.equal(ean.priceCents, 2875);
  const typed = decodeStoreLabel(body);                   // 11 digits typed without the check digit: the verifier vouches
  assert.equal(typed.priceCents, 2875); assert.equal(typed.verified, true); assert.equal(typed.checkOk, null);
  // a mistyped digit outside the price field breaks the check digit; the price digits still check out
  const typo = decodeStoreLabel(code.slice(0, -1) + ((Number(code.at(-1)) + 1) % 10));
  assert.equal(typo.priceCents, 2875); assert.equal(typo.checkOk, false); assert.equal(typo.verified, false);
  // wrong verifier with a good check digit -> a plain 5-digit price label, read but flagged for the volunteer to confirm
  const bad = "2" + "01234" + "0" + "2875";
  const r2 = decodeStoreLabel(bad + checkDigit(bad));
  assert.equal(r2.verified, false); assert.equal(r2.needsConfirm, true); assert.equal(r2.priceCents, 2875);
  assert.equal(decodeStoreLabel("078742054261"), null);
});

test("PLU codes: 4-digit produce, 9-prefix organic, 8-prefix is its own code", () => {
  assert.deepEqual(parsePlu("4011"), { plu: 4011, organic: false, prefix: null });
  assert.deepEqual(parsePlu("94011"), { plu: 4011, organic: true, prefix: "9" });
  assert.deepEqual(parsePlu("83000"), { plu: 83000, organic: false, prefix: "8" });
  assert.equal(parsePlu("1234"), null);
  assert.equal(parsePlu("5000"), null);
});

test("classifyCode routes typed input: PLU, store label, GTIN, else text", () => {
  assert.equal(classifyCode("4011").kind, "plu");
  assert.equal(classifyCode("201234928759").kind, "store-label");
  assert.equal(classifyCode("078742054261").kind, "gtin");
  assert.equal(classifyCode("0 78742 05426 1").kind, "gtin");
  assert.equal(classifyCode("peanut butter").kind, "text");
  assert.equal(classifyCode("16 oz").kind, "text");
  assert.equal(classifyCode("123456789").kind, "text");
  assert.equal(classifyCode("1000").kind, "text");       // a size, not a produce code
});

test("formatGtin shows the familiar grouping", () => {
  assert.equal(formatGtin("00078742054261"), "0 78742 05426 1");
  assert.equal(formatGtin("05000112637922"), "5 000112 637922");
});

test("a mistyped price digit on a store label never yields a price (the $5.99 -> $206.99 case)", () => {
  const body = "212345" + priceVerifier4("0599") + "0599";
  const code = body + checkDigit(body);
  assert.equal(decodeStoreLabel(code).priceCents, 599);
  const typo = code.slice(0, 7) + "2" + code.slice(8);       // 0599 -> 2599 typed: verifier and check digit both fail
  const r = decodeStoreLabel(typo);
  assert.equal(r.priceCents, null); assert.equal(r.verified, false);
  const short = decodeStoreLabel(typo.slice(0, 11));           // the same typo, typed as 11 digits
  assert.equal(short.priceCents, null);
  for (let pos = 7; pos < 11; pos++) {                          // every single-digit error in the price field is caught
    for (let dgt = 0; dgt < 10; dgt++) {
      if (String(dgt) === body[pos]) continue;
      const b = body.slice(0, pos) + dgt + body.slice(pos + 1);
      const x = decodeStoreLabel(b);
      assert.ok(x.priceCents === null || x.priceCents === 599 || x.needsConfirm === true, `${b}: ${x.priceCents}`);
      assert.notEqual(x.verified && x.priceCents !== 599, true, b);
    }
  }
});

test("an 11-digit product code typed without its check digit is marked unverifiable", () => {
  const g = toGtin14("07874205426");
  assert.equal(g.checkOk, null); assert.equal(g.digits, "078742054261");
});
