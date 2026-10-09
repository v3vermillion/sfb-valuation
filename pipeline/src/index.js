// sfb-pipeline — signs Walmart I/O Affiliate API requests.
// Secrets (Cloudflare): WM_PRIVATE_KEY, WM_CONSUMER_ID, ADMIN_TOKEN. Var: WM_KEY_VERSION.

const API = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2";

function pemToDer(pem) {
  const b64 = pem
    .replace(/\\n/g, "\n")
    .replace(/-----BEGIN [^-]+-----/, "")
    .replace(/-----END [^-]+-----/, "")
    .replace(/\s+/g, "");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

let cachedKey = null;
async function privateKey(env) {
  if (!cachedKey) {
    cachedKey = await crypto.subtle.importKey(
      "pkcs8", pemToDer(env.WM_PRIVATE_KEY),
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  }
  return cachedKey;
}

async function walmartHeaders(env) {
  const ts = Date.now().toString();
  const ver = env.WM_KEY_VERSION || "1";
  const toSign = `${env.WM_CONSUMER_ID}\n${ts}\n${ver}\n`;
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", await privateKey(env), new TextEncoder().encode(toSign));
  return {
    "WM_CONSUMER.ID": env.WM_CONSUMER_ID,
    "WM_CONSUMER.INTIMESTAMP": ts,
    "WM_SEC.KEY_VERSION": ver,
    "WM_SEC.AUTH_SIGNATURE": btoa(String.fromCharCode(...new Uint8Array(sig))),
    "Accept": "application/json",
  };
}

const HOST = "https://developer.api.walmart.com";

// Accepts "/taxonomy", "/paginated/items?...", "/api-proxy/...", or a full URL (nextPage formats vary).
function walmartUrl(pathOrUrl) {
  if (/^https?:\/\//.test(pathOrUrl)) return pathOrUrl;
  if (pathOrUrl.startsWith("/api-proxy/")) return HOST + pathOrUrl;
  return API + pathOrUrl;
}

export async function walmartGet(env, pathOrUrl) {
  const res = await fetch(walmartUrl(pathOrUrl), { headers: await walmartHeaders(env) });
  const body = await res.text();
  return { status: res.status, body };
}

// Compact view of one item: every field we might need for the schema, nothing else.
function summarizeItem(it) {
  return {
    itemId: it.itemId, parentItemId: it.parentItemId, upc: it.upc,
    name: it.name, brandName: it.brandName, size: it.size,
    salePrice: it.salePrice, msrp: it.msrp, offerType: it.offerType, marketplace: it.marketplace,
    sellerInfo: it.sellerInfo, availableOnline: it.availableOnline, stock: it.stock,
    categoryPath: it.categoryPath, categoryNode: it.categoryNode,
  };
}

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj, null, 2), { status, headers: { "content-type": "application/json" } });

// ---------------------------------------------------------------------------------------------
// Public live price check for the app: GET /v1/price/<gtin>
// No admin token (the app has none). Guarded by: strict GTIN validation, a Cloudflare rate limit binding
// (per client IP, see wrangler.toml [[ratelimits]]), a 6-hour edge cache per GTIN, and a tight CORS policy
// (GET only, no credentials). Applies the same Walmart-sold-only rule as crawler/normalize.py.

const PRICE_TTL_SECONDS = 6 * 60 * 60;
const THROTTLE_TTL_SECONDS = 60;          // how long a Walmart 429/5xx answer is remembered so the shared key is not hammered
const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, OPTIONS",
  "access-control-allow-headers": "accept",
  "access-control-max-age": "86400",
  "vary": "origin",
};
const pub = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", "cache-control": "no-store", ...CORS, ...extra } });

function gs1CheckDigit(body) {
  let sum = 0;
  for (let i = 0; i < body.length; i++) sum += Number(body[body.length - 1 - i]) * (i % 2 === 0 ? 3 : 1);
  return (10 - (sum % 10)) % 10;
}

// Accept 8/12/13/14 digit codes; return the 14-digit GTIN or null. Store labels (prefix 2) and PLUs are not Walmart items.
function parseGtin(raw) {
  const d = String(raw || "").replace(/\D/g, "");
  if (![8, 12, 13, 14].includes(d.length)) return null;
  if (gs1CheckDigit(d.slice(0, -1)) !== Number(d.at(-1))) return null;
  const g14 = d.padStart(14, "0");
  if (/^0{14}$/.test(g14)) return null;
  const upcA = g14.replace(/^0+(?=\d{12}$)/, "");
  if (upcA.length === 12 && upcA[0] === "2") return null;
  return g14;
}

function walmartSold(it) {
  if (it.marketplace === true) return false;
  const seller = (it.sellerInfo || "").trim().toLowerCase();
  if (seller && seller !== "walmart.com") return false;
  return typeof it.salePrice === "number" && it.salePrice > 0;
}

// Two limits guard the shared Walmart key: per caller (30/min per IP) and in aggregate (60 Walmart calls/min
// across everyone), both charged only when a Walmart call is actually about to be made. A deploy without the
// bindings fails closed: the route answers 503 rather than serving the key without a cap.
async function rateLimited(env, req) {
  if (!env.PRICE_LIMITER || !env.PRICE_GLOBAL_LIMITER) return env.ALLOW_UNLIMITED_DEV === "1" ? false : "not configured";
  const ip = req.headers.get("cf-connecting-ip") || "unknown";
  const per = await env.PRICE_LIMITER.limit({ key: ip });
  if (!per.success) return "rate limited";
  const all = await env.PRICE_GLOBAL_LIMITER.limit({ key: "walmart" });
  if (!all.success) return "rate limited";
  return false;
}

async function livePrice(req, env, ctx, gtinRaw) {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
  if (req.method !== "GET") return pub({ ok: false, reason: "method" }, 405);
  const gtin = parseGtin(gtinRaw);
  if (!gtin) return pub({ ok: false, reason: "not a product barcode" }, 400);

  // Edge cache keyed by GTIN only (never by client), so one Walmart call serves every volunteer for 6 hours.
  // Hits are answered before any rate limit is charged, and are never cached again by the phone.
  const cache = caches.default;
  // v2: answers carry the store's own price (STORE_ID); v1 entries held Walmart.com's and are never read again
  const cacheKey = new Request(`https://cache.sfb-valuation.internal/v2/price/${gtin}`, { method: "GET" });
  const hit = await cache.match(cacheKey);
  if (hit) {
    const h = new Headers(hit.headers);
    h.set("x-cache", "hit"); h.set("cache-control", "no-store");
    for (const [k, v] of Object.entries(CORS)) h.set(k, v);
    return new Response(hit.body, { status: hit.status, headers: h });
  }

  const limited = await rateLimited(env, req);
  if (limited === "not configured") return pub({ ok: false, reason: "not configured" }, 503, { "retry-after": "300" });
  if (limited) return pub({ ok: false, reason: "rate limited" }, 429, { "retry-after": "60" });
  if (!env.WM_PRIVATE_KEY || !env.WM_CONSUMER_ID) return pub({ ok: false, reason: "not configured" }, 503, { "retry-after": "300" });

  let payload, status = 200, ttl = PRICE_TTL_SECONDS;
  try {
    // UPC-A (12 digits, also when scanned as a 0-prefixed EAN-13) uses the upc parameter; everything else the 14-digit gtin.
    const raw = String(gtinRaw).replace(/\D/g, "");
    const upcA = gtin.replace(/^0+(?=\d{12}$)/, "");
    // STORE_ID (wrangler.toml): Walmart answers with that store's own shelf price and stock (the app's offline prices
    // are the same store's, data/store.json)
    const store = /^\d{1,6}$/.test(String(env.STORE_ID || "")) ? String(env.STORE_ID) : null;
    const path = (upcA.length === 12 && (raw.length === 12 || raw.length === 13) ? `/items?upc=${upcA}` : `/items?gtin=${gtin}`)
      + (store ? `&storeId=${store}` : "");
    const r = await walmartGet(env, path);
    if (r.status === 404) payload = { ok: false, reason: "not found", gtin };
    else if (r.status === 429 || r.status >= 500) { status = 503; ttl = THROTTLE_TTL_SECONDS; payload = { ok: false, reason: "walmart unavailable", gtin }; }
    else if (r.status !== 200) { status = 502; payload = { ok: false, reason: "walmart unavailable", gtin }; }
    else {
      const d = JSON.parse(r.body);
      const items = (d.items || []).filter(walmartSold);
      if (!items.length) payload = { ok: false, reason: (d.items || []).length ? "not sold by walmart" : "not found", gtin };
      else {
        const it = items[0];
        payload = {
          ok: true, gtin, itemId: it.itemId, upc: it.upc || null, name: it.name || null, brand: it.brandName || null, size: it.size || null,
          price: it.salePrice, offer: it.offerType || null, stock: it.stock || null, online: it.availableOnline ?? null,
          storeId: store, priceSource: store ? "store" : "online",
          // every Walmart-sold listing for the barcode, so the app can compare with the listing it is showing
          listings: items.map((l) => ({ itemId: l.itemId, price: l.salePrice, name: l.name || null, size: l.size || null, stock: l.stock || null })),
          checkedAt: new Date().toISOString(),
        };
      }
    }
  } catch (e) {
    status = 503; ttl = THROTTLE_TTL_SECONDS; payload = { ok: false, reason: "walmart unavailable", gtin };
  }
  const res = pub(payload, status, status === 503 ? { "retry-after": "30" } : {});
  if (status === 200 || status === 503) {
    // positive answers are kept for 6 hours; a throttled/failed Walmart call for 1 minute, so a throttled key is not hammered
    const toCache = new Response(JSON.stringify(payload), { status, headers: { "content-type": "application/json", "cache-control": `public, max-age=${ttl}`, ...(status === 503 ? { "retry-after": "30" } : {}) } });
    ctx.waitUntil(cache.put(cacheKey, toCache));
    res.headers.set("x-cache", "miss");
  }
  return res;
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);

    // Public, token-free, rate-limited route used by the offline app's live check.
    const mp = url.pathname.match(/^\/v1\/price\/([0-9]{8,14})$/);
    if (mp) return livePrice(req, env, ctx, mp[1]);

    if (!env.ADMIN_TOKEN || url.searchParams.get("token") !== env.ADMIN_TOKEN) {
      return json({ error: "unauthorized" }, 401);
    }

    if (url.pathname === "/health") {
      return json({
        WM_PRIVATE_KEY: Boolean(env.WM_PRIVATE_KEY),
        WM_CONSUMER_ID: Boolean(env.WM_CONSUMER_ID),
        WM_KEY_VERSION: env.WM_KEY_VERSION || null,
        PRICE_LIMITER: Boolean(env.PRICE_LIMITER),
        PRICE_GLOBAL_LIMITER: Boolean(env.PRICE_GLOBAL_LIMITER),
      });
    }

    if (url.pathname === "/taxonomy") {
      try {
        const { status, body } = await walmartGet(env, "/taxonomy");
        let parsed;
        try { parsed = JSON.parse(body); } catch { parsed = body.slice(0, 2000); }
        if (status !== 200) return json({ walmart_status: status, response: parsed }, 502);
        const top = (parsed.categories || []).map(c => ({ id: c.id, name: c.name, children: (c.children || []).length }));
        return json({ walmart_status: status, top_level_count: top.length, top_level: top });
      } catch (e) {
        return json({ error: String(e) }, 500);
      }
    }

    // /taxonomy/<id> — children of one category node (for mapping our 23 categories)
    const m = url.pathname.match(/^\/taxonomy\/([\w-]+)$/);
    if (m) {
      try {
        const { status, body } = await walmartGet(env, "/taxonomy");
        if (status !== 200) return json({ walmart_status: status, response: body.slice(0, 2000) }, 502);
        const find = (nodes) => {
          for (const n of nodes || []) {
            if (String(n.id) === m[1]) return n;
            const hit = find(n.children);
            if (hit) return hit;
          }
          return null;
        };
        const node = find(JSON.parse(body).categories);
        if (!node) return json({ error: `category ${m[1]} not found` }, 404);
        const kids = (node.children || []).map(c => ({ id: c.id, name: c.name, children: (c.children || []).length }));
        return json({ id: node.id, name: node.name, path: node.path || null, child_count: kids.length, children: kids });
      } catch (e) {
        return json({ error: String(e) }, 500);
      }
    }

    // /items/<categoryId>?pages=N — test pull of the product catalog for one category.
    // Reports field names, price coverage, seller mix, and paging behaviour. Read-only.
    const mi = url.pathname.match(/^\/items\/([\w-]+)$/);
    if (mi) {
      const pages = Math.min(Math.max(parseInt(url.searchParams.get("pages") || "1", 10) || 1, 1), 10);
      // Optional catalog filters to test (passed through only if present).
      const extra = ["soldByWmt", "available", "brand", "specialOffer"]
        .filter(k => url.searchParams.has(k))
        .map(k => `&${k}=${encodeURIComponent(url.searchParams.get(k))}`).join("");
      const delay = Math.min(parseInt(url.searchParams.get("delay") || "0", 10) || 0, 5000);
      let next = `/paginated/items?category=${encodeURIComponent(mi[1])}${extra}`;
      const all = [], pageLog = [];
      let firstRaw = null, meta = null;
      for (let i = 0; i < pages && next; i++) {
        if (i > 0 && delay) await new Promise(r => setTimeout(r, delay));
        const t0 = Date.now();
        const { status, body } = await walmartGet(env, next);
        if (status !== 200) { pageLog.push({ page: i + 1, status, error: body.slice(0, 500) }); break; }
        const d = JSON.parse(body);
        if (!meta) meta = { totalPages: d.totalPages ?? null, category: d.category ?? null, keys: Object.keys(d) };
        const items = d.items || [];
        if (!firstRaw && items[0]) firstRaw = items[0];
        all.push(...items);
        pageLog.push({ page: i + 1, status, items: items.length, ms: Date.now() - t0 });
        next = d.nextPage || null;
      }
      const priced = all.filter(x => typeof x.salePrice === "number").length;
      const sellers = {};
      for (const x of all) { const k = x.sellerInfo || "(none)"; sellers[k] = (sellers[k] || 0) + 1; }
      return json({
        category: mi[1], meta, pages: pageLog, has_more: Boolean(next),
        items_returned: all.length, with_salePrice: priced,
        with_msrp: all.filter(x => typeof x.msrp === "number").length,
        with_upc: all.filter(x => x.upc).length,
        with_size: all.filter(x => x.size).length,
        marketplace_true: all.filter(x => x.marketplace === true).length,
        marketplace_false: all.filter(x => x.marketplace === false).length,
        deleted_upc: all.filter(x => String(x.upc || "").startsWith("deleted_")).length,
        available_online: all.filter(x => x.availableOnline === true).length,
        filters_sent: extra || null, delay_ms: delay,
        sellers,
        item_fields: firstRaw ? Object.keys(firstRaw) : [],
        sample: all.slice(0, 15).map(summarizeItem),
        first_item_raw: url.searchParams.get("raw") ? firstRaw : undefined,
      });
    }

    // /search?q=...&category=<id> — coverage spot-check for a specific product.
    if (url.pathname === "/search") {
      const q = url.searchParams.get("q");
      if (!q) return json({ error: "missing q" }, 400);
      const cat = url.searchParams.get("category");
      const path = `/search?query=${encodeURIComponent(q)}&numItems=25` + (cat ? `&categoryId=${encodeURIComponent(cat)}` : "");
      const { status, body } = await walmartGet(env, path);
      if (status !== 200) return json({ walmart_status: status, response: body.slice(0, 1000) }, 502);
      const d = JSON.parse(body);
      return json({ query: q, totalResults: d.totalResults ?? null, items: (d.items || []).map(summarizeItem) });
    }

    return json({ error: "not found", routes: ["/health", "/taxonomy", "/taxonomy/<id>", "/items/<id>?pages=N", "/search?q=", "public: /v1/price/<gtin>"] }, 404);
  },
};
