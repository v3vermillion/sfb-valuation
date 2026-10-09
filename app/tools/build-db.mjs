#!/usr/bin/env node
// build-db.mjs — turn a published snapshot (a data-store checkout) into the app's binary database pack.
//
//   node --max-old-space-size=4096 app/tools/build-db.mjs --store <data-store dir> --out <dist/db dir>
//
// Reads  <store>/build/published/{items.jsonl.gz,manifest.json,stats.json} and <store>/identify/equivalents.jsonl.gz
// Writes <out>/<version>/{manifest.json, cols.bin.gz, strings-N.bin.gz, upc.bin.gz, tokens.bin.gz, equiv.bin.gz, plu.json}
//        <out>/current.json  -> { version, base }
//
// Format "sfb-pack v1" (all integers little-endian, arrays 8-byte aligned, every .bin gzipped as a whole):
//   cols.bin     "SFBC" u32 N | price u32[N] cents | size f32[N] | pack u16[N] | unit u8[N] | basis u8[N] | flags u8[N] | cat u8[N] | id f64[N] | upc f64[N]
//                | flags2 u8[N] | valueBasis u32[N] (rank, 0xFFFFFFFF = none) | rawPrice u32[N] cents (0 = not withheld)
//                (the three trailing arrays were added in format 2; a format-1 reader stops before them)
//                price is what the app shows: Walmart's price, or for a withheld price (flags2 PRICE_WITHHELD) its
//                equivalent value, with Walmart's own price in rawPrice; flags2 bits: 1 placeholder (barcode lookup only,
//                never in the token index), 2 price withheld, 4 discontinued, bits 3-4 value confidence (0 rough .. 3 high),
//                32 the price is the store's own shelf price (manifest.store names the store), not Walmart.com's,
//                64 the price is far from comparable items by size (unit_price_suspect: often a case listed as one)
//   strings-K    "SFBS" u32 count u32 firstRank | offsets u32[count+1] | utf8 bytes of "brand\x1Fname" per item
//   upc.bin      "SFBU" u32 M | keys f64[M] sorted (GTIN-14 as a number; primary row first within a key) | ranks u32[M]
//   tokens.bin   "SFBT" u32 T u32 postingBytes | dictOff u32[T+1] | dict utf8 (tokens in byte order) | postOff u32[T+1] | postings (varint deltas of ascending ranks) | tokCat u8[T] (dominant category, 0 = none)
//   equiv.bin    "SFBE" u32 E | keys f64[E] sorted | est u32[E] cents | basisRank u32[E] (0xFFFFFFFF = none) | baseQty f32[E] | pack u16[E] | unit u8[E] | conf u8[E] | offsets u32[E+1] | utf8 "brand\x1Fname\x1Fquantity"
// Items are stored in RANK order (best candidate first), so the search worker's bitset scan from rank 0 yields
// best-first results without sorting. See app/README.md for the reasoning.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import readline from "node:readline";
import { fileURLToPath } from "node:url";
import { uniqueTokens, tokenize } from "../public/js/tokenize.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP = path.resolve(HERE, "..");

const UNIT = { oz: 1, "fl oz": 2, lb: 3, ct: 4, g: 5, kg: 6, ml: 7, l: 8, gal: 9, qt: 10, pt: 11 };
const TO_OZ = { oz: 1, lb: 16, g: 0.035274, kg: 35.274 };
const TO_FLOZ = { "fl oz": 1, ml: 0.033814, l: 33.814, gal: 128, qt: 32, pt: 16 };
const F = { RETIRED: 1, NO_SIZE: 2, PROMO: 4, CARRIED: 8, STORE_BRAND: 16, PRIMARY: 32, SIZE_CONFLICT: 64, UNAVAILABLE: 128 };
const CORE_DEPTS = new Set(["Food", "Health and Medicine", "Pharmacy", "Personal Care", "Beauty", "Baby", "Pets", "Household Essentials"]);
const CONF = { low: 0, medium: 1, high: 2 };
const F2 = { PLACEHOLDER: 1, PRICE_WITHHELD: 2, DISCONTINUED: 4, STORE_PRICE: 32, UNIT_SUSPECT: 64 };
const VALUE_CONF = { rough: 0, low: 1, medium: 2, high: 3 };
const NO_RANK = 0xFFFFFFFF;

function arg(name, dflt) {
  const i = process.argv.indexOf("--" + name);
  return i > 0 ? process.argv[i + 1] : dflt;
}
const STORE = path.resolve(arg("store", path.join(APP, "build", "fixture-store")));
const OUT = path.resolve(arg("out", path.join(APP, "dist", "db")));
const MAX_ITEMS = Number(arg("max-items", "0")) || Infinity;

const t0 = Date.now();
const log = (m) => console.log(`[${((Date.now() - t0) / 1000).toFixed(1)}s] ${m}`);

// A data-store .jsonl.gz over 45 MB is stored as shards <name>.s000, <name>.s001, ... (crawler/store.py): read either form.
function jsonlFiles(file) {
  if (fs.existsSync(file)) return [file];
  const dir = path.dirname(file), base = path.basename(file);
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((n) => n.startsWith(base + ".s") && /\.s\d{3}$/.test(n)).sort().map((n) => path.join(dir, n));
}

async function* jsonlGz(file) {
  const files = jsonlFiles(file);
  if (!files.length) throw new Error(`missing ${file}`);
  for (const f of files) {
    const rl = readline.createInterface({ input: fs.createReadStream(f).pipe(zlib.createGunzip()), crlfDelay: Infinity });
    for await (const line of rl) if (line) yield JSON.parse(line);
  }
}

function gtinNumber(upc) {
  if (!upc) return 0;
  const d = String(upc).replace(/\D/g, "");
  if (!d || d.length > 14) return 0;
  return Number(d.padStart(14, "0"));
}

// ---------------------------------------------------------------- 1. read items
const pubDir = path.join(STORE, "build", "published");
const srcManifest = JSON.parse(fs.readFileSync(path.join(pubDir, "manifest.json"), "utf8"));
const srcStats = fs.existsSync(path.join(pubDir, "stats.json")) ? JSON.parse(fs.readFileSync(path.join(pubDir, "stats.json"), "utf8")) : {};
// The pack version names the snapshot plus a hash of everything else that shapes the pack bytes (the equivalents
// table, this builder, the tokenizer, the format), so an identify refresh or a builder change ships as a new version
// instead of new bytes under an "immutable" URL that phones already hold.
const snapshot = String(srcManifest.version);
const FORMAT_VERSION = 2;
const packHash = crypto.createHash("sha256").update(`sfb-pack/${FORMAT_VERSION}\n`);
const CATEGORIES_FILE = path.join(APP, "..", "data", "categories.json");
const STORE_FILE = path.join(APP, "..", "data", "store.json");
for (const f of [fileURLToPath(import.meta.url), path.join(APP, "public", "js", "tokenize.js"), path.join(STORE, "identify", "equivalents.jsonl.gz"), CATEGORIES_FILE, STORE_FILE]) {
  const parts = jsonlFiles(f);
  packHash.update(parts.length ? Buffer.concat(parts.map((p) => fs.readFileSync(p))) : Buffer.from("none")).update("\n");
}
const version = `${snapshot}-${packHash.digest("hex").slice(0, 8)}`;
log(`reading snapshot ${snapshot} from ${pubDir} (pack ${version})`);

const items = [];
for await (const r of jsonlGz(path.join(pubDir, srcManifest.file || "items.jsonl.gz"))) {
  if (items.length >= MAX_ITEMS) break;
  const flags = r.flags || [];
  let bits = 0;
  if (flags.includes("retired_upc")) bits |= F.RETIRED;
  if (flags.includes("no_size") || r.size == null) bits |= F.NO_SIZE;
  if (flags.includes("promo_price") || flags.includes("kept_normal_price")) bits |= F.PROMO;
  if (flags.includes("carried_over")) bits |= F.CARRIED;
  if (flags.includes("size_conflict")) bits |= F.SIZE_CONFLICT;
  if (r.store_brand) bits |= F.STORE_BRAND;
  if (r.primary) bits |= F.PRIMARY;
  const stock = flags.includes("store_price") && r.store_stock ? r.store_stock : r.stock;   // the store's shelf when known
  if (stock && stock !== "Available") bits |= F.UNAVAILABLE;
  let bits2 = 0;
  if (flags.includes("placeholder")) bits2 |= F2.PLACEHOLDER;
  if (flags.includes("discontinued")) bits2 |= F2.DISCONTINUED;
  if (flags.includes("store_price")) bits2 |= F2.STORE_PRICE;
  if (flags.includes("unit_price_suspect")) bits2 |= F2.UNIT_SUSPECT;
  const withheld = Boolean(r.price_withheld && r.equiv && r.equiv.price > 0);
  if (withheld) bits2 |= F2.PRICE_WITHHELD | ((VALUE_CONF[r.equiv.confidence] ?? 0) << 3);
  const name = String(r.name || "").trim();
  const brand = String(r.brand || "").trim();
  const upc = gtinNumber(r.upc);
  let score = 0;
  if (r.primary) score += 3;
  if (upc) score += 1;
  if (r.store_brand) score += 2;
  if (!(bits & F.UNAVAILABLE)) score += 1.5;
  if (CORE_DEPTS.has(r.dept)) score += 1;
  if (r.online) score += 0.3;
  if (r.reviews > 0) score += Math.min(1.5, Math.log10(1 + r.reviews) * 0.5);   // well-known items before obscure listings
  if (bits & F.CARRIED) score -= 1;
  if (bits & F.RETIRED) score -= 3;
  if (bits & F.NO_SIZE) score -= 0.5;
  if (bits & F.PROMO) score -= 0.2;
  if (bits2 & F2.PLACEHOLDER) score -= 2;
  if (withheld) score -= 1;
  if (bits2 & F2.UNIT_SUSPECT) score -= 1;      // priced far from items of its size: likely a case or multipack listing
  score -= Math.min(1, name.length / 120);
  if (/^\s*\(\d+\s*pack\)/i.test(name)) score -= 0.8;   // "(6 pack) ..." multipacks after the single item a volunteer holds
  items.push({
    id: Number(r.id), upc, name, brand, price: Math.round(Number(withheld ? r.equiv.price : r.price) * 100), size: r.size == null ? 0 : Number(r.size),
    flags2: bits2, rawPrice: withheld ? Math.round(Number(r.price) * 100) : 0, valueBasisId: withheld && r.equiv.basis_id != null ? Number(r.equiv.basis_id) : null,
    unit: UNIT[r.unit] || 0, unitName: r.unit || null, pack: Math.min(65535, Number(r.pack) || 1), basis: r.basis === "lb" ? 1 : 0,
    cat: Number(r.cat) || 0, flags: bits, score, dept: r.dept,
  });
}
log(`${items.length.toLocaleString()} items parsed`);

// ---------------------------------------------------------------- 2. rank
items.sort((a, b) => (b.score - a.score) || (a.id - b.id));
const N = items.length;
const rankById = new Map();
for (let i = 0; i < N; i++) rankById.set(items[i].id, i);
log("ranked");

// ---------------------------------------------------------------- helpers for binary writing
const MAGIC = (s) => Buffer.from(s, "ascii");
const pad8 = (n) => (n + 7) & ~7;
function concatAligned(parts) {
  // each part: Buffer; align the START of every part to 8 bytes
  let total = 0;
  for (const p of parts) total = pad8(total) + p.length;
  const out = Buffer.alloc(pad8(total));
  let o = 0;
  for (const p of parts) { o = pad8(o); p.copy(out, o); o += p.length; }
  return out;
}
const u32 = (arr) => Buffer.from(new Uint32Array(arr).buffer);
const u16 = (arr) => Buffer.from(new Uint16Array(arr).buffer);
const u8 = (arr) => Buffer.from(new Uint8Array(arr).buffer);
const f32 = (arr) => Buffer.from(new Float32Array(arr).buffer);
const f64 = (arr) => Buffer.from(new Float64Array(arr).buffer);
const header = (magic, ...nums) => Buffer.concat([MAGIC(magic), u32(nums)]);

fs.mkdirSync(path.join(OUT, version), { recursive: true });
const files = {};
const MAX_ASSET_BYTES = Number(process.env.SFB_MAX_ASSET_BYTES) || 25 * 1048576;   // Cloudflare Workers static assets reject any single file over 25 MiB
function writeGz(name, buf) {
  const gz = zlib.gzipSync(buf, { level: 6 });
  if (gz.length > MAX_ASSET_BYTES) throw new Error(`${name}.gz is ${(gz.length / 1048576).toFixed(1)} MiB, over Cloudflare's 25 MiB per-file limit: shard it (see SHARD_BYTES for strings)`);
  fs.writeFileSync(path.join(OUT, version, name + ".gz"), gz);
  files[name] = { path: name + ".gz", bytes: buf.length, gzBytes: gz.length };
  log(`wrote ${name}.gz  ${(buf.length / 1048576).toFixed(1)} MB raw -> ${(gz.length / 1048576).toFixed(1)} MB`);
}

// ---------------------------------------------------------------- 3. columns
{
  const price = new Uint32Array(N), size = new Float32Array(N), pack = new Uint16Array(N), unit = new Uint8Array(N),
    basis = new Uint8Array(N), flags = new Uint8Array(N), cat = new Uint8Array(N), id = new Float64Array(N), upc = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    const it = items[i];
    price[i] = it.price; size[i] = it.size; pack[i] = it.pack; unit[i] = it.unit; basis[i] = it.basis; flags[i] = it.flags; cat[i] = it.cat; id[i] = it.id; upc[i] = it.upc;
  }
  const flags2 = new Uint8Array(N), valueBasis = new Uint32Array(N).fill(NO_RANK), rawPrice = new Uint32Array(N);
  for (let i = 0; i < N; i++) {
    const it = items[i];
    flags2[i] = it.flags2; rawPrice[i] = Math.min(0xFFFFFFFF, it.rawPrice);
    if (it.valueBasisId != null && rankById.has(it.valueBasisId)) valueBasis[i] = rankById.get(it.valueBasisId);
  }
  writeGz("cols.bin", concatAligned([header("SFBC", N), Buffer.from(price.buffer), Buffer.from(size.buffer), Buffer.from(pack.buffer), Buffer.from(unit.buffer),
    Buffer.from(basis.buffer), Buffer.from(flags.buffer), Buffer.from(cat.buffer), Buffer.from(id.buffer), Buffer.from(upc.buffer),
    Buffer.from(flags2.buffer), Buffer.from(valueBasis.buffer), Buffer.from(rawPrice.buffer)]));
}

// ---------------------------------------------------------------- 4. strings (sharded, ≤ ~40 MB raw each)
{
  const SHARD_BYTES = 40 * 1048576;
  let start = 0, shard = 0;
  const shards = [];
  while (start < N) {
    const bufs = [], offs = [0];
    let bytes = 0, end = start;
    while (end < N && bytes < SHARD_BYTES) {
      const b = Buffer.from(items[end].brand + "\x1F" + items[end].name, "utf8");
      bufs.push(b); bytes += b.length; offs.push(bytes); end++;
    }
    const name = `strings-${shard}.bin`;
    writeGz(name, concatAligned([header("SFBS", end - start, start), u32(offs), Buffer.concat(bufs)]));
    shards.push({ file: name + ".gz", firstRank: start, count: end - start });
    start = end; shard++;
  }
  files._stringShards = shards;
}

// ---------------------------------------------------------------- 5. UPC index
{
  const rows = [];
  for (let i = 0; i < N; i++) if (items[i].upc) rows.push(i);
  rows.sort((a, b) => (items[a].upc - items[b].upc) || (((items[b].flags & F.PRIMARY) ? 1 : 0) - ((items[a].flags & F.PRIMARY) ? 1 : 0)) || (a - b));
  const keys = new Float64Array(rows.length), ranks = new Uint32Array(rows.length);
  for (let j = 0; j < rows.length; j++) { keys[j] = items[rows[j]].upc; ranks[j] = rows[j]; }
  writeGz("upc.bin", concatAligned([header("SFBU", rows.length), Buffer.from(keys.buffer), Buffer.from(ranks.buffer)]));
  files._upcs = rows.length;
}

// ---------------------------------------------------------------- 6. token index
{
  const post = new Map();   // token -> number[] ranks (ascending, since we iterate ranks in order)
  for (let i = 0; i < N; i++) {
    if (items[i].flags2 & F2.PLACEHOLDER) continue;        // barcode lookup only: a placeholder name never answers a typed search
    for (const t of uniqueTokens(items[i].brand + " " + items[i].name)) {
      let a = post.get(t);
      if (!a) { a = []; post.set(t, a); }
      a.push(i);
    }
  }
  const tokens = Array.from(post.keys()).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));   // UTF-16 order == byte order for ASCII
  const T = tokens.length;
  const dictOff = new Uint32Array(T + 1);
  const dictParts = [];
  let d = 0;
  for (let k = 0; k < T; k++) { const b = Buffer.from(tokens[k], "utf8"); dictParts.push(b); d += b.length; dictOff[k + 1] = d; }
  let totalPost = 0;
  for (const a of post.values()) totalPost += a.length;
  // varint delta encode
  let buf = Buffer.alloc(Math.max(1024, totalPost * 2)), p = 0;
  const postOff = new Uint32Array(T + 1);
  for (let k = 0; k < T; k++) {
    const a = post.get(tokens[k]);
    let prev = -1;
    if (p + a.length * 5 > buf.length) { const nb = Buffer.alloc(buf.length * 2 + a.length * 5); buf.copy(nb, 0, 0, p); buf = nb; }
    for (const r of a) {
      let v = r - prev - 1; prev = r;
      while (v >= 0x80) { buf[p++] = (v & 0x7f) | 0x80; v >>>= 7; }
      buf[p++] = v;
    }
    postOff[k + 1] = p;
  }
  const postings = buf.subarray(0, p);
  // dominant category per token (search boosts items in the category a word usually belongs to: "milk" -> dairy)
  const tokCat = new Uint8Array(T);
  for (let k = 0; k < T; k++) {
    const a = post.get(tokens[k]);
    const counts = new Map();
    const step = Math.max(1, Math.floor(a.length / 2000));
    for (let j = 0; j < a.length; j += step) { const c = items[a[j]].cat; counts.set(c, (counts.get(c) || 0) + 1); }
    let best = 0, bestN = 0, total = 0;
    for (const [c, n] of counts) { total += n; if (n > bestN) { bestN = n; best = c; } }
    tokCat[k] = bestN >= total * 0.45 ? best : 0;   // 0 = no clear home category
  }
  writeGz("tokens.bin", concatAligned([header("SFBT", T, p), Buffer.from(dictOff.buffer), Buffer.concat(dictParts), Buffer.from(postOff.buffer), postings, Buffer.from(tokCat.buffer)]));
  files._tokens = T; files._postings = totalPost;
  log(`${T.toLocaleString()} tokens, ${totalPost.toLocaleString()} postings`);
}

// ---------------------------------------------------------------- 7. equivalents (other-store barcodes)
{
  const eqFile = path.join(STORE, "identify", "equivalents.jsonl.gz");
  const rows = [];
  if (jsonlFiles(eqFile).length) {
    for await (const e of jsonlGz(eqFile)) {
      const key = gtinNumber(e.upc);
      if (!key || !(e.est_price > 0)) continue;
      rows.push({ key, est: Math.round(e.est_price * 100), basisRank: rankById.has(Number(e.basis_id)) ? rankById.get(Number(e.basis_id)) : 0xFFFFFFFF,
        baseQty: Number(e.base_qty) || 0, pack: Math.min(65535, Number(e.pack) || 1), unit: UNIT[e.base_unit] || 0, conf: CONF[e.confidence] ?? 0,
        str: Buffer.from(`${e.brand || ""}\x1F${e.name || ""}\x1F${e.quantity || ""}`, "utf8") });
    }
  }
  rows.sort((a, b) => a.key - b.key);
  const E = rows.length;
  const keys = new Float64Array(E), est = new Uint32Array(E), basisRank = new Uint32Array(E), baseQty = new Float32Array(E), pack = new Uint16Array(E), unit = new Uint8Array(E), conf = new Uint8Array(E), offs = new Uint32Array(E + 1);
  let o = 0;
  for (let j = 0; j < E; j++) { const r = rows[j]; keys[j] = r.key; est[j] = r.est; basisRank[j] = r.basisRank; baseQty[j] = r.baseQty; pack[j] = r.pack; unit[j] = r.unit; conf[j] = r.conf; o += r.str.length; offs[j + 1] = o; }
  writeGz("equiv.bin", concatAligned([header("SFBE", E), Buffer.from(keys.buffer), Buffer.from(est.buffer), Buffer.from(basisRank.buffer), Buffer.from(baseQty.buffer), Buffer.from(pack.buffer), Buffer.from(unit.buffer), Buffer.from(conf.buffer), Buffer.from(offs.buffer), Buffer.concat(rows.map((r) => r.str))]));
  files._equivalents = E;
}

// ---------------------------------------------------------------- 8. PLU produce table, priced from the snapshot when possible
// A code is priced from a produce row only when the row names everything that distinguishes the code ("yellow bell
// pepper", not any bell pepper; "blood orange", not a bag of navels), loose produce is preferred over bags and packs,
// and a price outside 0.4-2.5x the code's typical price falls back to the typical one: a wrong match never prices a code.
const PLU_GENERIC = new Set(["fresh", "small", "medium", "large", "extra", "jumbo", "greenhouse", "conventional", "loose", "each", "lb", "per", "whole", "the", "and", "of"]);
const singular = (t) => (t.endsWith("ies") ? t.slice(0, -3) + "y" : t.endsWith("oes") ? t.slice(0, -2) : t.endsWith("s") && !t.endsWith("ss") ? t.slice(0, -1) : t);
function pluMatchWords(c) {
  const own = tokenize(c.name).filter((t) => !/^\d/.test(t) && !PLU_GENERIC.has(t)).map(singular);
  return [...new Set([...(c.match || []).map(singular), ...own])];
}
{
  const src = JSON.parse(fs.readFileSync(path.join(APP, "data", "plu.json"), "utf8"));
  const produce = [];
  for (let i = 0; i < N; i++) if (items[i].cat === 1 && !(items[i].flags2 & (F2.PLACEHOLDER | F2.PRICE_WITHHELD))) produce.push(i);
  const toks = new Map(produce.map((i) => [i, tokenize(items[i].name).map(singular)]));
  const out = [];
  let priced = 0, outOfBand = 0;
  for (const c of src.codes) {
    const words = pluMatchWords(c);
    let best = null;
    for (const i of produce) {
      const tk = toks.get(i);
      if (!words.every((m) => tk.some((t) => t.startsWith(m)))) continue;
      const it = items[i];
      let price = null;
      if (c.unit === "lb") {
        if (it.basis === 1) price = it.price / 100;
        else if (it.size && it.unitName in TO_OZ) price = it.price / 100 / ((it.size * TO_OZ[it.unitName]) / 16 * it.pack);
      } else if (c.unit === "each") {
        if (!it.size || it.unitName === "ct") price = it.price / 100 / (it.unitName === "ct" ? it.size * it.pack : it.pack);
      }
      if (price == null || !(price > 0)) continue;
      // loose first: sold the way the code is (by the pound / each), not a bag, a pack or a tray
      let fit = 0;
      if ((c.unit === "lb" && it.basis === 1) || (c.unit === "each" && !it.size)) fit += 2;
      if (/\b(bag|bags|pack|packs|tray|clamshell|container|pouch|box)\b|\(\d+\s*pack\)/i.test(it.name)) fit -= 2;
      fit -= 0.1 * Math.max(0, tk.length - words.length);       // extra words: a variety or a product made from it
      if (!best || fit > best.fit || (fit === best.fit && i < best.rank)) best = { rank: i, price, fit };
    }
    if (best && c.fallback > 0 && (best.price < 0.4 * c.fallback || best.price > 2.5 * c.fallback)) { best = null; outOfBand++; }
    if (best) priced++;
    out.push({ plu: c.plu, name: c.name, unit: c.unit, price: best ? Math.round(best.price * 100) / 100 : c.fallback, source: best ? "snapshot" : "typical", rank: best ? best.rank : null });
  }
  const json = JSON.stringify({ built: new Date().toISOString(), codes: out });
  fs.writeFileSync(path.join(OUT, version, "plu.json"), json);
  files["plu.json"] = { path: "plu.json", bytes: json.length, gzBytes: json.length };
  log(`PLU table: ${priced}/${out.length} codes priced from the snapshot, ${outOfBand} matches outside 0.4-2.5x typical, rest typical`);
}

// ---------------------------------------------------------------- 9. manifest + pointer
const manifest = {
  format: "sfb-pack", formatVersion: FORMAT_VERSION, version, snapshot, published: srcManifest.published, built: new Date().toISOString(),
  priceDate: (srcStats.built || srcManifest.published || "").slice(0, 10),
  items: N, upcs: files._upcs, equivalents: files._equivalents, tokens: files._tokens, postings: files._postings,
  fixture: Boolean(srcManifest.fixture), gatesPassed: srcManifest.gates_passed ?? null, approvedManually: srcManifest.approved_manually ?? null,
  categories: fs.existsSync(CATEGORIES_FILE) ? JSON.parse(fs.readFileSync(CATEGORIES_FILE, "utf8")).categories : null,
  store: (() => { try { const s = JSON.parse(fs.readFileSync(STORE_FILE, "utf8")); return { id: s.store_id, name: s.name, address: s.address, label: s.label || "Strongsville Walmart" }; } catch { return null; } })(),
  storePriced: items.filter((it) => it.flags2 & F2.STORE_PRICE).length,
  files: {
    cols: files["cols.bin"], strings: files._stringShards.map((s) => ({ ...s, ...files[s.file.replace(/\.gz$/, "")] })),
    upc: files["upc.bin"], tokens: files["tokens.bin"], equiv: files["equiv.bin"], plu: files["plu.json"],
  },
};
manifest.totalGzBytes = Object.values(files).filter((f) => f && f.gzBytes).reduce((a, f) => a + f.gzBytes, 0);
fs.writeFileSync(path.join(OUT, version, "manifest.json"), JSON.stringify(manifest, null, 2));
fs.writeFileSync(path.join(OUT, "current.json"), JSON.stringify({ version, snapshot, base: `${version}/`, items: N, priceDate: manifest.priceDate, fixture: manifest.fixture }, null, 2));
log(`done: ${N.toLocaleString()} items, ${(manifest.totalGzBytes / 1048576).toFixed(1)} MB over the wire -> ${path.join(OUT, version)}`);
