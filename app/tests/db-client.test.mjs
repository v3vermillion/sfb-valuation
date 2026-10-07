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
