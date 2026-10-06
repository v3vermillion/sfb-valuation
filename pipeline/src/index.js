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
    salePrice: it.salePrice, msrp: it.msrp, offerType: it.offerType,
    sellerInfo: it.sellerInfo, availableOnline: it.availableOnline, stock: it.stock,
    categoryPath: it.categoryPath, categoryNode: it.categoryNode,
  };
}

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj, null, 2), { status, headers: { "content-type": "application/json" } });

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!env.ADMIN_TOKEN || url.searchParams.get("token") !== env.ADMIN_TOKEN) {
      return json({ error: "unauthorized" }, 401);
    }

    if (url.pathname === "/health") {
      return json({
        WM_PRIVATE_KEY: Boolean(env.WM_PRIVATE_KEY),
        WM_CONSUMER_ID: Boolean(env.WM_CONSUMER_ID),
        WM_KEY_VERSION: env.WM_KEY_VERSION || null,
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
      let next = `/paginated/items?category=${encodeURIComponent(mi[1])}`;
      const all = [], pageLog = [];
      let firstRaw = null, meta = null;
      for (let i = 0; i < pages && next; i++) {
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

    return json({ error: "not found", routes: ["/health", "/taxonomy", "/taxonomy/<id>", "/items/<id>?pages=N", "/search?q="] }, 404);
  },
};
