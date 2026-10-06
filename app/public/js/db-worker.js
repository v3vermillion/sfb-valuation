// db-worker.js — the database lives here, off the main thread.
//
// Loads the sfb-pack files (see tools/build-db.mjs for the layout), keeps them as typed-array views, and
// answers: search(query) within a frame, lookup(gtin), equivalent(gtin), plu(code), item(rank).
// Items are stored in rank order (best first), so a bitset scan from rank 0 already yields best-first results.
import { tokenize } from "./tokenize.js";

const te = new TextEncoder(), td = new TextDecoder();
const F = { RETIRED: 1, NO_SIZE: 2, PROMO: 4, CARRIED: 8, STORE_BRAND: 16, PRIMARY: 32, SIZE_CONFLICT: 64, UNAVAILABLE: 128 };
const UNIT_NAME = [null, "oz", "fl oz", "lb", "ct", "g", "kg", "ml", "l", "gal", "qt", "pt"];
const CAT_NAME = { 1: "Produce", 2: "Dairy & Eggs", 3: "Meat & Seafood", 4: "Deli & Prepared", 5: "Frozen", 6: "Canned & Jarred", 7: "Dry Goods & Baking", 8: "Bread & Bakery", 9: "Snacks & Candy", 10: "Beverages", 11: "Condiments & Sauces", 12: "International & Specialty", 13: "Baby", 14: "Health", 15: "Personal Care & Beauty", 16: "Household & Paper", 17: "Kitchen & Storage", 18: "Home", 19: "Pet", 20: "School, Office & Crafts", 21: "Toys, Books & Games", 22: "Seasonal & Party", 23: "Other", 24: "Auto", 25: "Electronics", 26: "Jewelry", 27: "Sports & Outdoors" };

// Query-time vocabulary: abbreviations volunteers actually type (AND-expansions) and spellings that
// should match each other (OR-groups). Index tokens are never altered; this only widens the query.
const ABBREV = {
  gv: ["great", "value"], pb: ["peanut", "butter"], pbj: ["peanut", "butter"], mac: ["macaroni"], "mac&cheese": ["macaroni", "cheese"],
  tp: ["toilet", "paper"], pt: ["paper", "towels"], hbs: ["head", "shoulders"], "h&s": ["head", "shoulders"], "a&h": ["arm", "hammer"],
  oj: ["orange", "juice"], aj: ["apple", "juice"], ev: ["extra", "virgin"], evoo: ["extra", "virgin", "olive", "oil"], gf: ["gluten", "free"],
  sf: ["sugar", "free"], ls: ["low", "sodium"], nsa: ["no", "salt", "added"], ww: ["whole", "wheat"], wg: ["whole", "grain"],
  kd: ["kraft", "macaroni"], veg: ["vegetable"], veggies: ["vegetable"], choc: ["chocolate"], vit: ["vitamin"], deod: ["deodorant"],
  shamp: ["shampoo"], cond: ["conditioner"], det: ["detergent"], bbq: ["barbecue"], mayo: ["mayonnaise"], ketchup: ["ketchup"],
  pnut: ["peanut"], spag: ["spaghetti"], marg: ["margarine"], tom: ["tomato"], toms: ["tomato"],
};
const SYNONYM_GROUPS = [
  ["oz", "ounce", "ounces"], ["fl", "fluid"], ["lb", "lbs", "pound", "pounds"], ["ct", "count", "cnt", "pk", "pack", "packs"],
  ["gal", "gallon", "gallons"], ["qt", "quart", "quarts"], ["l", "liter", "liters", "litre", "litres", "ltr"], ["ml", "milliliter", "milliliters"],
  ["g", "gram", "grams"], ["kg", "kilogram", "kilograms"], ["and", "n"], ["mac", "macaroni"], ["ketchup", "catsup"], ["soda", "pop"],
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

let db = null;        // { N, cols..., strings[], upc, tokens, equiv, plu, manifest }
const bitCache = new Map();   // prefix -> Uint32Array bitset (LRU-ish, capped)
const BIT_CACHE_MAX = 96;

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
}

async function load({ base, manifest, cacheName }) {
  const cache = (typeof caches !== "undefined" && cacheName) ? await caches.open(cacheName) : null;
  const files = [["cols", manifest.files.cols.path], ...manifest.files.strings.map((s, i) => [`strings${i}`, s.path]), ["upc", manifest.files.upc.path], ["tokens", manifest.files.tokens.path], ["equiv", manifest.files.equiv.path], ["plu", manifest.files.plu.path]];
  const total = files.length;
  let done = 0;
  const t0 = performance.now();
  const bufs = {};
  await Promise.all(files.map(async ([k, p]) => {
    const url = base + p;
    if (k === "plu") { const res = (cache && await cache.match(url)) || await fetch(url); const txt = await res.clone().text(); if (cache) cache.put(url, res.clone()).catch(() => {}); bufs[k] = JSON.parse(txt); }
    else bufs[k] = await readPack(url, cache);
    done++;
    postMessage({ type: "progress", done, total, file: p });
  }));
  const d = { manifest, loadMs: 0 };
  // cols
  { const r = new Reader(bufs.cols); r.magic("SFBC"); const N = r.u32(); d.N = N;
    d.price = r.arr(Uint32Array, N); d.size = r.arr(Float32Array, N); d.pack = r.arr(Uint16Array, N); d.unit = r.arr(Uint8Array, N);
    d.basis = r.arr(Uint8Array, N); d.flags = r.arr(Uint8Array, N); d.cat = r.arr(Uint8Array, N); d.id = r.arr(Float64Array, N); d.upcOf = r.arr(Float64Array, N); }
  // strings
  d.strings = manifest.files.strings.map((s, i) => { const r = new Reader(bufs[`strings${i}`]); r.magic("SFBS"); const count = r.u32(), first = r.u32(); const offs = r.arr(Uint32Array, count + 1); const bytes = r.bytes(offs[count]); return { first, count, offs, bytes }; });
  // upc
  { const r = new Reader(bufs.upc); r.magic("SFBU"); const M = r.u32(); d.upcKeys = r.arr(Float64Array, M); d.upcRanks = r.arr(Uint32Array, M); }
  // tokens
  { const r = new Reader(bufs.tokens); r.magic("SFBT"); const T = r.u32(), pbytes = r.u32(); const dictOff = r.arr(Uint32Array, T + 1); const dictBytes = r.bytes(dictOff[T]);
    const dict = new Array(T); for (let k = 0; k < T; k++) dict[k] = td.decode(dictBytes.subarray(dictOff[k], dictOff[k + 1]));
    d.dict = dict; d.postOff = r.arr(Uint32Array, T + 1); d.postings = r.bytes(pbytes);
    r.align(); d.tokCat = (r.o + T <= bufs.tokens.byteLength) ? r.bytes(T) : new Uint8Array(T); }
  // equivalents
  { const r = new Reader(bufs.equiv); r.magic("SFBE"); const E = r.u32(); d.eqKeys = r.arr(Float64Array, E); d.eqEst = r.arr(Uint32Array, E); d.eqBasis = r.arr(Uint32Array, E);
    d.eqBase = r.arr(Float32Array, E); d.eqPack = r.arr(Uint16Array, E); d.eqUnit = r.arr(Uint8Array, E); d.eqConf = r.arr(Uint8Array, E); d.eqOffs = r.arr(Uint32Array, E + 1); d.eqBytes = r.bytes(d.eqOffs[E]); }
  d.plu = new Map(bufs.plu.codes.map((c) => [c.plu, c]));
  d.words = (d.N + 31) >>> 5;
  d.loadMs = Math.round(performance.now() - t0);
  db = d;
  bitCache.clear();
  // warm the single-character prefixes in the background (they are the expensive unions)
  setTimeout(warm, 0);
  return { items: d.N, upcs: d.upcKeys.length, tokens: d.dict.length, equivalents: d.eqKeys.length, loadMs: d.loadMs };
}

let warmed = false;
function warm() {
  if (warmed || !db) return;
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789".split("");
  let i = 0;
  const step = () => { if (!db || i >= chars.length) { warmed = true; return; } prefixBits(chars[i++]); setTimeout(step, 0); };
  step();
}

// ---------------------------------------------------------------- item access
function itemText(rank) {
  const s = db.strings.find((sh) => rank >= sh.first && rank < sh.first + sh.count);
  const i = rank - s.first;
  return td.decode(s.bytes.subarray(s.offs[i], s.offs[i + 1]));
}
function item(rank) {
  const txt = itemText(rank);
  const sep = txt.indexOf("\x1F");
  const flags = db.flags[rank];
  const upc = db.upcOf[rank];
  return {
    rank, id: db.id[rank], brand: txt.slice(0, sep), name: txt.slice(sep + 1), priceCents: db.price[rank],
    size: db.size[rank] || null, unit: UNIT_NAME[db.unit[rank]], pack: db.pack[rank], basis: db.basis[rank] ? "lb" : "each",
    cat: db.cat[rank], catName: CAT_NAME[db.cat[rank]] || "Other", upc: upc ? String(upc).padStart(14, "0") : null,
    retired: !!(flags & F.RETIRED), noSize: !!(flags & F.NO_SIZE), promo: !!(flags & F.PROMO), carried: !!(flags & F.CARRIED),
    storeBrand: !!(flags & F.STORE_BRAND), primary: !!(flags & F.PRIMARY), sizeConflict: !!(flags & F.SIZE_CONFLICT), unavailable: !!(flags & F.UNAVAILABLE),
  };
}

// ---------------------------------------------------------------- UPC / equivalents / PLU
function lowerBound(arr, x) { let lo = 0, hi = arr.length; while (lo < hi) { const mid = (lo + hi) >>> 1; if (arr[mid] < x) lo = mid + 1; else hi = mid; } return lo; }

function lookupUpc(key) {
  const i = lowerBound(db.upcKeys, key);
  const ranks = [];
  for (let j = i; j < db.upcKeys.length && db.upcKeys[j] === key; j++) ranks.push(db.upcRanks[j]);
  return ranks.map(item);   // primary first (builder sorts it first)
}

function lookupEquivalent(key) {
  const i = lowerBound(db.eqKeys, key);
  if (i >= db.eqKeys.length || db.eqKeys[i] !== key) return null;
  const txt = td.decode(db.eqBytes.subarray(db.eqOffs[i], db.eqOffs[i + 1]));
  const [brand, name, quantity] = txt.split("\x1F");
  const basisRank = db.eqBasis[i];
  return {
    brand, name, quantity, estCents: db.eqEst[i], baseQty: db.eqBase[i], pack: db.eqPack[i], unit: UNIT_NAME[db.eqUnit[i]],
    confidence: ["low", "medium", "high"][db.eqConf[i]] || "low", basis: basisRank === 0xFFFFFFFF ? null : item(basisRank),
  };
}

function lookupPlu(code) {
  const c = db.plu.get(Number(code));
  if (!c) return null;
  return { ...c, item: c.rank != null ? item(c.rank) : null };
}

// ---------------------------------------------------------------- search
function dictRange(prefix) {
  // [lo, hi) of dictionary entries starting with prefix
  const lo = lowerBoundStr(prefix);
  let hi = lo;
  // binary search for the end: first token >= prefix + "￿"
  hi = lowerBoundStr(prefix + "￿");
  return [lo, hi];
}
function lowerBoundStr(x) { const a = db.dict; let lo = 0, hi = a.length; while (lo < hi) { const mid = (lo + hi) >>> 1; if (a[mid] < x) lo = mid + 1; else hi = mid; } return lo; }

function orPostings(bits, k) {
  // decode the varint-delta posting list of token k into the bitset
  const p = db.postings;
  let i = db.postOff[k]; const end = db.postOff[k + 1];
  let prev = -1;
  while (i < end) {
    let v = 0, shift = 0, b;
    do { b = p[i++]; v |= (b & 0x7f) << shift; shift += 7; } while (b & 0x80);
    const r = prev + v + 1; prev = r;
    bits[r >>> 5] |= 1 << (r & 31);
  }
}

function prefixBits(prefix) {
  let bits = bitCache.get(prefix);
  if (bits) { bitCache.delete(prefix); bitCache.set(prefix, bits); return bits; }   // refresh LRU position
  bits = new Uint32Array(db.words);
  const [lo, hi] = dictRange(prefix);
  for (let k = lo; k < hi; k++) orPostings(bits, k);
  if (bitCache.size >= BIT_CACHE_MAX) bitCache.delete(bitCache.keys().next().value);
  bitCache.set(prefix, bits);
  return bits;
}
function hasAnyToken(prefix) { const [lo, hi] = dictRange(prefix); return hi > lo; }
function popcount(bits) { let c = 0; for (let i = 0; i < bits.length; i++) { let v = bits[i]; v -= (v >>> 1) & 0x55555555; v = (v & 0x33333333) + ((v >>> 2) & 0x33333333); c += (((v + (v >>> 4)) & 0x0f0f0f0f) * 0x01010101) >>> 24; } return c; }

/** Expand the typed tokens into groups; each group is a list of alternative prefixes (OR), groups are ANDed. */
function expand(tokens) {
  const groups = [];
  for (const t of tokens) {
    if (ABBREV[t]) { for (const w of ABBREV[t]) groups.push([w]); continue; }
    const alts = new Set([t]);
    if (SYN.has(t)) for (const w of SYN.get(t)) alts.add(w);
    if (t.length >= 4 && t.endsWith("ies")) alts.add(t.slice(0, -3) + "y");
    else if (t.length >= 4 && t.endsWith("es")) alts.add(t.slice(0, -2));
    else if (t.length >= 4 && t.endsWith("s")) alts.add(t.slice(0, -1));
    groups.push([...alts]);
  }
  return groups;
}

function groupBits(alts) {
  let acc = null;
  for (const a of alts) {
    if (!hasAnyToken(a)) continue;
    const b = prefixBits(a);
    if (!acc) acc = b.slice(); else for (let i = 0; i < acc.length; i++) acc[i] |= b[i];
  }
  return acc;   // null when no alternative matches any token
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

function collect(bitsets, limit) {
  // AND all bitsets and collect ranks in ascending (= best-first) order
  const words = db.words;
  const out = [];
  for (let w = 0; w < words && out.length < limit; w++) {
    let v = bitsets[0][w];
    for (let g = 1; g < bitsets.length && v; g++) v &= bitsets[g][w];
    while (v && out.length < limit) {
      const bit = v & -v;
      const r = (w << 5) + (31 - Math.clz32(bit));
      out.push(r);
      v ^= bit;
    }
  }
  return out;
}

const UNIT_WORDS = new Set(["oz", "ounce", "ounces", "fl", "lb", "lbs", "pound", "pounds", "ct", "count", "pack", "pk", "pc", "pcs", "piece", "pieces", "g", "gram", "grams", "kg", "ml", "l", "liter", "litre", "gal", "gallon", "qt", "quart", "pt", "pint", "each", "ea", "x", "of", "the", "and", "with", "in", "a", "can", "bag", "box", "bottle", "jar", "cup", "tub", "pouch", "package", "carton", "case"]);
function numberTokens(tokens) { return tokens.filter((t) => /^\d/.test(t)).map(Number); }

function homeCategories(groups) {
  // for every group: the dominant category of the first matching dictionary token, 0 if unclear
  return groups.map((g) => {
    for (const a of g) { const [lo, hi] = dictRange(a); if (hi > lo) return db.tokCat[lo]; }
    return 0;
  });
}

// Tokenized names of recently scored items: successive keystrokes narrow the same candidates, so this makes
// scoring mostly allocation-free on a slow phone.
const tokCache = new Map();
function itemTokens(rank, it) {
  let t = tokCache.get(rank);
  if (!t) { t = tokenize(it.brand + " " + it.name); if (tokCache.size > 6000) tokCache.clear(); tokCache.set(rank, t); }
  return t;
}

function scoreCandidates(ranks, qTokens, groups) {
  const nums = numberTokens(qTokens);
  const homes = homeCategories(groups);
  const scored = ranks.map((r) => {
    const it = item(r);
    const toks = itemTokens(r, it);
    const tokSet = new Set(toks);
    let s = 0;
    const brandToks = tokenize(it.brand);
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
    if (brandToks.length && groups.length && groups[0].some((a) => brandToks.some((b) => b.startsWith(a)))) s += 1.5;
    for (const n of nums) { if (it.size === n || it.pack === n) s += 1.2; }
    s -= 0.03 * Math.max(0, toks.length - groups.length);
    // phrase proximity: query words that sit next to each other in the name are the item the volunteer means
    let first = -1, last = -1;
    for (const g of groups) { const pos = toks.findIndex((t) => g.some((a) => t.startsWith(a))); if (pos >= 0) { if (first < 0 || pos < first) first = pos; if (pos > last) last = pos; } }
    if (first >= 0 && groups.length > 1) s += 1.2 * groups.length / Math.max(groups.length, last - first + 1);
    for (const h of homes) if (h && h === it.cat) s += 0.8;
    if (it.storeBrand) s += 0.3;
    if (it.retired) s -= 1.5;
    if (it.unavailable) s -= 0.4;
    s -= (r / db.N) * 0.8;            // global rank as the final tiebreaker
    return { it, s };
  });
  scored.sort((a, b) => b.s - a.s || a.it.rank - b.it.rank);
  return scored.map((x) => x.it);
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
  let groups = expand(tokens);
  let bitsets = groups.map(groupBits);
  let fuzzy = false, relaxed = false, dropped = [];
  // typo tolerance: a group that matches nothing at all gets one-edit alternatives
  if (bitsets.some((b) => !b)) {
    groups = groups.map((g, i) => (bitsets[i] ? g : [...g, ...fuzzyAlternatives(g[0])]));
    bitsets = groups.map(groupBits);
    fuzzy = true;
  }
  let live = groups.map((g, i) => ({ g, b: bitsets[i] })).filter((x) => x.b);
  if (!live.length) return { query: q, items: [], relaxed: false, fuzzy, ms: performance.now() - t0, total: 0 };
  const CAND = Math.max(limit * 10, 400);   // candidates scored per query; long Walmart names rank low globally, so the pool must be deep enough to include them
  let ranks = collect(live.map((x) => x.b), CAND);
  // never blank: relax by dropping the most restrictive group until something matches
  while (!ranks.length && live.length > 1) {
    let worst = 0, worstCount = Infinity;
    live.forEach((x, i) => { const c = popcount(x.b); if (c < worstCount) { worstCount = c; worst = i; } });
    dropped.push(live[worst].g[0]);
    live.splice(worst, 1);
    relaxed = true;
    ranks = collect(live.map((x) => x.b), CAND);
  }
  const items = scoreCandidates(ranks, tokens, live.map((x) => x.g)).slice(0, limit);
  return { query: q, items, relaxed, dropped, fuzzy, total: andCount(live.map((x) => x.b)), ms: Math.round((performance.now() - t0) * 100) / 100 };
}

// ---------------------------------------------------------------- messages
self.onmessage = async (e) => {
  const m = e.data;
  try {
    switch (m.type) {
      case "load": { const stats = await load(m); postMessage({ type: "ready", id: m.id, stats }); break; }
      case "search": { postMessage({ type: "result", id: m.id, result: db ? search(m.q, m.limit) : { query: m.q, items: [], notReady: true } }); break; }
      case "upc": { postMessage({ type: "result", id: m.id, result: db ? { items: lookupUpc(m.key), equivalent: lookupEquivalent(m.key) } : { notReady: true } }); break; }
      case "plu": { postMessage({ type: "result", id: m.id, result: db ? lookupPlu(m.code) : null }); break; }
      case "item": { postMessage({ type: "result", id: m.id, result: db ? item(m.rank) : null }); break; }
      case "unload": { db = null; bitCache.clear(); tokCache.clear(); warmed = false; postMessage({ type: "result", id: m.id, result: true }); break; }
      default: postMessage({ type: "error", id: m.id, error: "unknown message " + m.type });
    }
  } catch (err) {
    postMessage({ type: "error", id: m.id, error: String(err && err.stack || err) });
  }
};
