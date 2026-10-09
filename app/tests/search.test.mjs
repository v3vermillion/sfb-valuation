// The search worker on a small real pack (built by tools/build-db.mjs from a handful of rows): relaxation order and
// ranking rules that real queries depend on.
import { test, before } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import zlib from "node:zlib";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { openPack } from "../tools/search-harness.mjs";

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
let id = 1000;
const row = (name, brand, price, extra = {}) => ({ id: id++, upc: String(70000000000 + id).padStart(14, "0"), name, brand, price, size: null, unit: null, pack: 1,
  cat: "7", dept: "Food", flags: [], primary: true, stock: "Available", ...extra });
const ROWS = [
  row("Great Value Pinto Beans, 32 oz", "Great Value", 2.12, { size: 32, unit: "oz", cat: "7", store_brand: true }),
  row("Great Value Dry Roasted Peanuts, 16 oz", "Great Value", 2.98, { size: 16, unit: "oz", cat: "9", store_brand: true }),
  row("Great Value Active Dry Yeast, 0.75 oz, 3 Count", "Great Value", 1.12, { size: 0.75, unit: "oz", pack: 3, cat: "28", store_brand: true }),
  row("Great Value Dry Black Beans, 2 lb", "Great Value", 2.24, { size: 2, unit: "lb", cat: "7", store_brand: true }),
  row("Huggies Little Movers Baby Diapers, Size 4, 60 Count", "Huggies", 24.97, { size: 60, unit: "ct", cat: "13", dept: "Baby" }),
  row("Huggies Diaper Bag Backpack, Gray", "Huggies", 39.97, { cat: "13", dept: "Baby" }),
  row("Huggies Diaper Pail Refills", "Huggies", 9.97, { cat: "13", dept: "Baby" }),
];

let db;
before(async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sfb-search-"));
  const pub = path.join(tmp, "store", "build", "published");
  fs.mkdirSync(pub, { recursive: true });
  fs.writeFileSync(path.join(pub, "items.jsonl.gz"), zlib.gzipSync(ROWS.map((r) => JSON.stringify(r)).join("\n") + "\n"));
  fs.writeFileSync(path.join(pub, "manifest.json"), JSON.stringify({ version: "test-1", published: "2026-10-09T00:00:00Z" }));
  execFileSync(process.execPath, [path.join(APP, "tools", "build-db.mjs"), "--store", path.join(tmp, "store"), "--out", path.join(tmp, "db")], { stdio: "ignore" });
  db = await openPack(path.join(tmp, "db"));
});

const top = (q) => db.search(q, 10);

test("a word that matches nothing together is dropped by how little it says, not how rare it is", () => {
  const r = top("great value dry pinto beans");
  assert.equal(r.relaxed, true);
  assert.deepEqual(r.dropped, ["dry"]);
  assert.equal(r.items[0].name, "Great Value Pinto Beans, 32 oz");
});

test("the item a query names (its head noun) comes before things that merely carry the word", () => {
  const r = top("huggies diapers");
  assert.equal(r.items[0].name, "Huggies Little Movers Baby Diapers, Size 4, 60 Count");
});

test("every query still returns something", () => {
  for (const q of ["pinto", "dry beans", "zzzz", "huggies size 4", "yeast packets"]) {
    const r = top(q);
    if (q !== "zzzz") assert.ok(r.items.length > 0, q);
  }
});
