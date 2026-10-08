// db-client.js — main-thread side of the database: install, cache, update, and query the worker.
//
// Storage model
//   Cache Storage bucket `sfb-db-<version>` holds the pack files exactly as served (gzip). The worker reads
//   them from there (falling back to the network on first install). localStorage["sfb.db"] records the
//   installed version and localStorage["sfb.db.pending"] a fully downloaded newer one; when localStorage is
//   unavailable the buckets themselves are the source of truth. New versions download into their own bucket
//   while the current one keeps answering; the swap happens when the app is idle and is rolled back if the
//   new pack fails to open.
//
// Events (EventTarget): "state" {state, ...}, "progress" {phase, ...}, "ready" {stats}, "update-available" {version}

const KEY = "sfb.db";
const PENDING_KEY = "sfb.db.pending";
const PERSIST_KEY = "sfb.persist";       // when persistent storage was last requested
const PERSIST_RETRY_MS = 86_400_000;     // ask again at most once a day until it is granted
const DB_ROOT = "./db/";
const CACHE_PREFIX = "sfb-db-";

const FILES = (manifest) => [manifest.files.cols, ...manifest.files.strings, manifest.files.upc, manifest.files.tokens, manifest.files.equiv, manifest.files.plu];

export class DbClient extends EventTarget {
  constructor() {
    super();
    this.worker = new Worker("./js/db-worker.js", { type: "module" });
    this.worker.onmessage = (e) => this.#onMessage(e.data);
    this.worker.onerror = (e) => this.#emit("state", { state: "error", message: e.message });
    this.pending = new Map();
    this.seq = 0;
    this.state = "idle";
    this.version = null;
    this.manifest = null;
    this.stats = null;
    this.pendingUpdate = null;
    this.persisted = undefined;   // true | false | null (the browser cannot say) | undefined (not asked yet)
    this.ready = new Promise((r) => (this.#resolveReady = r));
  }
  #resolveReady = null;
  #downloads = new Map();     // version -> in-flight download promise
  #updating = null;           // in-flight checkForUpdate

  #readKey(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch { return null; } }
  #writeKey(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage may be blocked */ } }
  #emit(type, detail) { this.dispatchEvent(new CustomEvent(type, { detail })); }
  #setState(state, extra = {}) { this.state = state; this.#emit("state", { state, ...extra }); }

  #onMessage(m) {
    if (m.type === "progress") { this.#emit("progress", { done: m.done, total: m.total, file: m.file, phase: "load" }); return; }
    const p = this.pending.get(m.id);
    if (!p) return;
    this.pending.delete(m.id);
    if (m.type === "error") p.reject(new Error(m.error));
    else p.resolve(m.type === "ready" ? m.stats : m.result);
  }
  call(msg, transfer) {
    return new Promise((resolve, reject) => {
      const id = ++this.seq;
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ ...msg, id }, transfer || []);
    });
  }

  /** Versions that have a complete bucket on this device (newest first), for when localStorage is gone. */
  async #cachedVersions() {
    const out = [];
    try {
      for (const n of await caches.keys()) {
        if (!n.startsWith(CACHE_PREFIX)) continue;
        const v = n.slice(CACHE_PREFIX.length);
        if (await this.#bucketComplete(v)) out.push(v);
      }
    } catch { /* no Cache Storage */ }
    return out.sort().reverse();
  }
  async #bucketComplete(version) {
    try {
      const cache = await caches.open(CACHE_PREFIX + version);
      const m = await cache.match(`${DB_ROOT}${version}/manifest.json`);
      if (!m) return false;
      const manifest = await m.json();
      for (const f of FILES(manifest)) if (!(await cache.match(`${DB_ROOT}${version}/${f.path}`))) return false;
      return true;
    } catch { return false; }
  }

  /** Boot: load what is installed (instantly, offline), then look for a newer snapshot when online. */
  async start() {
    if (this.#updating) return this.#updating;
    const run = (async () => {
      let installed = this.#readKey(KEY)?.version || null;
      const pending = this.#readKey(PENDING_KEY)?.version || null;
      if (!installed) { const cached = await this.#cachedVersions(); if (cached.length) installed = cached[0]; }
      // a fully downloaded newer snapshot waits for an idle moment: boot is one
      if (pending && pending !== installed && (await this.#bucketComplete(pending))) {
        try { await this.#load(pending); this.#writeKey(KEY, { version: pending, installedAt: Date.now() }); this.#writeKey(PENDING_KEY, null); installed = pending; }
        catch (err) { console.warn("pending pack failed to open, keeping the installed one", err); this.#writeKey(PENDING_KEY, null); await caches.delete(CACHE_PREFIX + pending).catch(() => {}); }
      }
      if (installed && !this.version) {
        try { await this.#load(installed); this.#writeKey(KEY, { version: installed, installedAt: Date.now() }); }
        catch (err) {
          console.warn("installed pack failed to load, reinstalling", err);
          await caches.delete(CACHE_PREFIX + installed).catch(() => {});
          this.#writeKey(KEY, null);
          installed = null;
        }
      }
      if (!this.version) {
        if (!navigator.onLine) { this.#setState("offline-empty"); return; }
        try {
          const cur = await this.#fetchCurrent();
          await this.#download(cur.version, { background: false });
          await this.#load(cur.version);
          this.#writeKey(KEY, { version: cur.version, installedAt: Date.now() });
        } catch (err) {
          this.#setState("error", { message: String(err.message || err) });
        }
        return;
      }
    })();
    // the launch check runs once start() has released #updating; called inside run it would only see itself as busy
    this.#updating = run.finally(() => {
      this.#updating = null;
      if (this.version) this.checkForUpdate().catch(() => {});
    });
    return this.#updating;
  }

  async #fetchCurrent() {
    const res = await fetch(DB_ROOT + "current.json", { cache: "no-store" });
    if (!res.ok) throw new Error("could not read db/current.json");
    const cur = await res.json();
    if (!cur?.version || !/^[\w.-]+$/.test(cur.version)) throw new Error("db/current.json is not a snapshot pointer");
    return cur;
  }

  async #fetchManifest(version) {
    const url = `${DB_ROOT}${version}/manifest.json`;
    const cache = await caches.open(CACHE_PREFIX + version);
    let res = await cache.match(url);
    if (!res) {
      res = await fetch(url, { cache: "no-store" });
      if (!res.ok || /text\/html/i.test(res.headers.get("content-type") || "")) throw new Error("manifest missing");
      await cache.put(url, res.clone());
    }
    return res.json();
  }

  /** Download every pack file for a version into its cache bucket, with progress. Deduplicated per version. */
  #download(version, { background }) {
    let p = this.#downloads.get(version);
    if (!p) {
      p = this.#downloadNow(version, background).finally(() => this.#downloads.delete(version));
      this.#downloads.set(version, p);
    }
    return p;
  }
  async #downloadNow(version, background) {
    if (!background) this.#setState("downloading", { version });
    const manifest = await this.#fetchManifest(version);
    const cache = await caches.open(CACHE_PREFIX + version);
    const files = FILES(manifest);
    const totalBytes = files.reduce((a, f) => a + (f.gzBytes || f.bytes || 0), 0);
    let doneBytes = 0;
    // two at a time: fast enough on Wi-Fi, gentle on a phone's memory
    const queue = files.slice();
    const runOne = async () => {
      while (queue.length) {
        const f = queue.shift();
        const url = `${DB_ROOT}${version}/${f.path}`;
        if (await cache.match(url)) { doneBytes += f.gzBytes || 0; this.#emit("progress", { phase: "download", background, version, doneBytes, totalBytes, file: f.path }); continue; }
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) throw new Error(`download failed: ${f.path} (${res.status})`);
        const ct = res.headers.get("content-type") || "";
        if (/text\/html/i.test(ct)) throw new Error(`download failed: ${f.path} (not a pack file)`);
        const buf = await res.arrayBuffer();
        await cache.put(url, new Response(buf, { headers: { "content-type": ct || "application/octet-stream" } }));
        doneBytes += f.gzBytes || buf.byteLength;
        this.#emit("progress", { phase: "download", background, version, doneBytes, totalBytes, file: f.path });
      }
    };
    await Promise.all([runOne(), runOne()]);
    return manifest;
  }

  async #load(version) {
    this.#setState("loading", { version });
    const manifest = await this.#fetchManifest(version);
    const t0 = performance.now();
    const stats = await this.call({ type: "load", base: new URL(`${DB_ROOT}${version}/`, location.href).href, manifest, cacheName: CACHE_PREFIX + version });
    this.manifest = manifest;
    this.stats = { ...stats, wallMs: Math.round(performance.now() - t0) };
    this.version = version;
    this.#setState("ready", { version, manifest, stats: this.stats });
    this.#emit("ready", { stats: this.stats, manifest });
    this.#resolveReady?.(true);
    this.#cleanup().catch(() => {});
    this.requestPersistence().catch(() => {});
  }

  /**
   * Look for a newer snapshot and download it in the background while the current one keeps answering.
   * Returns {upToDate} | {downloaded, version} | {pending, version} | {applied, version} | {offline} | {notReady}.
   */
  checkForUpdate(opts = {}) {
    if (this.#updating) return this.#updating.then(() => ({ busy: true }));
    const run = this.#checkForUpdate(opts);
    this.#updating = run.finally(() => { this.#updating = null; });
    return this.#updating;
  }
  async #checkForUpdate({ apply = false } = {}) {
    if (!navigator.onLine) return { offline: true };
    if (!this.version) {
      // nothing installed yet: a first install is start()'s job, never two parallel downloads
      if (this.state === "offline-empty" || this.state === "error" || this.state === "idle") { this.#updating = null; await this.start(); return { installed: !!this.version }; }
      return { notReady: true };
    }
    const cur = await this.#fetchCurrent();
    if (cur.version === this.version) { this.#writeKey(PENDING_KEY, null); return { upToDate: true }; }
    if (this.pendingUpdate?.version !== cur.version) {
      const manifest = await this.#download(cur.version, { background: true });
      this.pendingUpdate = { version: cur.version, manifest };
      this.#writeKey(PENDING_KEY, { version: cur.version, at: Date.now() });
      this.#emit("update-available", { version: cur.version, manifest });
    }
    if (apply) { await this.applyUpdate(); return { applied: true, version: cur.version }; }
    return { pending: true, version: cur.version };
  }

  /** Swap to the downloaded snapshot. The old pack is restored if the new one fails to open. */
  async applyUpdate() {
    const u = this.pendingUpdate;
    if (!u) return false;
    const prev = this.version;
    this.pendingUpdate = null;
    await this.call({ type: "unload" });
    try {
      await this.#load(u.version);
      this.#writeKey(KEY, { version: u.version, installedAt: Date.now() });
      this.#writeKey(PENDING_KEY, null);
      return true;
    } catch (err) {
      console.warn("new pack failed to open, restoring the previous one", err);
      this.#writeKey(PENDING_KEY, null);
      await caches.delete(CACHE_PREFIX + u.version).catch(() => {});
      if (prev) await this.#load(prev);
      throw err;
    }
  }

  async #cleanup() {
    const keep = new Set([this.version, this.pendingUpdate?.version, this.#readKey(PENDING_KEY)?.version, ...this.#downloads.keys()].filter(Boolean));
    for (const n of await caches.keys()) if (n.startsWith(CACHE_PREFIX) && !keep.has(n.slice(CACHE_PREFIX.length))) await caches.delete(n);
  }

  async storageEstimate() { try { return await navigator.storage.estimate(); } catch { return null; } }

  /** true when the browser has promised not to evict the pack, false when storage is best-effort, null when it cannot say. */
  async persistenceStatus() {
    try {
      if (!navigator.storage?.persisted) return null;
      this.persisted = !!(await navigator.storage.persisted());
      return this.persisted;
    } catch { return null; }
  }

  /**
   * Ask the browser to keep the pack through storage pressure. Chrome decides silently (installed app, bookmark or
   * enough engagement), Safari grants it to Home Screen apps, Firefox asks the user: cheap to repeat, so it is asked
   * after every successful load, but at most once a day unless `force` (the app was just installed, which changes
   * the answer). Resolves to the same values as persistenceStatus(); never throws.
   */
  async requestPersistence({ force = false } = {}) {
    const s = navigator.storage;
    if (!s?.persist) { this.persisted = null; return null; }
    try {
      if (s.persisted && (await s.persisted())) { this.persisted = true; return true; }
      const askedAt = Number(this.#readKey(PERSIST_KEY)?.askedAt) || 0;
      if (!force && Date.now() - askedAt < PERSIST_RETRY_MS) { this.persisted = false; return false; }
      this.#writeKey(PERSIST_KEY, { askedAt: Date.now() });
      this.persisted = !!(await s.persist());
      return this.persisted;
    } catch { return null; }
  }

  // ---- queries
  search(q, limit = 40) { return this.call({ type: "search", q, limit }); }
  lookupUpc(key) { return this.call({ type: "upc", key }); }
  lookupPlu(code) { return this.call({ type: "plu", code }); }
  item(rank) { return this.call({ type: "item", rank }); }

  /** Remove every downloaded pack and the markers (settings → reset). The app shell is left alone. */
  async reset() {
    await this.call({ type: "unload" }).catch(() => {});
    for (const n of await caches.keys()) if (n.startsWith(CACHE_PREFIX)) await caches.delete(n);
    this.#writeKey(KEY, null); this.#writeKey(PENDING_KEY, null);
    this.version = null; this.manifest = null; this.stats = null; this.pendingUpdate = null;
  }
}
