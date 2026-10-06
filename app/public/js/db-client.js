// db-client.js — main-thread side of the database: install, cache, update, and query the worker.
//
// Storage model
//   Cache Storage bucket `sfb-db-<version>` holds the pack files exactly as served (gzip). The worker reads
//   them from there (falling back to the network on first install). `localStorage["sfb.db"]` records the
//   installed version. New versions download into their own bucket, then we switch and delete the old one.
//
// Events (EventTarget): "state" {state, ...}, "progress" {done,total,file}, "ready" {stats}, "update-available" {version}

const KEY = "sfb.db";
const DB_ROOT = "./db/";
const CACHE_PREFIX = "sfb-db-";

export class DbClient extends EventTarget {
  constructor() {
    super();
    this.worker = new Worker("./js/db-worker.js", { type: "module" });
    this.worker.onmessage = (e) => this.#onMessage(e.data);
    this.worker.onerror = (e) => this.#emit("state", { state: "error", message: e.message });
    this.pending = new Map();
    this.seq = 0;
    this.state = "idle";
    this.installed = this.#readInstalled();
    this.manifest = null;
    this.stats = null;
    this.pendingUpdate = null;
    this.ready = new Promise((r) => (this.#resolveReady = r));
  }
  #resolveReady = null;

  #readInstalled() { try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch { return null; } }
  #writeInstalled(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch { /* storage may be blocked */ } }
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

  /** Boot: load what is installed (instantly, offline), then look for a newer snapshot when online. */
  async start() {
    if (this.installed?.version) {
      try {
        await this.#load(this.installed.version);
      } catch (err) {
        console.warn("installed pack failed to load, reinstalling", err);
        this.installed = null;
        this.#writeInstalled(null);
      }
    }
    if (!this.installed) {
      if (!navigator.onLine) { this.#setState("offline-empty"); window.addEventListener("online", () => this.start(), { once: true }); return; }
      try {
        const cur = await this.#fetchCurrent();
        await this.#download(cur.version);
        this.#writeInstalled({ version: cur.version, installedAt: Date.now() });
        this.installed = this.#readInstalled();
        await this.#load(cur.version);
      } catch (err) {
        this.#setState("error", { message: String(err.message || err) });
        return;
      }
    } else {
      this.checkForUpdate().catch(() => {});
    }
  }

  async #fetchCurrent() {
    const res = await fetch(DB_ROOT + "current.json", { cache: "no-store" });
    if (!res.ok) throw new Error("could not read db/current.json");
    return res.json();
  }

  async #fetchManifest(version) {
    const url = `${DB_ROOT}${version}/manifest.json`;
    const cache = await caches.open(CACHE_PREFIX + version);
    let res = await cache.match(url);
    if (!res) { res = await fetch(url, { cache: "no-store" }); if (!res.ok) throw new Error("manifest missing"); await cache.put(url, res.clone()); }
    return res.json();
  }

  /** Download every pack file for a version into its cache bucket, with progress. */
  async #download(version) {
    this.#setState("downloading", { version });
    const manifest = await this.#fetchManifest(version);
    const cache = await caches.open(CACHE_PREFIX + version);
    const files = [manifest.files.cols, ...manifest.files.strings, manifest.files.upc, manifest.files.tokens, manifest.files.equiv, manifest.files.plu];
    const totalBytes = files.reduce((a, f) => a + (f.gzBytes || f.bytes || 0), 0);
    let doneBytes = 0;
    try { await navigator.storage?.persist?.(); } catch { /* optional */ }
    // two at a time: fast enough on Wi-Fi, gentle on a phone's memory
    const queue = files.slice();
    const runOne = async () => {
      while (queue.length) {
        const f = queue.shift();
        const url = `${DB_ROOT}${version}/${f.path}`;
        if (await cache.match(url)) { doneBytes += f.gzBytes || 0; this.#emit("progress", { phase: "download", doneBytes, totalBytes, file: f.path }); continue; }
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) throw new Error(`download failed: ${f.path} (${res.status})`);
        const buf = await res.arrayBuffer();
        await cache.put(url, new Response(buf, { headers: { "content-type": res.headers.get("content-type") || "application/octet-stream" } }));
        doneBytes += f.gzBytes || buf.byteLength;
        this.#emit("progress", { phase: "download", doneBytes, totalBytes, file: f.path });
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
    this.#cleanup(version).catch(() => {});
  }

  /** Look for a newer snapshot; download it in the background; apply when the app is idle (or on request). */
  async checkForUpdate({ apply = false } = {}) {
    if (!navigator.onLine) return { offline: true };
    const cur = await this.#fetchCurrent();
    if (cur.version === this.version) return { upToDate: true };
    if (this.pendingUpdate?.version === cur.version) return { pending: true, version: cur.version };
    const manifest = await this.#download(cur.version);
    this.pendingUpdate = { version: cur.version, manifest };
    this.#setState("ready", { version: this.version, manifest: this.manifest, stats: this.stats });
    this.#emit("update-available", { version: cur.version, manifest });
    if (apply) await this.applyUpdate();
    return { downloaded: true, version: cur.version };
  }

  async applyUpdate() {
    const u = this.pendingUpdate;
    if (!u) return false;
    this.pendingUpdate = null;
    await this.call({ type: "unload" });
    this.#writeInstalled({ version: u.version, installedAt: Date.now() });
    this.installed = this.#readInstalled();
    await this.#load(u.version);
    return true;
  }

  async #cleanup(keep) {
    const names = await caches.keys();
    for (const n of names) if (n.startsWith(CACHE_PREFIX) && n !== CACHE_PREFIX + keep && n !== CACHE_PREFIX + (this.pendingUpdate?.version || "")) await caches.delete(n);
  }

  async storageEstimate() { try { return await navigator.storage.estimate(); } catch { return null; } }

  // ---- queries
  search(q, limit = 40) { return this.call({ type: "search", q, limit }); }
  lookupUpc(key) { return this.call({ type: "upc", key }); }
  lookupPlu(code) { return this.call({ type: "plu", code }); }
  item(rank) { return this.call({ type: "item", rank }); }

  /** Wipe everything (settings → reset). */
  async reset() {
    await this.call({ type: "unload" }).catch(() => {});
    for (const n of await caches.keys()) if (n.startsWith(CACHE_PREFIX)) await caches.delete(n);
    this.#writeInstalled(null);
    this.installed = null; this.version = null; this.manifest = null; this.stats = null;
  }
}
