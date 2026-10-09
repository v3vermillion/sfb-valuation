// db-client.js — main-thread side of the database: install, cache, update, and query the worker.
//
// Storage model
//   A format-3 pack is a manifest plus shard files named by their content (db/files/<sha>.bin.gz). The files live in one
//   Cache Storage bucket (`sfb-db-files`) shared by every version, so an update downloads only the files whose content
//   changed; each version's manifest and its small per-version files (equivalents, produce codes) live in
//   `sfb-db-<version>`. A format-2 pack keeps all its files in its version bucket. localStorage["sfb.db"] records the
//   installed version and localStorage["sfb.db.pending"] a fully downloaded newer one; without localStorage the buckets
//   are the source of truth.
//
// First install: the core shards (consumable departments) download first and the app opens on them; the other
//   departments follow in the background and join the search when they arrive ("more" in the state). A boot that finds
//   only the core on the phone (the first download was interrupted) opens it and resumes the rest when online.
// Updates download every file of the new version in the background while the current one keeps answering; the swap
//   happens when the app is idle and is rolled back if the new pack fails to open.
// Downloads retry each file with back-off, stop at the first file that keeps failing, and say why in words a volunteer
//   can act on; nothing half-downloaded is ever opened.
//
// Events (EventTarget): "state" {state, ...}, "progress" {phase, ...}, "ready" {stats}, "more" {loaded, pending},
// "update-available" {version}

const KEY = "sfb.db";
const PENDING_KEY = "sfb.db.pending";
const PERSIST_KEY = "sfb.persist";       // when persistent storage was last requested
const PERSIST_RETRY_MS = 86_400_000;     // ask again at most once a day until it is granted
const DB_ROOT = "./db/";
const CACHE_PREFIX = "sfb-db-";
const FILES_CACHE = "sfb-db-files";      // shard files of every format-3 version (not a version bucket)
const RETRIES = 3;                       // per file, before the download stops
const PARALLEL = 3;

/** Every file of a version: { url (relative to the page), bytes, shard, tier, bucket }, core first. */
export function fileList(manifest, version) {
  if (manifest.shards) {
    const out = [];
    for (const sh of manifest.shards) for (const f of [sh.files.cols, sh.files.upc, sh.files.tokens, ...sh.files.strings]) {
      out.push({ url: DB_ROOT + f.path, bytes: f.gzBytes || f.bytes || 0, shard: sh.id, tier: sh.tier || "core", bucket: FILES_CACHE });
    }
    for (const f of [manifest.files.equiv, manifest.files.plu]) out.push({ url: DB_ROOT + f.path, bytes: f.gzBytes || f.bytes || 0, shard: null, tier: "core", bucket: CACHE_PREFIX + version });
    return out.sort((a, b) => (a.tier === b.tier ? 0 : a.tier === "core" ? -1 : 1));
  }
  const f = manifest.files;
  return [f.cols, ...f.strings, f.upc, f.tokens, f.equiv, f.plu].map((x) => ({ url: `${DB_ROOT}${version}/${x.path}`, bytes: x.gzBytes || x.bytes || 0, shard: "all", tier: "core", bucket: CACHE_PREFIX + version }));
}
const shardIds = (manifest) => (manifest.shards ? manifest.shards.map((s) => s.id) : ["all"]);

/** A download that failed: `network` when the phone lost its connection (worth retrying), else the server's answer. */
class DownloadError extends Error {
  constructor(message, { network = false } = {}) { super(message); this.network = network; }
}

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
    this.more = null;             // { loaded: [shard ids], pending: [shard ids] } while other departments are still arriving
    this.persisted = undefined;   // true | false | null (the browser cannot say) | undefined (not asked yet)
    this.ready = new Promise((r) => (this.#resolveReady = r));
  }
  #resolveReady = null;
  #downloads = new Map();     // version + tier -> in-flight download promise
  #updating = null;           // in-flight start/checkForUpdate
  #moreTask = null;           // in-flight background completion of the current version

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

  // ---- what is on the phone
  async #manifestOf(version) {
    try {
      const cache = await caches.open(CACHE_PREFIX + version);
      const m = await cache.match(`${DB_ROOT}${version}/manifest.json`);
      return m ? await m.json() : null;
    } catch { return null; }
  }
  /** Shard ids whose every file is in Cache Storage, and whether the per-version files are there too. */
  async #present(version, manifest) {
    const have = new Set(), missing = new Set();
    let base = true;
    for (const f of fileList(manifest, version)) {
      let ok = false;
      try { ok = !!(await (await caches.open(f.bucket)).match(f.url)); } catch { ok = false; }
      if (f.shard == null) { if (!ok) base = false; } else if (ok) have.add(f.shard); else missing.add(f.shard);
    }
    for (const s of missing) have.delete(s);
    return { base, shards: [...have] };
  }
  /** The core shards of a version are all on the phone: it can open offline. */
  async #usable(version) {
    const manifest = await this.#manifestOf(version);
    if (!manifest) return null;
    const p = await this.#present(version, manifest);
    const core = (manifest.shards || [{ id: "all", tier: "core" }]).filter((s) => (s.tier || "core") === "core").map((s) => s.id);
    return p.base && core.every((id) => p.shards.includes(id)) ? { manifest, shards: p.shards, complete: p.shards.length === shardIds(manifest).length } : null;
  }
  /** Versions with a usable bucket on this device (newest first), for when localStorage is gone. */
  async #cachedVersions() {
    const out = [];
    try {
      for (const n of await caches.keys()) {
        if (!n.startsWith(CACHE_PREFIX) || n === FILES_CACHE) continue;
        const v = n.slice(CACHE_PREFIX.length);
        if (await this.#usable(v)) out.push(v);
      }
    } catch { /* no Cache Storage */ }
    return out.sort().reverse();
  }

  /** Boot: open what is installed (instantly, offline), then look for a newer snapshot when online. */
  async start() {
    if (this.#updating) return this.#updating;
    const run = (async () => {
      let installed = this.#readKey(KEY)?.version || null;
      const pending = this.#readKey(PENDING_KEY)?.version || null;
      if (!installed) { const cached = await this.#cachedVersions(); if (cached.length) installed = cached[0]; }
      // a fully downloaded newer snapshot waits for an idle moment: boot is one
      if (pending && pending !== installed && (await this.#usable(pending))?.complete) {
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
          await this.#download(cur.version, { background: false, tier: "core" });
          await this.#load(cur.version);
          this.#writeKey(KEY, { version: cur.version, installedAt: Date.now() });
        } catch (err) {
          this.#setState("error", { message: this.#explain(err), network: !!err.network });
        }
      }
    })();
    // the launch check runs once start() has released #updating; called inside run it would only see itself as busy
    this.#updating = run.finally(() => {
      this.#updating = null;
      if (this.version) { this.#completeMore().catch(() => {}); this.checkForUpdate().catch(() => {}); }
    });
    return this.#updating;
  }

  #explain(err) {
    if (err?.network || !navigator.onLine) return "The connection dropped while downloading prices. They will download again as soon as the phone is back online.";
    return String(err?.message || err);
  }

  async #fetchCurrent() {
    let res;
    try { res = await fetch(DB_ROOT + "current.json", { cache: "no-store" }); }
    catch (e) { throw new DownloadError(`could not reach the price server (${e.message})`, { network: true }); }
    if (!res.ok) throw new DownloadError("could not read db/current.json");
    const cur = await res.json();
    if (!cur?.version || !/^[\w.-]+$/.test(cur.version)) throw new DownloadError("db/current.json is not a snapshot pointer");
    return cur;
  }

  async #fetchManifest(version) {
    const url = `${DB_ROOT}${version}/manifest.json`;
    const cache = await caches.open(CACHE_PREFIX + version);
    let res = await cache.match(url);
    if (!res) {
      try { res = await fetch(url, { cache: "no-store" }); }
      catch (e) { throw new DownloadError(`could not reach the price server (${e.message})`, { network: true }); }
      if (!res.ok || /text\/html/i.test(res.headers.get("content-type") || "")) throw new DownloadError("manifest missing");
      await cache.put(url, res.clone());
    }
    return res.json();
  }

  /** Download the files of a version (tier "core", "more" or "all") that are not on the phone yet. Deduplicated. */
  #download(version, { background, tier = "all" }) {
    const k = `${version}:${tier}`;
    let p = this.#downloads.get(k);
    if (!p) {
      p = this.#downloadNow(version, background, tier).finally(() => this.#downloads.delete(k));
      this.#downloads.set(k, p);
    }
    return p;
  }
  async #downloadNow(version, background, tier) {
    if (!background) this.#setState("downloading", { version });
    const t0 = performance.now();
    const manifest = await this.#fetchManifest(version);
    const files = fileList(manifest, version).filter((f) => tier === "all" || f.tier === tier);
    const totalBytes = files.reduce((a, f) => a + f.bytes, 0);
    let doneBytes = 0, failed = null;
    const queue = files.slice();
    const progress = (f) => { if (!failed) this.#emit("progress", { phase: "download", background, tier, version, doneBytes, totalBytes, file: f.url }); };
    const fetchOne = async (f) => {
      const cache = await caches.open(f.bucket);
      if (await cache.match(f.url)) return;
      for (let attempt = 1; ; attempt++) {
        try {
          let res;
          try { res = await fetch(f.url, { cache: "no-store" }); }
          catch (e) { throw new DownloadError(`${f.url}: ${e.message}`, { network: true }); }
          if (!res.ok) throw new DownloadError(`download failed: ${f.url} (${res.status})`, { network: res.status >= 500 });
          if (/text\/html/i.test(res.headers.get("content-type") || "")) throw new DownloadError(`download failed: ${f.url} (not a pack file)`);
          // the response goes straight into Cache Storage: reading it into an ArrayBuffer first copied every pack file
          // through the page's JS heap twice on a phone
          await cache.put(f.url, res);
          return;
        } catch (e) {
          if (failed || attempt >= RETRIES || !e.network || !navigator.onLine) throw e;
          await new Promise((r) => setTimeout(r, 1000 * 2 ** attempt));    // 2 s, 4 s
        }
      }
    };
    const runOne = async () => {
      while (queue.length && !failed) {
        const f = queue.shift();
        try { await fetchOne(f); } catch (e) { failed = failed || e; break; }
        doneBytes += f.bytes;
        progress(f);
      }
    };
    await Promise.all(Array.from({ length: PARALLEL }, runOne));
    if (failed) throw failed;                  // the other downloads stopped too; late progress is never reported
    if (!background) this.#lastDownloadMs = Math.round(performance.now() - t0);
    return manifest;
  }
  #lastDownloadMs = null;     // the foreground (first-install) download, reported once in the next load's stats

  async #load(version, { quiet = false } = {}) {
    if (!quiet) this.#setState("loading", { version });
    const manifest = await this.#fetchManifest(version);
    const t0 = performance.now();
    const p = await this.#present(version, manifest);
    if (!p.base || !p.shards.length) throw new Error("the price database on this phone is incomplete");
    const stats = await this.call({ type: "load", root: new URL(DB_ROOT, location.href).href, base: new URL(`${DB_ROOT}${version}/`, location.href).href,
      manifest, cacheName: CACHE_PREFIX + version, filesCache: FILES_CACHE, only: p.shards });
    this.manifest = manifest;
    this.stats = { ...stats, wallMs: Math.round(performance.now() - t0), downloadMs: this.#lastDownloadMs };
    this.#lastDownloadMs = null;
    this.version = version;
    this.more = stats.pending?.length ? { loaded: stats.shards, pending: stats.pending } : null;
    if (!quiet) {
      this.#setState("ready", { version, manifest, stats: this.stats, more: this.more });
      this.#emit("ready", { stats: this.stats, manifest });
      this.#resolveReady?.(true);
    }
    this.#cleanup().catch(() => {});
    this.requestPersistence().catch(() => {});
  }

  /** The other departments of the open version: download what is missing (when online) and add it to the search. */
  #completeMore() {
    if (this.#moreTask || !this.more || !this.version) return this.#moreTask || Promise.resolve();
    const version = this.version;
    this.#moreTask = (async () => {
      if (!navigator.onLine) return;
      await this.#download(version, { background: true, tier: "more" });
      if (this.version !== version) return;
      const p = await this.#present(version, this.manifest);
      const stats = await this.call({ type: "load", root: new URL(DB_ROOT, location.href).href, base: new URL(`${DB_ROOT}${version}/`, location.href).href,
        manifest: this.manifest, cacheName: CACHE_PREFIX + version, filesCache: FILES_CACHE, only: p.shards });
      this.stats = { ...this.stats, ...stats };
      this.more = stats.pending?.length ? { loaded: stats.shards, pending: stats.pending } : null;
      this.#emit("more", { loaded: stats.shards, pending: stats.pending || [], items: stats.items });
    })().catch((err) => { console.warn("other departments not downloaded yet", err); }).finally(() => { this.#moreTask = null; });
    return this.#moreTask;
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
    this.#completeMore().catch(() => {});
    const cur = await this.#fetchCurrent();
    if (cur.version === this.version) { this.#writeKey(PENDING_KEY, null); return { upToDate: true }; }
    if (this.pendingUpdate?.version !== cur.version) {
      const manifest = await this.#download(cur.version, { background: true, tier: "all" });
      this.pendingUpdate = { version: cur.version, manifest };
      this.#writeKey(PENDING_KEY, { version: cur.version, at: Date.now() });
      this.#emit("update-available", { version: cur.version, manifest });
    }
    if (apply) { await this.applyUpdate(); return { applied: this.version === cur.version, version: cur.version }; }
    return { pending: true, version: cur.version };
  }

  /** Swap to the downloaded snapshot. Shards whose files did not change stay open; the old pack is restored on failure. */
  applyUpdate() {
    // one swap at a time: a second caller (the idle handler and an "Update now" tap) waits for the same one
    if (this.#applying) return this.#applying;
    if (!this.pendingUpdate) return Promise.resolve(false);
    this.#applying = this.#applyNow().finally(() => { this.#applying = null; });
    return this.#applying;
  }
  #applying = null;
  async #applyNow() {
    const u = this.pendingUpdate;
    const prev = this.version;
    this.pendingUpdate = null;
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

  /** Remove versions and shard files nothing uses any more (keeps the open, pending and downloading versions). */
  async #cleanup() {
    const keep = new Set([this.version, this.pendingUpdate?.version, this.#readKey(PENDING_KEY)?.version,
      ...[...this.#downloads.keys()].map((k) => k.split(":")[0])].filter(Boolean));
    const used = new Set();
    for (const v of keep) { const m = v === this.version ? this.manifest : await this.#manifestOf(v); if (m) for (const f of fileList(m, v)) used.add(new URL(f.url, location.href).href); }
    for (const n of await caches.keys()) {
      if (n === FILES_CACHE) {
        const c = await caches.open(n);
        for (const req of await c.keys()) if (!used.has(req.url)) await c.delete(req);
      } else if (n.startsWith(CACHE_PREFIX) && !keep.has(n.slice(CACHE_PREFIX.length))) await caches.delete(n);
    }
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
    this.version = null; this.manifest = null; this.stats = null; this.pendingUpdate = null; this.more = null;
  }
}
