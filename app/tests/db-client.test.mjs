// db-client.js runs in a page; here only the storage-persistence policy is exercised, with the browser globals stubbed.
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

const DAY = 86_400_000;
const store = new Map();
globalThis.Worker = class { postMessage() {} terminate() {} };
globalThis.localStorage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };
const nav = { onLine: true, storage: null };
Object.defineProperty(globalThis, "navigator", { configurable: true, value: nav });

const { DbClient } = await import("../public/js/db-client.js");

let calls, persistedNow, persistResult;
beforeEach(() => {
  store.clear();
  calls = []; persistedNow = false; persistResult = true;
  nav.storage = {
    persisted: async () => { calls.push("persisted"); return persistedNow; },
    persist: async () => { calls.push("persist"); return persistResult; },
  };
});
const askedAt = () => JSON.parse(store.get("sfb.persist") || "null")?.askedAt;

test("requestPersistence asks the browser the first time and remembers when it asked", async () => {
  const db = new DbClient();
  assert.equal(db.persisted, undefined);
  assert.equal(await db.requestPersistence(), true);
  assert.deepEqual(calls, ["persisted", "persist"]);
  assert.equal(db.persisted, true);
  assert.ok(Date.now() - askedAt() < 5000);
});

test("requestPersistence records a refusal and does not nag again the same day", async () => {
  const db = new DbClient();
  persistResult = false;
  assert.equal(await db.requestPersistence(), false);
  assert.equal(db.persisted, false);
  calls = [];
  assert.equal(await db.requestPersistence(), false);
  assert.deepEqual(calls, ["persisted"]);                        // checked, not asked
});

test("requestPersistence asks again after a day, and at once when forced (the app was just installed)", async () => {
  const db = new DbClient();
  store.set("sfb.persist", JSON.stringify({ askedAt: Date.now() - DAY - 1000 }));
  assert.equal(await db.requestPersistence(), true);
  assert.deepEqual(calls, ["persisted", "persist"]);
  calls = []; persistedNow = false; persistResult = true;
  store.set("sfb.persist", JSON.stringify({ askedAt: Date.now() - 60_000 }));
  assert.equal(await db.requestPersistence({ force: true }), true);
  assert.deepEqual(calls, ["persisted", "persist"]);
});

test("requestPersistence never re-asks once the browser has granted persistence", async () => {
  const db = new DbClient();
  persistedNow = true;
  assert.equal(await db.requestPersistence({ force: true }), true);
  assert.deepEqual(calls, ["persisted"]);
  assert.equal(askedAt(), undefined);
});

test("requestPersistence copes with a browser that has no storage API or a throwing one", async () => {
  const db = new DbClient();
  nav.storage = undefined;
  assert.equal(await db.requestPersistence(), null);
  assert.equal(db.persisted, null);
  nav.storage = { persist: async () => { throw new Error("blocked"); } };   // no persisted(), persist() throws
  assert.equal(await db.requestPersistence(), null);
});

test("persistenceStatus reports persistent / best-effort / unknown without asking for anything", async () => {
  const db = new DbClient();
  persistedNow = true;
  assert.equal(await db.persistenceStatus(), true);
  persistedNow = false;
  assert.equal(await db.persistenceStatus(), false);
  assert.equal(db.persisted, false);
  assert.deepEqual(calls, ["persisted", "persisted"]);
  nav.storage = {};
  assert.equal(await db.persistenceStatus(), null);
  nav.storage = { persisted: async () => { throw new Error("blocked"); } };
  assert.equal(await db.persistenceStatus(), null);
});

// ---- launch: an installed pack loads offline-first, then the launch looks for a newer snapshot (once)
const MANIFEST = { files: { cols: { path: "c.bin.gz" }, strings: [{ path: "s.bin.gz" }], upc: { path: "u.bin.gz" },
  tokens: { path: "t.bin.gz" }, equiv: { path: "e.bin.gz" }, plu: { path: "p.bin.gz" } } };
function stubBrowser({ live }) {
  const buckets = new Map();
  const fetched = [];
  const bucket = (n) => { if (!buckets.has(n)) buckets.set(n, new Map()); return buckets.get(n); };
  const response = (body, ct = "application/json") => ({ ok: true, status: 200, headers: { get: () => ct },
    json: async () => JSON.parse(body), arrayBuffer: async () => new TextEncoder().encode(body).buffer, clone() { return this; } });
  globalThis.caches = {
    keys: async () => [...buckets.keys()],
    delete: async (n) => buckets.delete(n),
    open: async (n) => { const b = bucket(n); return { match: async (u) => b.get(String(u)), put: async (u, r) => { b.set(String(u), r); } }; },
  };
  globalThis.fetch = async (url) => {
    url = String(url); fetched.push(url);
    if (url.endsWith("current.json")) return response(JSON.stringify({ version: live }));
    if (url.endsWith("manifest.json")) return response(JSON.stringify(MANIFEST));
    return response("pack", "application/octet-stream");
  };
  globalThis.location = { href: "https://app.test/" };
  globalThis.performance ??= { now: () => 0 };
  const install = (v) => {
    const b = bucket("sfb-db-" + v);
    b.set(`./db/${v}/manifest.json`, response(JSON.stringify(MANIFEST)));
    for (const f of FILES) b.set(`./db/${v}/${f}`, response("pack"));
  };
  return { buckets, fetched, install };
}
const FILES = ["c.bin.gz", "s.bin.gz", "u.bin.gz", "t.bin.gz", "e.bin.gz", "p.bin.gz"];
function fakeWorker(db) {   // answers every call as the worker would, asynchronously
  db.worker.postMessage = (m) => setTimeout(() => db.worker.onmessage({ data: m.type === "load" ? { id: m.id, type: "ready", stats: {} } : { id: m.id, type: "result", result: null } }));
}

test("start() loads the installed pack and then checks for a newer snapshot on every launch", async () => {
  const b = stubBrowser({ live: "v2" });
  b.install("v1");
  store.set("sfb.db", JSON.stringify({ version: "v1" }));
  const db = new DbClient(); fakeWorker(db);
  const seen = [];
  db.addEventListener("update-available", (e) => seen.push(e.detail.version));
  await db.start();
  assert.equal(db.version, "v1", "the installed pack answers at once");
  for (let i = 0; i < 50 && !seen.length; i++) await new Promise((r) => setTimeout(r, 5));
  assert.ok(b.fetched.some((u) => u.endsWith("current.json")), "the launch asked for db/current.json");
  assert.deepEqual(seen, ["v2"], "the newer snapshot was downloaded in the background");
  assert.equal(JSON.parse(store.get("sfb.db.pending")).version, "v2");
});

test("start() with the live snapshot already installed checks once and stays put", async () => {
  const b = stubBrowser({ live: "v1" });
  b.install("v1");
  store.set("sfb.db", JSON.stringify({ version: "v1" }));
  const db = new DbClient(); fakeWorker(db);
  await db.start();
  for (let i = 0; i < 20; i++) await new Promise((r) => setTimeout(r, 5));
  assert.equal(b.fetched.filter((u) => u.endsWith("current.json")).length, 1);
  assert.equal(db.version, "v1"); assert.equal(store.get("sfb.db.pending"), undefined);
});
