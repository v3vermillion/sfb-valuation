// The pipeline Worker's public live-price route, exercised with a stubbed Walmart API and stubbed bindings.
import { test } from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync } from "node:crypto";

const pem = `-----BEGIN PRIVATE KEY-----\n${Buffer.from(generateKeyPairSync("rsa", { modulusLength: 2048 }).privateKey.export({ type: "pkcs8", format: "der" })).toString("base64")}\n-----END PRIVATE KEY-----`;

function harness({ walmart, limits = { per: Infinity, all: Infinity }, bindings = true } = {}) {
  const store = new Map();
  globalThis.caches = { default: { async match(k) { const r = store.get(k.url); return r ? r.clone() : undefined; }, async put(k, r) { store.set(k.url, r); } } };
  const calls = [];
  globalThis.fetch = async (url) => { calls.push(url); return walmart(url); };
  let per = 0, all = 0;
  const env = {
    WM_PRIVATE_KEY: pem, WM_CONSUMER_ID: "cid", ADMIN_TOKEN: "secret",
    ...(bindings ? { PRICE_LIMITER: { async limit() { return { success: ++per <= limits.per }; } }, PRICE_GLOBAL_LIMITER: { async limit() { return { success: ++all <= limits.all }; } } } : {}),
  };
  const ctx = { waitUntil: (p) => p };
  return {
    calls, counts: () => ({ per, all }),
    async hit(path, method = "GET") {
      const mod = await import("../../pipeline/src/index.js");
      const r = await mod.default.fetch(new Request("https://w.example" + path, { method }), env, ctx);
      return { status: r.status, cors: r.headers.get("access-control-allow-origin"), cache: r.headers.get("x-cache"), cc: r.headers.get("cache-control"), retry: r.headers.get("retry-after"), body: r.status === 204 ? null : await r.json() };
    },
  };
}
const ok = (items) => new Response(JSON.stringify({ items }), { status: 200 });
const corn = { itemId: 1, upc: "078742054261", name: "Great Value Corn", brandName: "Great Value", salePrice: 0.87, marketplace: false, sellerInfo: "Walmart.com", stock: "Available" };

test("a Walmart-sold item is returned with every listing, cached, and never cached by the phone", async () => {
  const h = harness({ walmart: (u) => (u.includes("upc=078742054261") ? ok([{ ...corn, marketplace: true, sellerInfo: "Other" }, corn, { ...corn, itemId: 2, salePrice: 9.96, name: "Great Value Corn 12-pack" }]) : new Response("{}", { status: 404 })) });
  const a = await h.hit("/v1/price/078742054261");
  assert.equal(a.status, 200); assert.equal(a.body.ok, true); assert.equal(a.body.itemId, 1); assert.equal(a.body.price, 0.87);
  assert.deepEqual(a.body.listings.map((l) => l.itemId), [1, 2]);
  assert.equal(a.cors, "*"); assert.equal(a.cache, "miss"); assert.equal(a.cc, "no-store");
  const b = await h.hit("/v1/price/078742054261");
  assert.equal(b.cache, "hit"); assert.equal(b.cc, "no-store"); assert.equal(b.body.itemId, 1);
  assert.equal(h.calls.length, 1, "one Walmart call for two requests");
  assert.deepEqual(h.counts(), { per: 1, all: 1 }, "limits charged only on the Walmart call");
  assert.match(h.calls[0], /\/items\?upc=078742054261$/);
});

test("marketplace-only, not found, throttled and failed upstreams are distinguishable", async () => {
  const h = harness({ walmart: (u) => u.includes("012345678905") ? ok([{ itemId: 2, salePrice: 5, marketplace: true, sellerInfo: "Some Seller" }]) : u.includes("036000291452") ? new Response("", { status: 429 }) : u.includes("5000112637922") ? new Response("", { status: 500 }) : new Response("{}", { status: 404 }) });
  assert.deepEqual((await h.hit("/v1/price/012345678905")).body, { ok: false, reason: "not sold by walmart", gtin: "00012345678905" });
  const t = await h.hit("/v1/price/036000291452");
  assert.equal(t.status, 503); assert.equal(t.body.reason, "walmart unavailable"); assert.equal(t.retry, "30");
  const t2 = await h.hit("/v1/price/036000291452");
  assert.equal(t2.cache, "hit", "a throttled answer is remembered briefly so the key is not hammered");
  assert.equal((await h.hit("/v1/price/5000112637922")).status, 503);
  assert.match(h.calls.find((c) => c.includes("5000112637922")), /items\?gtin=05000112637922$/, "EAN-13 goes through the 14-digit gtin parameter");
  assert.equal((await h.hit("/v1/price/096385074")).status, 400);   // not a valid code
});

test("rate limits, validation, CORS preflight and the admin gate", async () => {
  const h = harness({ walmart: () => ok([corn]), limits: { per: 2, all: Infinity } });
  assert.equal((await h.hit("/v1/price/078742054261")).status, 200);
  assert.equal((await h.hit("/v1/price/5000112637922")).status, 200);
  const lim = await h.hit("/v1/price/036000291452");
  assert.equal(lim.status, 429); assert.equal(lim.retry, "60");
  assert.equal((await h.hit("/v1/price/078742054261")).cache, "hit", "cached barcodes still answer while limited");
  assert.equal((await h.hit("/v1/price/078742054262")).status, 400);   // bad check digit
  assert.equal((await h.hit("/v1/price/201234928759")).status, 400);   // store label is not a catalog item
  assert.equal((await h.hit("/v1/price/078742054261", "OPTIONS")).status, 204);
  assert.equal((await h.hit("/health")).status, 401);
  const g = harness({ walmart: () => ok([corn]), limits: { per: Infinity, all: 1 } });
  assert.equal((await g.hit("/v1/price/078742054261")).status, 200);
  assert.equal((await g.hit("/v1/price/5000112637922")).status, 429, "the aggregate cap protects the shared key");
});

test("without the rate-limit bindings the route fails closed", async () => {
  const h = harness({ walmart: () => ok([corn]), bindings: false });
  const r = await h.hit("/v1/price/078742054261");
  assert.equal(r.status, 503); assert.equal(r.body.reason, "not configured");
  assert.equal(h.calls.length, 0);
});
