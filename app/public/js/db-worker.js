// db-worker.js — the database lives here, off the main thread.
//
// Loads an sfb-pack (tools/build-db.mjs describes the layout), keeps its files as typed-array views, and answers:
// search(query) within a frame, lookup(gtin), equivalent(gtin), plu(code), item(id). A format-3 pack is a list of
// shards (one per department); a shard already loaded is kept when a new version still uses the same files, and the
// core shards can be loaded first and the rest added later (load with `only`). Items are stored in rank order within a
// shard (best first), so a bitset scan from rank 0 already yields best-first candidates. An item's id across the pack is
// shard * 2^24 + rank. Format-2 packs load as one shard.
import { tokenize, joinedTokens, headNoun } from "./tokenize.js";

const td = new TextDecoder();
const F = { RETIRED: 1, NO_SIZE: 2, PROMO: 4, CARRIED: 8, STORE_BRAND: 16, PRIMARY: 32, SIZE_CONFLICT: 64, UNAVAILABLE: 128 };
const UNIT_NAME = [null, "oz", "fl oz", "lb", "ct", "g", "kg", "ml", "l", "gal", "qt", "pt"];
// category names come from the pack manifest (data/categories.json); this table only covers a pack built before that
const CAT_NAME = { 1: "Produce", 2: "Dairy & Eggs", 3: "Meat & Seafood", 4: "Deli & Prepared Foods", 5: "Frozen Foods", 6: "Canned & Jarred Foods", 7: "Pasta, Rice & Dry Goods", 8: "Bread & Bakery", 9: "Snacks & Candy", 10: "Beverages", 11: "Condiments, Sauces & Spreads", 12: "International Foods", 13: "Baby", 14: "Health & Medicine", 15: "Personal Care", 16: "Household Supplies", 17: "Kitchen & Dining", 18: "Home", 19: "Pet Food & Supplies", 20: "School, Office & Crafts", 21: "Toys, Books & Games", 22: "Seasonal & Party", 23: "Other", 24: "Auto", 25: "Electronics", 26: "Jewelry & Accessories", 27: "Sports & Outdoors", 28: "Baking, Spices & Oils", 29: "Breakfast & Cereal", 30: "Beauty", 31: "Hardware & Tools", 32: "Lawn, Garden & Floral" };
const F2 = { PLACEHOLDER: 1, PRICE_WITHHELD: 2, DISCONTINUED: 4, STORE_PRICE: 32, UNIT_SUSPECT: 64 };
const VALUE_CONF = ["rough", "low", "medium", "high"];
const NO_RANK = 0xFFFFFFFF;
const SHARD_SPAN = 16777216;          // 2^24 ranks per shard in an item id
const gidOf = (si, r) => si * SHARD_SPAN + r;
const splitGid = (g) => [Math.floor(g / SHARD_SPAN), g % SHARD_SPAN];

// Query-time vocabulary: abbreviations volunteers actually type (AND-expansions) and spellings that
// should match each other (OR-groups). Index tokens are never altered; this only widens the query.
const ABBREV = {
  gv: ["great", "value"], pb: ["peanut", "butter"], pbj: ["peanut", "butter"], mac: ["macaroni"],
  tp: ["toilet", "paper"], hbs: ["head", "shoulders"],
  oj: ["orange", "juice"], aj: ["apple", "juice"], ev: ["extra", "virgin"], evoo: ["extra", "virgin", "olive", "oil"], gf: ["gluten", "free"],
  sf: ["sugar", "free"], ls: ["low", "sodium"], nsa: ["no", "salt", "added"], ww: ["whole", "wheat"], wg: ["whole", "grain"],
  kd: ["kraft", "macaroni"], veg: ["vegetable"], veggies: ["vegetable"], choc: ["chocolate"], vit: ["vitamin"], deod: ["deodorant"],
  shamp: ["shampoo"], cond: ["conditioner"], det: ["detergent"], bbq: ["barbecue"], mayo: ["mayonnaise"], ketchup: ["ketchup"],
  pnut: ["peanut"], spag: ["spaghetti"], marg: ["margarine"], tom: ["tomato"], toms: ["tomato"],
};
const SYNONYM_GROUPS = [
  ["oz", "ounce", "ounces"], ["fl", "fluid"], ["lb", "lbs", "pound", "pounds"], ["ct", "count", "cnt", "pk", "pack", "packs"],
  ["gal", "gallon", "gallons"], ["qt", "quart", "quarts"], ["pt", "pint", "pints"], ["l", "liter", "liters", "litre", "litres", "ltr"], ["ml", "milliliter", "milliliters"],
  ["g", "gram", "grams"], ["kg", "kilogram", "kilograms"], ["and", "n"], ["mac", "macaroni"], ["ketchup", "catsup"], ["soda", "pop"], ["coke", "cocacola"],
  ["diaper", "diapers"], ["wipe", "wipes"], ["tissue", "tissues", "kleenex"], ["bandaid", "bandaids", "bandage", "bandages"],
  ["tuna", "tunafish"], ["ramen", "noodles"], ["cereal", "cereals"], ["bar", "bars"], ["cookie", "cookies"], ["chip", "chips"],
  ["cracker", "crackers"], ["bean", "beans"], ["tomato", "tomatoes"], ["potato", "potatoes"], ["pea", "peas"], ["egg", "eggs"],
  ["sock", "socks"], ["battery", "batteries"], ["candle", "candles"], ["toothbrush", "toothbrushes"], ["pad", "pads"], ["pen", "pens"],
  ["pencil", "pencils"], ["crayon", "crayons"], ["marker", "markers"], ["notebook", "notebooks"], ["towel", "towels"], ["roll", "rolls"],
  ["pretzel", "pretzels"], ["waffle", "waffles"], ["pancake", "pancakes"], ["nugget", "nuggets"], ["bagel", "bagels"], ["muffin", "muffins"],
  ["roll", "rolls"], ["mix", "mixes"], ["sauce", "sauces"], ["spice", "spices"], ["vitamin", "vitamins"], ["supplement", "supplements"],
];
const SYN = new Map();
for (const g of SYNONYM_GROUPS) for (const w of g) SYN.set(w, g);

let db = null;        // { manifest, version, shards: [S], N, eq*, plu, catNames }
const loaded = new Map();   // cols file path -> S, so a new version reuses a shard whose files did not change
const BIT_CACHE_MAX = 64;   // per shard

// ---------------------------------------------------------------- loading
async function readPack(url, cache) {
  // Prefer the app-managed Cache Storage copy; fall back to the network and store it.
  let res = cache ? await cache.match(url) : null;
  if (!res) {
    res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`fetch ${url}: ${res.status}`);
    if (cache) await cache.put(url, res.clone());
  }
  let buf = await res.arrayBuffer();
  const u = new Uint8Array(buf);
  if (u.length > 2 && u[0] === 0x1f && u[1] === 0x8b) {   // gzip magic -> we must inflate ourselves
    const ds = new DecompressionStream("gzip");
    const w = ds.writable.getWriter();
    w.write(u); w.close();
    buf = await new Response(ds.readable).arrayBuffer();
  }
  return buf;
}

const pad8 = (n) => (n + 7) & ~7;
class Reader {
  constructor(buf) { this.buf = buf; this.dv = new DataView(buf); this.o = 0; }
  magic(expect) { const m = td.decode(new Uint8Array(this.buf, this.o, 4)); if (m !== expect) throw new Error(`bad magic ${m} (want ${expect})`); this.o += 4; }
  u32() { const v = this.dv.getUint32(this.o, true); this.o += 4; return v; }
  align() { this.o = pad8(this.o); return this; }
  arr(Ctor, n) { this.align(); const a = new Ctor(this.buf, this.o, n); this.o += n * Ctor.BYTES_PER_ELEMENT; return a; }
  bytes(n) { this.align(); const a = new Uint8Array(this.buf, this.o, n); this.o += n; return a; }
  left() { return this.buf.byteLength - pad8(this.o); }
}

/** The shards a manifest describes, with their file URLs: format 3 lists shards (paths relative to the db folder),
 * format 2 is one shard (paths relative to the version folder). */
export function shardsOf(manifest, root, base) {
  if (manifest.shards) return manifest.shards.map((sh) => ({ ...sh, url: (f) => root + f.path }));
  const f = manifest.files;
  return [{ id: "all", tier: "core", items: manifest.items, files: { cols: f.cols, strings: f.strings, upc: f.upc, tokens: f.tokens }, url: (x) => base + x.path }];
}

async function openShard(sh, cache) {
  const key = sh.url(sh.files.cols);
  if (loaded.has(key)) return loaded.get(key);
  const [cols, upc, tokens, ...strings] = await Promise.all([sh.files.cols, sh.files.upc, sh.files.tokens, ...sh.files.strings].map((f) => readPack(sh.url(f), cache)));
  const S = { shardId: sh.id, tier: sh.tier, key, bitCache: new Map(), headCache: new Map() };   // S.id is the Walmart id column
  { const r = new Reader(cols); r.magic("SFBC"); const N = r.u32(); S.N = N;
    S.price = r.arr(Uint32Array, N); S.size = r.arr(Float32Array, N); S.pack = r.arr(Uint16Array, N); S.unit = r.arr(Uint8Array, N);
    S.basis = r.arr(Uint8Array, N); S.flags = r.arr(Uint8Array, N); S.cat = r.arr(Uint8Array, N); S.id = r.arr(Float64Array, N); S.upcOf = r.arr(Float64Array, N);
    // format 2 appended flags2, the value basis and Walmart's own price of a withheld item; a format-1 pack has none
    if (pad8(r.o) + N * 9 <= cols.byteLength) { S.flags2 = r.arr(Uint8Array, N); S.valueBasis = r.arr(Uint32Array, N); S.rawPrice = r.arr(Uint32Array, N); }
    else { S.flags2 = new Uint8Array(N); S.valueBasis = new Uint32Array(N).fill(NO_RANK); S.rawPrice = new Uint32Array(N); } }
  S.strings = strings.map((buf) => { const r = new Reader(buf); r.magic("SFBS"); const count = r.u32(), first = r.u32(); const offs = r.arr(Uint32Array, count + 1); const bytes = r.bytes(offs[count]); return { first, count, offs, bytes }; });
  { const r = new Reader(upc); r.magic("SFBU"); const M = r.u32(); S.upcKeys = r.arr(Float64Array, M); S.upcRanks = r.arr(Uint32Array, M); }
  { const r = new Reader(tokens); r.magic("SFBT"); const T = r.u32(), pbytes = r.u32(); const dictOff = r.arr(Uint32Array, T + 1); const dictBytes = r.bytes(dictOff[T]);
    const dict = new Array(T); for (let k = 0; k < T; k++) dict[k] = td.decode(dictBytes.subarray(dictOff[k], dictOff[k + 1]));
    S.dict = dict; S.postOff = r.arr(Uint32Array, T + 1); S.postings = r.bytes(pbytes);
    S.tokCat = r.left() >= T ? r.bytes(T) : new Uint8Array(T);
    if (r.left() >= 4 + 4 * (T + 1)) { r.align(); const hb = r.u32(); S.headOff = r.arr(Uint32Array, T + 1); S.headPostings = r.bytes(hb); }   // format 3
    else { S.headOff = null; S.headPostings = null; } }
  S.words = (S.N + 31) >>> 5;
  loaded.set(key, S);
  return S;
}

function readVersionFile(url, cache, json) {
  return (async () => {
    let res = cache && await cache.match(url);
    if (!res) { res = await fetch(url, { cache: "no-store" }); if (!res.ok) throw new Error(`fetch ${url}: ${res.status}`); if (cache) cache.put(url, res.clone()).catch(() => {}); }
    return json ? JSON.parse(await res.text()) : readPack(url, cache);
  })();
}

/**
 * Open a pack: every shard, or only the ids in `only` (the core first, the rest in a second call with the same
 * manifest). root is the db folder URL, base the version folder URL; cacheName the version's Cache Storage bucket and
 * filesCache the bucket of shard files shared by every version.
 */
async function cachesFor(cacheName, filesCache) {
  // shard files (db/files/) live in the bucket every version shares; manifests and per-version files in the version's
  if (typeof caches === "undefined" || !cacheName) return null;
  const v = await caches.open(cacheName), f = filesCache ? await caches.open(filesCache) : v;
  const pick = (url) => (String(url).includes("/db/files/") ? f : v);
  return { match: (url) => pick(url).match(url), put: (url, res) => pick(url).put(url, res) };
}

async function load({ base, root, manifest, cacheName, filesCache, only }) {
  const cache = await cachesFor(cacheName, filesCache);
  root = root || new URL("../", base).href;
  const t0 = performance.now();
  const all = shardsOf(manifest, root, base);
  const want = only ? all.filter((sh) => only.includes(sh.id)) : all;
  const same = db && db.version === manifest.version;
  let done = 0;
  const total = want.length + (same ? 0 : 2);
  const tick = (file) => postMessage({ type: "progress", done: ++done, total, file });
  const opened = new Map(same ? db.shardsById : []);
  for (const sh of want) { if (!opened.has(sh.id)) opened.set(sh.id, await openShard(sh, cache)); tick(sh.id); }
  const d = same ? db : { manifest, version: manifest.version, shardsById: opened };
  d.shardsById = opened;
  d.shards = all.map((sh) => opened.get(sh.id) || null);      // index = shard number in item ids; null = not loaded yet
  if (!same) {
    const eqFile = manifest.files.equiv;
    const pluFile = manifest.files.plu;
    const eqUrl = manifest.shards ? root + eqFile.path : base + eqFile.path, pluUrl = manifest.shards ? root + pluFile.path : base + pluFile.path;
    const [eqBuf, plu] = await Promise.all([readVersionFile(eqUrl, cache, false), readVersionFile(pluUrl, cache, true)]);
    tick("equiv"); tick("plu");
    { const r = new Reader(eqBuf); r.magic("SFBE"); const E = r.u32(); d.eqKeys = r.arr(Float64Array, E); d.eqEst = r.arr(Uint32Array, E); d.eqBasis = r.arr(Uint32Array, E);
      d.eqBase = r.arr(Float32Array, E); d.eqPack = r.arr(Uint16Array, E); d.eqUnit = r.arr(Uint8Array, E); d.eqConf = r.arr(Uint8Array, E); d.eqOffs = r.arr(Uint32Array, E + 1); d.eqBytes = r.bytes(d.eqOffs[E]); }
    d.plu = new Map(plu.codes.map((c) => [c.plu, c]));
    d.catNames = manifest.categories || null;
    d.v2 = !manifest.shards;
  }
  // shards no new version uses are released
  const keep = new Set(d.shards.filter(Boolean).map((S) => S.key));
  for (const k of [...loaded.keys()]) if (!keep.has(k)) loaded.delete(k);
  d.N = d.shards.reduce((a, S) => a + (S ? S.N : 0), 0);
  d.loadMs = Math.round(performance.now() - t0);
  db = d;
  tokCache.clear();
  setTimeout(warm, 0);
  return { items: d.N, upcs: d.shards.reduce((a, S) => a + (S ? S.upcKeys.length : 0), 0), tokens: d.shards.reduce((a, S) => a + (S ? S.dict.length : 0), 0),
    equivalents: d.eqKeys.length, loadMs: d.loadMs, shards: d.shards.filter(Boolean).map((S) => S.shardId), pending: all.filter((sh) => !opened.has(sh.id)).map((sh) => sh.id) };
}

function warm() {
  // the single-character prefixes are the expensive unions: build them in the background, core shards first
  if (!db) return;
  const jobs = [];
  for (const S of db.shards) if (S && !S.warmed) { S.warmed = true; for (const c of "abcdefghijklmnopqrstuvwxyz0123456789") jobs.push([S, c]); }
  const step = () => { if (!db || !jobs.length) return; const [S, c] = jobs.shift(); prefixBits(S, c); setTimeout(step, 0); };
  step();
}

// ---------------------------------------------------------------- item access
function itemText(S, rank) {
  const s = S.strings.find((sh) => rank >= sh.first && rank < sh.first + sh.count);
  const i = rank - s.first;
  return td.decode(s.bytes.subarray(s.offs[i], s.offs[i + 1]));
}
function itemOf(S, rank, withBasis = true) {
  const si = db.shards.indexOf(S);
  const txt = itemText(S, rank);
  const sep = txt.indexOf("\x1F");
  const flags = S.flags[rank], flags2 = S.flags2[rank];
  const upc = S.upcOf[rank];
  const withheld = !!(flags2 & F2.PRICE_WITHHELD);
  const basisRank = S.valueBasis[rank];
  return {
    rank: gidOf(si, rank), id: S.id[rank], brand: txt.slice(0, sep), name: txt.slice(sep + 1), priceCents: S.price[rank],
    size: S.size[rank] || null, unit: UNIT_NAME[S.unit[rank]], pack: S.pack[rank], basis: S.basis[rank] ? "lb" : "each",
    cat: S.cat[rank], catName: (db.catNames && db.catNames[S.cat[rank]]) || CAT_NAME[S.cat[rank]] || "Other", upc: upc ? String(upc).padStart(14, "0") : null,
    placeholder: !!(flags2 & F2.PLACEHOLDER), discontinued: !!(flags2 & F2.DISCONTINUED), storePrice: !!(flags2 & F2.STORE_PRICE), unitSuspect: !!(flags2 & F2.UNIT_SUSPECT),
    priceWithheld: withheld, rawPriceCents: withheld ? S.rawPrice[rank] : null, valueConfidence: withheld ? VALUE_CONF[(flags2 >> 3) & 3] : null,
    valueBasis: withheld && withBasis && basisRank !== NO_RANK && basisRank !== rank ? itemOf(S, basisRank, false) : null,
    retired: !!(flags & F.RETIRED), noSize: !!(flags & F.NO_SIZE), promo: !!(flags & F.PROMO), carried: !!(flags & F.CARRIED),
    storeBrand: !!(flags & F.STORE_BRAND), primary: !!(flags & F.PRIMARY), sizeConflict: !!(flags & F.SIZE_CONFLICT), unavailable: !!(flags & F.UNAVAILABLE),
  };
}
/** An item by its id across the pack (shard * 2^24 + rank); null when its shard is not loaded. */
function item(g, withBasis = true) {
  const [si, r] = splitGid(Number(g));
  const S = db.shards[si];
  return S && r < S.N ? itemOf(S, r, withBasis) : null;
}

// ---------------------------------------------------------------- UPC / equivalents / PLU
function lowerBound(arr, x) { let lo = 0, hi = arr.length; while (lo < hi) { const mid = (lo + hi) >>> 1; if (arr[mid] < x) lo = mid + 1; else hi = mid; } return lo; }

function lookupUpc(key) {
  const out = [];
  for (const S of db.shards) {
    if (!S) continue;
    const i = lowerBound(S.upcKeys, key);
    for (let j = i; j < S.upcKeys.length && S.upcKeys[j] === key; j++) out.push(itemOf(S, S.upcRanks[j]));
  }
  // the primary listing first (each shard sorts its own primary first; a barcode listed in two departments has one primary)
  return out.sort((a, b) => (b.primary ? 1 : 0) - (a.primary ? 1 : 0));
}

function lookupEquivalent(key) {
  const i = lowerBound(db.eqKeys, key);
  if (i >= db.eqKeys.length || db.eqKeys[i] !== key) return null;
  const txt = td.decode(db.eqBytes.subarray(db.eqOffs[i], db.eqOffs[i + 1]));
  const [brand, name, quantity] = txt.split("\x1F");
  const b = db.eqBasis[i];
  // format 3: shard << 24 | rank; format 2: a plain rank in its only shard
  const basis = b === NO_RANK ? null : db.v2 ? item(b) : item(gidOf(b >>> 24, b & 0xFFFFFF));
  return {
    brand, name, quantity, estCents: db.eqEst[i], baseQty: db.eqBase[i], pack: db.eqPack[i], unit: UNIT_NAME[db.eqUnit[i]],
    confidence: ["low", "medium", "high"][db.eqConf[i]] || "low", basis,
  };
}

function lookupPlu(code) {
  const c = db.plu.get(Number(code));
  if (!c) return null;
  const g = c.rank == null ? null : c.shard != null ? gidOf(c.shard, c.rank) : c.rank;
  return { ...c, item: g != null ? item(g) : null };
}

// ---------------------------------------------------------------- search, per shard
function lowerBoundStr(S, x) { const a = S.dict; let lo = 0, hi = a.length; while (lo < hi) { const mid = (lo + hi) >>> 1; if (a[mid] < x) lo = mid + 1; else hi = mid; } return lo; }
function dictRange(S, prefix) { return [lowerBoundStr(S, prefix), lowerBoundStr(S, prefix + "\uffff")]; }

function orList(bits, bytes, i, end) {
  // decode a varint-delta posting list into the bitset
  let prev = -1;
  while (i < end) {
    let v = 0, shift = 0, b;
    do { b = bytes[i++]; v |= (b & 0x7f) << shift; shift += 7; } while (b & 0x80);
    const r = prev + v + 1; prev = r;
    bits[r >>> 5] |= 1 << (r & 31);
  }
}
function cached(cache, key, make) {
  let bits = cache.get(key);
  if (bits) { cache.delete(key); cache.set(key, bits); return bits; }    // refresh LRU position
  bits = make();
  if (cache.size >= BIT_CACHE_MAX) cache.delete(cache.keys().next().value);
  cache.set(key, bits);
  return bits;
}
function prefixBits(S, prefix) {
  return cached(S.bitCache, prefix, () => { const bits = new Uint32Array(S.words); const [lo, hi] = dictRange(S, prefix); for (let k = lo; k < hi; k++) orList(bits, S.postings, S.postOff[k], S.postOff[k + 1]); return bits; });
}
// items whose head noun (what the listing is) is exactly the word
function headBits(S, word) {
  if (!S.headOff) return null;
  const k = lowerBoundStr(S, word);
  if (k >= S.dict.length || S.dict[k] !== word || S.headOff[k] === S.headOff[k + 1]) return null;
  return cached(S.headCache, word, () => { const bits = new Uint32Array(S.words); orList(bits, S.headPostings, S.headOff[k], S.headOff[k + 1]); return bits; });
}
const hasAnyToken = (prefix) => db.shards.some((S) => { if (!S) return false; const [lo, hi] = dictRange(S, prefix); return hi > lo; });
const hasExactToken = (w) => db.shards.some((S) => { if (!S) return false; const i = lowerBoundStr(S, w); return i < S.dict.length && S.dict[i] === w; });
function popcount(bits) { let c = 0; for (let i = 0; i < bits.length; i++) { let v = bits[i]; v -= (v >>> 1) & 0x55555555; v = (v & 0x33333333) + ((v >>> 2) & 0x33333333); c += (((v + (v >>> 4)) & 0x0f0f0f0f) * 0x01010101) >>> 24; } return c; }

/** Expand the typed tokens into groups; each group is a list of alternative prefixes (OR), groups are ANDed. */
function expand(tokens) {
  const groups = [];   // { alts: [prefixes ORed], src: the word the volunteer typed }
  for (const t of tokens) {
    if (ABBREV[t]) { for (const w of ABBREV[t]) groups.push({ alts: [w], src: t }); continue; }
    const alts = new Set([t]);
    if (SYN.has(t)) for (const w of SYN.get(t)) alts.add(w);
    if (t.length >= 4 && t.endsWith("ies")) alts.add(t.slice(0, -3) + "y");
    else if (t.length >= 6 && /(ches|shes|sses|xes|zes|oes)$/.test(t) && hasExactToken(t.slice(0, -2))) alts.add(t.slice(0, -2));   // boxes, tomatoes, dishes — only when the stem is a real word
    else if (t.length >= 4 && t.endsWith("s")) alts.add(t.slice(0, -1));
    groups.push({ alts: [...alts], src: t });
  }
  return groups;
}

function groupBits(S, alts) {
  let acc = null;
  for (const a of alts) {
    const [lo, hi] = dictRange(S, a);
    if (hi <= lo) continue;
    const b = prefixBits(S, a);
    if (!acc) acc = b.slice(); else for (let i = 0; i < acc.length; i++) acc[i] |= b[i];
  }
  return acc;   // null when no alternative matches any token of this shard
}
function groupHeadBits(S, alts) {
  let acc = null;
  for (const a of alts) { const b = headBits(S, a); if (!b) continue; if (!acc) acc = b.slice(); else for (let i = 0; i < acc.length; i++) acc[i] |= b[i]; }
  return acc;
}

// One-edit variants of a token that exist in the dictionary as prefixes (typo tolerance).
function fuzzyAlternatives(t) {
  if (t.length < 4) return [];
  const out = new Set();
  const letters = "abcdefghijklmnopqrstuvwxyz";
  const tryAdd = (s) => { if (s && s !== t && hasAnyToken(s)) out.add(s); };
  for (let i = 0; i < t.length; i++) {
    tryAdd(t.slice(0, i) + t.slice(i + 1));                                   // deletion
    if (i < t.length - 1) tryAdd(t.slice(0, i) + t[i + 1] + t[i] + t.slice(i + 2));   // transposition
    for (const c of letters) { tryAdd(t.slice(0, i) + c + t.slice(i + 1)); tryAdd(t.slice(0, i) + c + t.slice(i)); }   // substitution, insertion
  }
  tryAdd(t + "s");
  return [...out].slice(0, 12);
}

function collect(bitsets, limit, mask = null, skip = null) {
  // AND all bitsets (and the mask) and collect ranks in ascending (= best-first) order
  const words = bitsets[0].length;
  const out = [];
  for (let w = 0; w < words && out.length < limit; w++) {
    let v = bitsets[0][w];
    for (let g = 1; g < bitsets.length && v; g++) v &= bitsets[g][w];
    if (mask) v &= mask[w];
    if (skip) v &= ~skip[w];
    while (v && out.length < limit) {
      const bit = v & -v;
      out.push((w << 5) + (31 - Math.clz32(bit)));
      v ^= bit;
    }
  }
  return out;
}

const UNIT_WORDS = new Set(["oz", "ounce", "ounces", "fl", "fluid", "lb", "lbs", "pound", "pounds", "ct", "cnt", "count", "pack", "pk", "pc", "pcs", "piece", "pieces", "g", "gram", "grams", "kg", "mg", "mcg", "ml", "l", "liter", "liters", "litre", "litres", "gal", "gallon", "gallons", "qt", "quart", "quarts", "pt", "pint", "pints", "each", "ea", "x", "of", "the", "and", "with", "in", "a", "can", "bag", "box", "bottle", "jar", "cup", "tub", "pouch", "package", "carton", "case", "sq", "ft", "inch", "inches", "mm", "cm"]);
const PLAIN_QUALIFIERS = new Set(["organic", "fresh", "whole", "large", "small", "medium", "jumbo", "original", "classic", "regular", "plain", "pure", "natural", "each", "loose", "family", "size", "value"]);
function numberTokens(tokens) { return tokens.filter((t) => /^\d/.test(t)).map(Number); }

function homeCategories(S, groups) {
  // for every group: the dominant category of the first matching dictionary token, 0 if unclear
  return groups.map((g) => {
    for (const a of g) { const [lo, hi] = dictRange(S, a); if (hi > lo) return S.tokCat[lo]; }
    return 0;
  });
}

// Tokenized names of recently scored items: successive keystrokes narrow the same candidates, so this makes
// scoring mostly allocation-free on a slow phone.
const tokCache = new Map();
function itemTokens(key, it) {
  let t = tokCache.get(key);
  if (!t) {
    const s = it.brand + " " + it.name;
    t = { toks: [...tokenize(s), ...joinedTokens(s)], brandToks: tokenize(it.brand), brandJoined: joinedTokens(it.brand), head: headNoun(it.name) };
    if (tokCache.size > 20000) tokCache.clear();
    tokCache.set(key, t);
  }
  return t;
}

function scoreCandidates(S, ranks, qTokens, groups, typed = null) {
  const nums = numberTokens(qTokens);
  const homes = homeCategories(S, groups);
  const scored = ranks.map((r) => {
    const it = itemOf(S, r);
    const { toks, brandToks, brandJoined, head } = itemTokens(it.rank, it);
    const tokSet = new Set(toks);
    let s = 0;
    let matched = 0;
    for (const g of groups) {
      if (g.some((a) => tokSet.has(a))) {
        s += 2; matched++;                                                         // exact token vs prefix-only
        let tf = 0; for (const t of toks) if (g.includes(t)) tf++;                 // "Corn, Canned Corn" over "Corn Meal"
        if (tf > 1) s += 0.8;
      } else { s += 0.6; if (toks.some((t) => g.some((a) => t.startsWith(a)))) matched++; }
    }
    // coverage: how much of the item's content (brand, numbers and unit words aside) the query explains.
    // "Peanut Butter 16 oz" (2/2) beats "Peanut Butter Cookies 12 ct" (2/3) for the query "peanut butter".
    const content = toks.filter((t) => !/^\d/.test(t) && !UNIT_WORDS.has(t) && !brandToks.includes(t));
    s += 1.5 * Math.min(1, matched / Math.max(1, content.length));
    // the brand counts only when the query names all of it: "tomato sauce" is not a search for the Jersey Tomato brand,
    // "soy sauce" not for Soy Vay
    // brand words must be typed whole ("hot" is not the brand Hotel Doggy), except the word still being typed
    const lastG = groups.length - 1;
    const covers = (g, gi, b) => g.some((a) => a === b || (gi === lastG && b.startsWith(a)) || (b.length > 3 && a === b + "s"));
    const namesBrand = (g) => brandToks.some((b) => covers(g, 0, b)) || brandJoined.some((j) => covers(g, 0, j));
    if (brandToks.length && groups.length && namesBrand(groups[0])
        && (brandToks.every((b) => groups.some((g, gi) => covers(g, gi, b))) || brandJoined.some((j) => groups.some((g, gi) => covers(g, gi, j))))) s += 1.5;
    // the plain item: every word of the listing (brand, sizes and qualifiers aside) is in the query ("Organic Bananas"
    // for "bananas", "Heinz Ketchup, 20 oz" for "ketchup"), not a product made with it ("Banana Pouch")
    // (the word as typed or a listed synonym, not its singular: "Chocolate Chip" cookies are not "chocolate chips")
    if (typed && content.length && content.every((t) => PLAIN_QUALIFIERS.has(t) || typed.some((w, gi) => w.has(t) || (gi === lastG && [...w].some((x) => t.startsWith(x)))))) s += 1.2;
    for (const n of nums) { if ((it.size && Math.abs(it.size - n) < 0.01) || it.pack === n) s += 1.2; }
    s -= 0.03 * Math.max(0, toks.length - groups.length);
    // phrase proximity: query words that sit next to each other in the name are the item the volunteer means
    let first = -1, last = -1;
    for (const g of groups) { const pos = toks.findIndex((t) => g.some((a) => t.startsWith(a))); if (pos >= 0) { if (first < 0 || pos < first) first = pos; if (pos > last) last = pos; } }
    if (first >= 0 && groups.length > 1) s += 1.2 * groups.length / Math.max(groups.length, last - first + 1);
    for (const h of homes) if (h && h === it.cat) s += 0.8;
    if (head && groups.some((g) => g.some((a) => head === a || (a.length >= 4 && head.startsWith(a))))) s += 1.6;
    else if (head && toks.length) s -= 0.6;          // the query's words only describe it: a diaper *bag*, a tomato *basket*
    if (it.storeBrand) s += 0.3;
    if (it.retired) s -= 1.5;
    if (it.unavailable) s -= 0.4;
    s -= (r / S.N) * 0.8;             // rank within the shard as the final tiebreaker
    if (globalThis.SFB_SCORE_DEBUG) it._score = Math.round(s * 100) / 100;
    return { it, s };
  });
  return scored;
}

// exact number of items matching every live group (AND of the bitsets), for the "N matches" line
function andCount(bs) {
  let n = 0;
  const w = bs[0].length;
  for (let i = 0; i < w; i++) {
    let v = bs[0][i];
    for (let k = 1; k < bs.length; k++) v &= bs[k][i];
    v = v - ((v >>> 1) & 0x55555555);
    v = (v & 0x33333333) + ((v >>> 2) & 0x33333333);
    n += (((v + (v >>> 4)) & 0x0f0f0f0f) * 0x01010101) >>> 24;
  }
  return n;
}

function search(q, limit = 40) {
  const t0 = performance.now();
  const tokens = tokenize(q).filter(Boolean);
  if (!tokens.length) return { query: q, items: [], relaxed: false, fuzzy: false, ms: 0, total: 0 };
  const shards = db.shards.filter(Boolean);
  let groups = expand(tokens);
  const matches = (g) => g.alts.some((a) => hasAnyToken(a));
  let fuzzy = false, relaxed = false;
  const dropped = [];
  // typo tolerance: a group that matches nothing in any shard gets one-edit alternatives
  if (groups.some((g) => !matches(g))) {
    groups = groups.map((g) => (matches(g) || /^\d/.test(g.src) ? g : { ...g, alts: [...g.alts, ...fuzzyAlternatives(g.alts[0])] }));
    fuzzy = groups.some((g) => g.alts.length > 1 && matches(g) && !hasAnyToken(g.src) && !SYN.has(g.src) && !ABBREV[g.src]);   // a typo was actually corrected
  }
  // a word that still matches nothing is dropped and named, so the result is flagged, never silently widened
  let live = [];
  for (const g of groups) { if (matches(g)) live.push(g); else if (!dropped.includes(g.src)) { dropped.push(g.src); relaxed = true; } }
  if (!live.length) return { query: q, items: [], relaxed: false, dropped, fuzzy, ms: performance.now() - t0, total: 0 };
  // per shard: the bitset of every live group (null: the word is not in this shard, so nothing here matches all)
  const perShard = shards.map((S) => ({ S, bits: live.map((g) => groupBits(S, g.alts)) }));
  const anyAll = (keep) => perShard.some(({ bits }) => { const bs = bits.filter((_, i) => keep(i)); return bs.every(Boolean) && collect(bs, 1).length > 0; });
  // never blank: relax one word at a time. The word dropped is the least informative one (the most common) among those
  // whose removal leaves something to show: "great value dry pinto beans" drops "dry" and keeps "pinto"; dropping the
  // rarest word, as before, threw away exactly the word that says what the item is.
  while (live.length > 1 && !anyAll(() => true)) {
    const counts = live.map((_, i) => perShard.reduce((a, { bits }) => a + (bits[i] ? popcount(bits[i]) : 0), 0));
    let pick = -1;
    for (let i = 0; i < live.length; i++) {
      if (pick >= 0 && counts[i] <= counts[pick]) continue;
      if (anyAll((j) => j !== i)) pick = i;
    }
    if (pick < 0) pick = counts.indexOf(Math.max(...counts));   // no single word frees a result: drop the most common, go on
    if (!dropped.includes(live[pick].src)) dropped.push(live[pick].src);
    live = live.filter((_, j) => j !== pick);
    for (const p of perShard) p.bits = p.bits.filter((_, j) => j !== pick);
    relaxed = true;
  }
  // candidates per shard, best rank first: items that ARE what a query word names (head noun) before items that only
  // carry the word, so "bananas" reaches the fresh bananas before a thousand banana-flavoured things
  const CAND = Math.max(limit * 10, 400);
  let scored = [], total = 0;
  const alts = live.map((g) => g.alts);
  const sameWord = (a, b) => a === b || a === b + "s" || b === a + "s" || a === b + "es" || b === a + "es";
  const typed = live.map((g) => new Set([g.src, ...(SYN.get(g.src) || []).filter((w) => !sameWord(w, g.src)), ...(ABBREV[g.src] ? g.alts : [])]));
  // one candidate budget shared by the shards, in proportion to their matches (each keeps a floor), so a one-letter
  // query that matches in every shard scores about CAND items in all, not CAND per shard
  const counts = perShard.map(({ bits }) => (bits.every(Boolean) ? andCount(bits) : 0));
  const sum = counts.reduce((a, b) => a + b, 0);
  const POOL = CAND, FLOOR = limit;
  perShard.forEach((p, i) => { p.n = counts[i]; p.cand = Math.min(CAND, Math.max(FLOOR, Math.ceil(POOL * counts[i] / Math.max(1, sum)))); });
  for (const { S, bits, n, cand } of perShard) {
    if (!n) continue;
    total += n;
    let heads = null;
    for (const g of live) { const h = groupHeadBits(S, g.alts); if (h) { if (!heads) heads = h; else for (let i = 0; i < heads.length; i++) heads[i] |= h[i]; } }
    // at most half the pool from head matches, the rest in plain rank order, so a word that is also a common head
    // elsewhere ("dogs" in "Coat For Dogs") cannot crowd out the item ("Hot Dogs") the rank order would have found
    let ranks = heads ? collect(bits, cand >> 1, heads) : [];
    if (ranks.length < cand) {
      const seen = new Set(ranks);
      for (const r of collect(bits, cand)) { if (ranks.length >= cand) break; if (!seen.has(r)) ranks.push(r); }
    }
    scored = scored.concat(scoreCandidates(S, ranks, tokens, alts, typed));
  }
  scored.sort((a, b) => b.s - a.s || a.it.rank - b.it.rank);
  const items = scored.slice(0, limit).map((x) => x.it);
  return { query: q, items, relaxed, dropped, fuzzy, total, ms: Math.round((performance.now() - t0) * 100) / 100 };
}

// ---------------------------------------------------------------- messages
self.onmessage = async (e) => {
  const m = e.data;
  try {
    switch (m.type) {
      case "load": { const stats = await load(m); postMessage({ type: "ready", id: m.id, stats }); break; }
      case "search": { postMessage({ type: "result", id: m.id, result: db ? search(m.q, m.limit) : { query: m.q, items: [], notReady: true } }); break; }
      case "upc": { postMessage({ type: "result", id: m.id, result: db ? { items: lookupUpc(m.key), equivalent: lookupEquivalent(m.key) } : { notReady: true } }); break; }
      case "plu": { postMessage({ type: "result", id: m.id, result: db ? lookupPlu(m.code) : { notReady: true } }); break; }
      case "item": { postMessage({ type: "result", id: m.id, result: db ? item(m.rank) : null }); break; }
      case "unload": { db = null; loaded.clear(); tokCache.clear(); postMessage({ type: "result", id: m.id, result: true }); break; }
      default: postMessage({ type: "error", id: m.id, error: "unknown message " + m.type });
    }
  } catch (err) {
    postMessage({ type: "error", id: m.id, error: String(err && err.stack || err) });
  }
};

// for tools/search-harness.mjs (Node: tests and the gold search set); a module worker ignores exports
export { load, search, lookupUpc, lookupEquivalent, lookupPlu, item };
