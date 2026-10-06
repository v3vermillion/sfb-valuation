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
//   strings-K    "SFBS" u32 count u32 firstRank | offsets u32[count+1] | utf8 bytes of "brand\x1Fname" per item
//   upc.bin      "SFBU" u32 M | keys f64[M] sorted (GTIN-14 as a number; primary row first within a key) | ranks u32[M]
//   tokens.bin   "SFBT" u32 T u32 postingBytes | dictOff u32[T+1] | dict utf8 (tokens in byte order) | postOff u32[T+1] | postings (varint deltas of ascending ranks) | tokCat u8[T] (dominant category, 0 = none)
//   equiv.bin    "SFBE" u32 E | keys f64[E] sorted | est u32[E] cents | basisRank u32[E] (0xFFFFFFFF = none) | baseQty f32[E] | pack u16[E] | unit u8[E] | conf u8[E] | offsets u32[E+1] | utf8 "brand\x1Fname\x1Fquantity"
// Items are stored in RANK order (best candidate first), so the search worker's bitset scan from rank 0 yields
// best-first results without sorting. See app/README.md for the reasoning.
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

function arg(name, dflt) {
  const i = process.argv.indexOf("--" + name);
  return i > 0 ? process.argv[i + 1] : dflt;
}
const STORE = path.resolve(arg("store", path.join(APP, "build", "fixture-store")));
const OUT = path.resolve(arg("out", path.join(APP, "dist", "db")));
const MAX_ITEMS = Number(arg("max-items", "0")) || Infinity;

const t0 = Date.now();
const log = (m) => console.log(`[${((Date.now() - t0) / 1000).toFixed(1)}s] ${m}`);

async function* jsonlGz(file) {
  const rl = readline.createInterface({ input: fs.createReadStream(file).pipe(zlib.createGunzip()), crlfDelay: Infinity });
  for await (const line of rl) if (line) yield JSON.parse(line);
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
const version = String(srcManifest.version);
log(`reading snapshot ${version} from ${pubDir}`);

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
  if (r.stock && r.stock !== "Available") bits |= F.UNAVAILABLE;
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
  if (bits & F.CARRIED) score -= 1;
  if (bits & F.RETIRED) score -= 3;
  if (bits & F.NO_SIZE) score -= 0.5;
  if (bits & F.PROMO) score -= 0.2;
  score -= Math.min(1, name.length / 120);
  items.push({
    id: Number(r.id), upc, name, brand, price: Math.round(Number(r.price) * 100), size: r.size == null ? 0 : Number(r.size),
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
function writeGz(name, buf) {
  const gz = zlib.gzipSync(buf, { level: 6 });
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
  writeGz("cols.bin", concatAligned([header("SFBC", N), Buffer.from(price.buffer), Buffer.from(size.buffer), Buffer.from(pack.buffer), Buffer.from(unit.buffer),
    Buffer.from(basis.buffer), Buffer.from(flags.buffer), Buffer.from(cat.buffer), Buffer.from(id.buffer), Buffer.from(upc.buffer)]));
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
  if (fs.existsSync(eqFile)) {
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
{
  const src = JSON.parse(fs.readFileSync(path.join(APP, "data", "plu.json"), "utf8"));
  const produce = [];
  for (let i = 0; i < N; i++) if (items[i].cat === 1) produce.push(i);
  const toks = new Map(produce.map((i) => [i, uniqueTokens(items[i].name)]));
  const out = [];
  let priced = 0;
  for (const c of src.codes) {
    let best = null;
    for (const i of produce) {
      const tk = toks.get(i);
      if (!c.match.every((m) => tk.some((t) => t.startsWith(m)))) continue;
      const it = items[i];
      let price = null;
      if (c.unit === "lb") {
        if (it.basis === 1) price = it.price / 100;
        else if (it.size && it.unitName in TO_OZ) price = it.price / 100 / ((it.size * TO_OZ[it.unitName]) / 16 * it.pack);
      } else if (c.unit === "each") {
        if (!it.size || it.unitName === "ct") price = it.price / 100 / (it.unitName === "ct" ? it.size * it.pack : it.pack);
      }
      if (price == null || !(price > 0)) continue;
      if (!best || i < best.rank) best = { rank: i, price };
    }
    if (best) priced++;
    out.push({ plu: c.plu, name: c.name, unit: c.unit, price: best ? Math.round(best.price * 100) / 100 : c.fallback, source: best ? "snapshot" : "typical", rank: best ? best.rank : null });
  }
  const json = JSON.stringify({ built: new Date().toISOString(), codes: out });
  fs.writeFileSync(path.join(OUT, version, "plu.json"), json);
  files["plu.json"] = { path: "plu.json", bytes: json.length, gzBytes: json.length };
  log(`PLU table: ${priced}/${out.length} codes priced from the snapshot, rest typical`);
}

// ---------------------------------------------------------------- 9. manifest + pointer
const manifest = {
  format: "sfb-pack", formatVersion: 1, version, published: srcManifest.published, built: new Date().toISOString(),
  priceDate: (srcStats.built || srcManifest.published || "").slice(0, 10),
  items: N, upcs: files._upcs, equivalents: files._equivalents, tokens: files._tokens, postings: files._postings,
  fixture: Boolean(srcManifest.fixture), gatesPassed: srcManifest.gates_passed ?? null, approvedManually: srcManifest.approved_manually ?? null,
  files: {
    cols: files["cols.bin"], strings: files._stringShards.map((s) => ({ ...s, ...files[s.file.replace(/\.gz$/, "")] })),
    upc: files["upc.bin"], tokens: files["tokens.bin"], equiv: files["equiv.bin"], plu: files["plu.json"],
  },
};
manifest.totalGzBytes = Object.values(files).filter((f) => f && f.gzBytes).reduce((a, f) => a + f.gzBytes, 0);
fs.writeFileSync(path.join(OUT, version, "manifest.json"), JSON.stringify(manifest, null, 2));
fs.writeFileSync(path.join(OUT, "current.json"), JSON.stringify({ version, base: `${version}/`, items: N, priceDate: manifest.priceDate, fixture: manifest.fixture }, null, 2));
log(`done: ${N.toLocaleString()} items, ${(manifest.totalGzBytes / 1048576).toFixed(1)} MB over the wire -> ${path.join(OUT, version)}`);
