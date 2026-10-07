import { test } from "node:test";
import assert from "node:assert/strict";
import { tokenize, uniqueTokens, normalizeText } from "../public/js/tokenize.js";

test("tokenizer splits sizes, keeps decimals, drops punctuation", () => {
  assert.deepEqual(tokenize("Great Value Golden Sweet Whole Kernel Corn, Canned Corn, 15.25 oz Can"), ["great", "value", "golden", "sweet", "whole", "kernel", "corn", "canned", "corn", "15.25", "oz", "can"]);
  assert.deepEqual(tokenize("Bush's Best 16oz"), ["bushs", "best", "16", "oz"]);
  assert.deepEqual(tokenize("Pen+Gear  2-Pack"), ["pen", "gear", "2", "pack"]);
  assert.deepEqual(tokenize("Café Bustelo"), ["cafe", "bustelo"]);
});

test("percent stays a word so '2% milk' finds 2% milk", () => {
  assert.deepEqual(tokenize("Great Value 2% Reduced Fat Milk, 1 Gallon"), ["great", "value", "2", "percent", "reduced", "fat", "milk", "1", "gallon"]);
  assert.deepEqual(tokenize("2% milk"), ["2", "percent", "milk"]);
});

test("unique tokens are sorted and deduplicated", () => {
  assert.deepEqual(uniqueTokens("corn Corn CORN 15.25 oz"), ["15.25", "corn", "oz"]);
  assert.equal(normalizeText("A&W Root Beer"), "a and w root beer");
});
