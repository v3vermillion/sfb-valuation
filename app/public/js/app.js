// app.js — UI controller. One screen, two ways in (type / scan), one result sheet.
// Everything heavy (index, search, lookups) lives in db-worker.js; this file only renders.

import { DbClient } from "./db-client.js";
import { classifyCode, formatGtin } from "./barcode.js";
import { resolveCode, fromItem, kindLabel, titleOf, splitTitle, sizeText, fmtNum, notesFor } from "./resolve.js";
import { tokenize } from "./tokenize.js";

// ------------------------------------------------------------------ setup
const $ = (id) => document.getElementById(id);
const el = Object.fromEntries(["status", "statusText", "tallyBtn", "tallyCount", "tallyTotal", "settingsBtn", "progress", "progressBar", "home", "results", "list", "resultsMeta", "recent", "recentList", "q", "clearBtn", "scanBtn", "searchForm", "sheet", "tallySheet", "settings", "scanner", "video", "overlay", "scanClose", "scanEngine", "torchBtn", "reticle", "scanHint", "scanTypeForm", "scanTypeInput", "scanTypeBtn", "toasts", "quick", "heroEyebrow"].map((k) => [k, $(k)]));

const LIVE_URL = (document.querySelector('meta[name="sfb-live-check"]')?.content || "").trim().replace(/\/$/, "");
const BUILD = document.querySelector('meta[name="sfb-build"]')?.content || "dev";
const PREFS_KEY = "sfb.prefs", TALLY_KEY = "sfb.tally", RECENT_KEY = "sfb.recent";

const readJson = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
const writeJson = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } };
const prefs = Object.assign({ theme: "auto", haptics: true, live: true }, readJson(PREFS_KEY, {}));
let tally = readJson(TALLY_KEY, []);
let recent = readJson(RECENT_KEY, []);

const perf = { boot: { start: performance.now() }, keystrokes: [], scans: [], opens: [] };
const state = { query: "", seq: 0, last: null, codeHit: null, sheetRes: null, qty: 1, scan: null, scanOpen: false, source: null, pendingReload: false };

const db = new DbClient();
window.__sfb = { db, perf, state, prefs, resolveCode: (c, f) => resolveCode(db, c, f), openCode, openRank, openScanner, closeScanner, runSearch, version: BUILD };

// ------------------------------------------------------------------ helpers
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (cents) => (cents == null ? "—" : `$${(cents / 100).toFixed(2)}`);
const bigMoney = (cents) => {
  if (cents == null) return `<span class="price-big is-none" aria-label="No saved price">—</span>`;
  const d = Math.floor(cents / 100), c = String(cents % 100).padStart(2, "0");
  return `<span class="price-big" aria-label="${money(cents)}">$${d.toLocaleString()}<span class="cents" aria-hidden="true">.${c}</span></span>`;
};
const fmtInt = (n) => Number(n || 0).toLocaleString();
const compact = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}k` : String(n));
const fmtDate = (iso, long = false) => { if (!iso) return ""; const d = new Date(`${iso}T12:00:00`); return d.toLocaleDateString(undefined, long ? { month: "long", day: "numeric", year: "numeric" } : { month: "short", day: "numeric" }); };
const icon = (name, cls = "ico") => `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const haptic = (ms = 12) => { if (prefs.haptics && navigator.vibrate) { try { navigator.vibrate(ms); } catch { /* ignore */ } } };
const priceDate = () => db.manifest?.priceDate || db.manifest?.published?.slice(0, 10) || "";

function highlight(text, toks) {
  const t = String(text ?? "");
  const words = toks.filter((w) => w.length >= 2 || /\d/.test(w));
  if (!words.length) return esc(t);
  const re = new RegExp(`(^|[^a-z0-9])(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  let out = "", last = 0;
  for (const m of t.matchAll(re)) {
    const start = m.index + m[1].length;
    out += esc(t.slice(last, start)) + `<mark>${esc(m[2])}</mark>`;
    last = start + m[2].length;
  }
  return out + esc(t.slice(last));
}

function toast(text, { action, onAction, ms = 4200, iconName = "check" } = {}) {
  const t = document.createElement("div");
  t.className = "toast"; t.setAttribute("role", "status");
  t.innerHTML = `${icon(iconName)}<span>${esc(text)}</span>${action ? `<button type="button">${esc(action)}</button>` : ""}`;
  t.querySelector("button")?.addEventListener("click", () => { onAction?.(); dismiss(); });
  const dismiss = () => { if (!t.isConnected) return; t.classList.add("is-out"); setTimeout(() => t.remove(), 220); };
  el.toasts.appendChild(t);
  while (el.toasts.children.length > 3) el.toasts.firstChild.remove();
  if (ms) setTimeout(dismiss, ms);
  return dismiss;
}

// ------------------------------------------------------------------ theme / viewport
function applyTheme() {
  const root = document.documentElement;
  if (prefs.theme === "auto") delete root.dataset.theme; else root.dataset.theme = prefs.theme;
  const dark = prefs.theme === "dark" || (prefs.theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.querySelectorAll('meta[name="theme-color"]').forEach((m) => { m.content = dark ? "#141311" : "#f7f5f0"; });
}
applyTheme();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);

const vv = window.visualViewport;
function keyboardInset() {
  if (!vv) return;
  const inset = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop));
  document.documentElement.style.setProperty("--kb", `${inset}px`);
}
vv?.addEventListener("resize", keyboardInset);
vv?.addEventListener("scroll", keyboardInset);

// ------------------------------------------------------------------ modal stack (dialogs + scanner share history)
const modals = {
  open(dlg, html) {
    dlg.innerHTML = html;
    dlg.classList.remove("is-closing");
    if (!dlg.open) dlg.showModal();
    history.pushState({ modal: dlg.id, n: (history.state?.n || 0) + 1 }, "");
    dlg.querySelector(".sheet-inner").scrollTop = 0;
    dlg.querySelector(".x-btn")?.addEventListener("click", () => modals.close(dlg));
    grabToDismiss(dlg);
  },
  close(dlg, { fromPop = false } = {}) {
    if (!dlg.open) return;
    if (!fromPop && history.state?.modal === dlg.id) { history.back(); return; }   // popstate finishes the close
    const finish = () => { dlg.classList.remove("is-closing"); if (dlg.open) dlg.close(); dlg.dispatchEvent(new CustomEvent("closed")); };
    if (matchMedia("(prefers-reduced-motion: no-preference)").matches) { dlg.classList.add("is-closing"); setTimeout(finish, 220); } else finish();
  },
};
for (const dlg of [el.sheet, el.tallySheet, el.settings]) {
  dlg.addEventListener("cancel", (e) => { e.preventDefault(); modals.close(dlg); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) modals.close(dlg); });
}
window.addEventListener("popstate", () => {
  const openDlg = [el.sheet, el.tallySheet, el.settings].find((d) => d.open && !d.classList.contains("is-closing"));
  const top = history.state?.modal;
  if (openDlg && top !== openDlg.id) { modals.close(openDlg, { fromPop: true }); return; }
  if (state.scanOpen && top !== "scanner") closeScanner({ fromPop: true });
});

function grabToDismiss(dlg) {
  const inner = dlg.querySelector(".sheet-inner"), grab = dlg.querySelector(".grab");
  if (!grab) return;
  let y0 = null;
  grab.addEventListener("pointerdown", (e) => { y0 = e.clientY; grab.setPointerCapture(e.pointerId); dlg.style.transition = "none"; });
  grab.addEventListener("pointermove", (e) => { if (y0 == null) return; const dy = Math.max(0, e.clientY - y0); dlg.style.transform = `translateY(${dy}px)`; });
  const end = (e) => {
    if (y0 == null) return;
    const dy = e.clientY - y0; y0 = null;
    dlg.style.transition = ""; dlg.style.transform = "";
    if (dy > 90) modals.close(dlg); else inner.scrollTop = 0;
  };
  grab.addEventListener("pointerup", end); grab.addEventListener("pointercancel", end);
}

// ------------------------------------------------------------------ status / progress
function setStatus(stateName, text) {
  el.status.dataset.state = stateName;
  el.statusText.textContent = text;
}
function setProgress(frac) {
  if (frac == null) { el.progress.hidden = true; el.progressBar.style.width = "0"; return; }
  el.progress.hidden = false; el.progressBar.style.width = `${Math.round(Math.min(1, Math.max(0, frac)) * 100)}%`;
}
function readyText() {
  const m = db.manifest; if (!m) return "Ready";
  return `${navigator.onLine ? "" : "Offline · "}${compact(m.items)} items · ${fmtDate(priceDate())}`;
}

db.addEventListener("state", (e) => {
  const d = e.detail;
  switch (d.state) {
    case "downloading": setStatus("downloading", "Downloading prices…"); break;
    case "loading": setStatus("loading", "Opening database…"); break;
    case "ready": setStatus("ready", readyText()); setProgress(null); break;
    case "offline-empty": setStatus("offline", "Offline — connect once to get prices"); setProgress(null); break;
    case "error": setStatus("error", "Database problem — tap for details"); setProgress(null); state.dbError = d.message; break;
  }
});
db.addEventListener("progress", (e) => {
  const d = e.detail;
  if (d.phase === "download") { setProgress(d.totalBytes ? d.doneBytes / d.totalBytes : 0); setStatus("downloading", `Downloading prices… ${Math.round((d.doneBytes / (d.totalBytes || 1)) * 100)}%`); }
  else setProgress(0.9 + 0.1 * (d.done / d.total));
});
db.addEventListener("ready", () => {
  performance.mark("sfb:db-ready");
  perf.boot.dbReadyMs = Math.round(performance.now());
  perf.boot.loadMs = db.stats?.loadMs; perf.boot.wallMs = db.stats?.wallMs;
  requestAnimationFrame(() => { performance.mark("sfb:interactive"); perf.boot.interactiveMs = Math.round(performance.now()); document.documentElement.dataset.ready = "1"; });
  if (db.manifest?.fixture) el.heroEyebrow.textContent = "Strongsville Food Bank · sample data";
  if (state.query.trim()) runSearch(state.query);
  if (new URLSearchParams(location.search).get("scan") === "1" && !state.scanOpen) { history.replaceState(null, "", location.pathname); openScanner(); }
});
db.addEventListener("update-available", (e) => {
  const idle = !el.sheet.open && !el.tallySheet.open && !el.settings.open && !state.scanOpen && !state.query.trim();
  const apply = () => db.applyUpdate().then(() => toast(`Prices updated to ${fmtDate(db.manifest?.priceDate, true)}`));
  if (idle) apply(); else toast("Newer prices are ready", { action: "Use now", onAction: apply, ms: 8000, iconName: "refresh" });
});
window.addEventListener("online", () => { if (db.state === "ready") setStatus("ready", readyText()); db.checkForUpdate().catch(() => {}); });
window.addEventListener("offline", () => { if (db.state === "ready") setStatus("ready", readyText()); toast("Offline — scanning and search still work", { iconName: "wifi-off" }); });

// ------------------------------------------------------------------ search
el.q.addEventListener("input", () => {
  const q = el.q.value;
  el.clearBtn.hidden = !q;
  state.query = q;
  if (!q.trim()) { showHome(); return; }
  cancelMore();
  runSearch(q);
});
el.clearBtn.addEventListener("click", () => { el.q.value = ""; el.clearBtn.hidden = true; state.query = ""; showHome(); el.q.focus(); });
el.searchForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (state.codeHit) { openResolution(state.codeHit, { source: "typed" }); return; }
  const first = state.last?.items?.[0];
  if (first) openRank(first.rank, { closest: !!state.last.relaxed });
});
el.quick.addEventListener("click", (e) => {
  const b = e.target.closest("[data-q]"); if (!b) return;
  el.q.value = b.dataset.q; el.q.dispatchEvent(new Event("input")); el.q.focus({ preventScroll: true });
});

function showHome() {
  state.seq++;
  el.results.hidden = true; el.home.hidden = false;
  el.list.innerHTML = ""; el.resultsMeta.textContent = "";
  state.last = null; state.codeHit = null;
  renderRecent();
}

async function runSearch(q) {
  const t0 = performance.now();
  const seq = ++state.seq;
  if (db.state !== "ready") {
    el.home.hidden = true; el.results.hidden = false;
    el.list.innerHTML = `<li class="empty">${db.state === "offline-empty" ? "Prices haven't been downloaded yet. Connect once and they stay on this phone." : "Opening the price database…"}</li>`;
    el.resultsMeta.textContent = "";
    return;
  }
  const cls = classifyCode(q);
  const [res, code] = await Promise.all([db.search(q, 40), cls.kind === "text" ? null : resolveCode(db, q).catch(() => null)]);
  if (seq !== state.seq) return;       // a newer keystroke won
  const t1 = performance.now();
  state.last = res; state.codeHit = code;
  renderResults(res, code, q);
  const t2 = performance.now();
  requestAnimationFrame(() => perf.keystrokes.push({ q, workerMs: res.ms, roundtripMs: Math.round((t1 - t0) * 10) / 10, renderMs: Math.round((t2 - t1) * 10) / 10, totalMs: Math.round((performance.now() - t0) * 10) / 10, n: res.items.length }));
}

function rowHtml(it, toks) {
  const { pre, brand, rest } = splitTitle(it);
  const title = brand ? `${highlight(pre, toks)}<b>${highlight(brand, toks)}</b>${highlight(rest, toks)}` : highlight(rest, toks);
  const tags = [sizeText(it), it.pack > 1 ? `Pack of ${it.pack}` : "", it.storeBrand ? "Store brand" : "", it.retired ? "older barcode" : "", it.unavailable ? "out of stock at check" : ""].filter(Boolean);
  const sub = it.basis === "lb" ? "<small>per lb</small>" : it.pack > 1 ? `<small>${money(Math.round(it.priceCents / it.pack))} each</small>` : "";
  return `<li><button class="row${it.retired ? " is-retired" : ""}" type="button" data-rank="${it.rank}"><span class="name">${title}</span><span class="price">${money(it.priceCents)}${sub}</span><span class="meta">${tags.map((t) => `<span class="tag">${esc(t)}</span>`).join("")}</span></button></li>`;
}
function codeRowHtml(res) {
  const sub = res.unit === "lb" ? "<small>per lb</small>" : "";
  return `<li><button class="row row--code" type="button" data-code="${esc(res.code)}"><span class="name"><span class="kind" data-kind="${res.kind}">${esc(kindLabel(res))}</span><span class="code-title">${esc(res.title)}</span></span><span class="price">${money(res.priceCents)}${sub}</span><span class="meta"><span class="tag mono">${esc(res.gtin ? formatGtin(res.gtin) : res.code)}</span></span></button></li>`;
}

const FIRST_ROWS = 12;   // painted synchronously (more than a phone screen); the rest arrive on the next idle slice
let moreTimer = 0;
function cancelMore() { if (!moreTimer) return; ("cancelIdleCallback" in window ? cancelIdleCallback : clearTimeout)(moreTimer); moreTimer = 0; }
function renderResults(res, code, q) {
  el.home.hidden = true; el.results.hidden = false;
  const toks = tokenize(q);
  let html = code ? codeRowHtml(code) : "";
  const first = res.items.slice(0, FIRST_ROWS), rest = res.items.slice(FIRST_ROWS);
  for (const it of first) html += rowHtml(it, toks);
  if (!html) html = `<li class="empty">Nothing matches <b>${esc(q)}</b>. Try fewer words, the brand, or scan the barcode.</li>`;
  el.list.innerHTML = html;
  cancelMore();
  if (rest.length) {
    const seq = state.seq;
    const append = () => { moreTimer = 0; if (seq !== state.seq) return; el.list.insertAdjacentHTML("beforeend", rest.map((it) => rowHtml(it, toks)).join("")); };
    // the remaining rows arrive when the main thread is idle, so a fast typist never pays for them between keystrokes
    moreTimer = "requestIdleCallback" in window ? requestIdleCallback(append, { timeout: 400 }) : setTimeout(append, 150);
  }
  let meta = "";
  if (res.notReady) meta = "Opening the price database…";
  else if (res.items.length) {
    meta = `<b>${fmtInt(res.total)}</b> ${res.total === 1 ? "match" : "matches"} · best one is next to the search box`;
    if (res.fuzzy) meta += " · spelling adjusted";
    if (res.relaxed) meta = `<span class="warn">Closest matches</span> — nothing had every word${res.dropped?.length ? ` (ignored “${esc(res.dropped.join(" "))}”)` : ""}`;
  }
  el.resultsMeta.innerHTML = meta;
}

el.list.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-rank], button[data-code]"); if (!b) return;
  if (b.dataset.code != null) { if (state.codeHit) openResolution(state.codeHit, { source: "typed" }); return; }
  openRank(Number(b.dataset.rank), { closest: !!state.last?.relaxed });
});

async function openRank(rank, { closest = false, source = "search" } = {}) {
  const item = await db.item(rank);
  if (!item) return;
  openResolution(fromItem(item, { closest, query: state.query, dropped: state.last?.dropped || [] }), { source });
}
async function openCode(raw, { source = "typed", format } = {}) {
  const res = await resolveCode(db, raw, format);
  if (!res) { toast("That isn't a barcode number", { iconName: "info" }); return null; }
  openResolution(res, { source });
  return res;
}

// ------------------------------------------------------------------ result sheet
function defaultQty(res) { return res.unit === "lb" ? 1 : 1; }

function sheetHtml(res) {
  const it = res.item;
  const label = kindLabel(res);
  const basis = res.priceCents == null ? "" : res.unit === "lb" ? "per lb" : res.kind === "store-label" ? "on the label" : "each";
  const chips = [];
  if (it && (res.kind === "exact" || res.kind === "closest")) {
    const s = sizeText(it); if (s) chips.push(s);
    if (it.pack > 1) chips.push(`Pack of ${it.pack}`);
    if (it.catName) chips.push(it.catName);
    if (it.storeBrand) chips.push("Store brand");
  }
  if (res.kind === "plu") { chips.push(`PLU ${res.code}`); chips.push(res.unit === "lb" ? "Sold by weight" : "Sold each"); }
  if (res.kind === "equivalent") { const e = res.equiv; if (e.quantity) chips.push(e.quantity); chips.push(`Confidence: ${e.confidence}`); }
  if (res.kind === "store-label") { chips.push(`Item ref ${res.label.itemRef}`); chips.push(res.label.verified ? "Price digit verified" : "Unverified price"); }
  if (res.gtin && res.kind !== "plu" && res.kind !== "unknown") chips.push(`<span class="mono">${esc(formatGtin(res.gtin))}</span>`);
  const notes = notesFor(res, { priceDateLong: fmtDate(priceDate(), true) });
  const title = res.kind === "exact" || res.kind === "closest" ? boldTitle(it) : res.kind === "live" ? boldTitle({ brand: res.brand, name: res.name }) : esc(res.title);
  const checked = res.kind === "live" ? "Walmart price, checked just now" : res.kind === "store-label" ? "Read from the scale label, not a Walmart catalog price" : res.kind === "plu" && res.entry.source === "typical" ? "Typical Walmart price" : res.priceCents == null ? "No saved price for this barcode" : `Walmart price, checked ${fmtDate(priceDate(), true)}`;

  const perEach = it && it.pack > 1 && res.unit !== "lb" ? `<p class="price-note">${money(Math.round(res.priceCents / it.pack))} per single item in the pack</p>` : "";
  const liveRow = (LIVE_URL && prefs.live && res.gtin && res.kind !== "store-label" && res.kind !== "plu") ? `<div class="live-row" data-state="idle" hidden></div>` : "";

  const stepper = res.priceCents == null ? "" : res.unit === "lb"
    ? `<div class="stepper" role="group" aria-label="Weight"><button class="st-btn" type="button" data-step="-0.25" aria-label="Less weight">${icon("minus")}</button><span class="st-val counting"><span id="qtyVal">${fmtNum(state.qty)}</span><small>lb</small></span><button class="st-btn" type="button" data-step="0.25" aria-label="More weight">${icon("plus")}</button></div>`
    : `<div class="stepper" role="group" aria-label="Quantity"><button class="st-btn" type="button" data-step="-1" aria-label="One fewer">${icon("minus")}</button><span class="st-val counting"><span id="qtyVal">${state.qty}</span><small>${state.qty === 1 ? "item" : "items"}</small></span><button class="st-btn" type="button" data-step="1" aria-label="One more">${icon("plus")}</button></div>`;

  const primary = res.priceCents == null
    ? `<button class="btn btn--accent btn--block" type="button" data-act="find">${icon("search")} Find it by name</button>`
    : `<button class="btn btn--accent btn--block" type="button" data-act="add">${icon("receipt")} Add <span id="addTotal" class="counting">${money(lineTotal(res))}</span> to tally</button>`;
  const secondary = state.source === "scan"
    ? `<button class="btn btn--ghost" type="button" data-act="scan">${icon("scan")} Scan next</button><button class="btn btn--ghost" type="button" data-act="close">Done</button>`
    : `<button class="btn btn--ghost" type="button" data-act="scan">${icon("scan")} Scan</button><button class="btn btn--ghost" type="button" data-act="close">Back to search</button>`;

  const also = res.others?.length ? `<section class="also"><h2 class="h2">Same barcode, other listings</h2><ol class="list list--compact">${res.others.map((o) => rowHtml(o, [])).join("")}</ol></section>` : "";
  const basisCard = res.kind === "equivalent" && res.equiv.basis ? basisCardHtml("Priced from this Walmart item", res.equiv.basis)
    : res.kind === "plu" && res.item ? basisCardHtml("Priced from this Walmart listing", res.item) : "";

  const facts = [];
  if (res.gtin) facts.push(["Barcode", `<span class="mono">${esc(formatGtin(res.gtin))}</span>`]);
  if (res.kind === "store-label") facts.push(["Layout", esc(res.label.layout)], ["Digits", `<span class="mono">${esc(res.label.digits)}</span>`]);
  if (it) {
    facts.push(["Walmart item", `#${esc(String(it.id))}`]);
    if (it.catName) facts.push(["Department", esc(it.catName)]);
    facts.push(["Listing", it.primary ? "Primary for this barcode" : "Secondary listing"]);
  }
  if (res.kind === "equivalent") facts.push(["Source", "Equivalent values table"]);
  facts.push(["Prices as of", esc(fmtDate(priceDate(), true) || "—")]);
  if (db.manifest?.fixture) facts.push(["Data", "Sample snapshot (synthetic)"]);

  return `<div class="sheet-inner">
    <div class="grab" aria-hidden="true"></div>
    <div class="sheet-head"><span class="kind" data-kind="${esc(res.kind)}">${esc(label)}</span><button class="x-btn" type="button" aria-label="Close">${icon("x")}</button></div>
    <div class="price-block">${bigMoney(res.priceCents)}${basis ? `<span class="price-basis">${basis}</span>` : ""}</div>
    <p class="price-note">${esc(checked)}</p>${perEach}
    <h2 class="item-title" id="sheetTitle">${title}</h2>
    ${chips.length ? `<div class="chips">${chips.map((c) => `<span class="t">${c}</span>`).join("")}</div>` : ""}
    ${notes.map((n) => `<p class="note${n.tone ? ` note--${n.tone}` : ""}">${esc(n.text)}</p>`).join("")}
    ${liveRow}
    ${stepper}
    <div class="actions">${primary}${secondary}</div>
    ${basisCard}${also}
    <ul class="facts">${facts.map(([k, v]) => `<li><span>${k}</span><span>${v}</span></li>`).join("")}</ul>
  </div>`;
}

function boldTitle(item) {
  const { pre, brand, rest } = splitTitle(item);
  return brand ? `${esc(pre)}<b>${esc(brand)}</b>${esc(rest)}` : esc(rest);
}
function basisCardHtml(heading, item) {
  return `<section class="also"><h2 class="h2">${esc(heading)}</h2><button class="basis-card" type="button" data-rank="${item.rank}"><span><span class="name">${boldTitle(item)}</span><span class="sub">${esc([sizeText(item), item.pack > 1 ? `Pack of ${item.pack}` : ""].filter(Boolean).join(" · ") || item.catName || "")}</span></span><span class="price">${money(item.priceCents)}${item.basis === "lb" ? "<small>per lb</small>" : ""}</span></button></section>`;
}

function lineTotal(res) { return Math.round(res.priceCents * state.qty); }

function openResolution(res, { source = "search" } = {}) {
  const t0 = performance.now();
  state.sheetRes = res; state.source = source; state.qty = defaultQty(res);
  modals.open(el.sheet, sheetHtml(res));
  wireSheet(el.sheet, res);
  pushRecent(res);
  requestAnimationFrame(() => perf.opens.push({ kind: res.kind, source, ms: Math.round((performance.now() - t0) * 10) / 10 }));
  if (res.priceCents != null) haptic(8);
  liveCheck(res).catch(() => {});
}

function wireSheet(dlg, res) {
  dlg.querySelectorAll("[data-step]").forEach((b) => b.addEventListener("click", () => {
    const step = Number(b.dataset.step);
    const min = res.unit === "lb" ? 0.25 : 1, max = res.unit === "lb" ? 200 : 99;
    state.qty = Math.min(max, Math.max(min, Math.round((state.qty + step) * 100) / 100));
    const v = dlg.querySelector("#qtyVal"); if (v) v.textContent = res.unit === "lb" ? fmtNum(state.qty) : String(state.qty);
    const small = v?.nextElementSibling; if (small && res.unit !== "lb") small.textContent = state.qty === 1 ? "item" : "items";
    const tot = dlg.querySelector("#addTotal"); if (tot) tot.textContent = money(lineTotal(res));
    haptic(5);
  }));
  dlg.querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", () => {
    const act = b.dataset.act;
    if (act === "add") { addToTally(res); modals.close(dlg); if (state.source === "scan") resumeScan(); else { el.q.value = ""; el.clearBtn.hidden = true; state.query = ""; showHome(); } }
    else if (act === "scan") { modals.close(dlg); if (state.scanOpen) resumeScan(); else openScanner(); }
    else if (act === "find") { modals.close(dlg); if (state.scanOpen) closeScanner(); el.q.value = ""; state.query = ""; showHome(); el.q.placeholder = "Type the name and size from the label"; el.q.focus(); }
    else if (act === "close") { modals.close(dlg); if (state.scanOpen) resumeScan(); }
  }));
  dlg.querySelectorAll("[data-rank]").forEach((b) => b.addEventListener("click", async () => {
    const item = await db.item(Number(b.dataset.rank));
    if (item) { const r = fromItem(item); state.sheetRes = r; state.qty = 1; dlg.innerHTML = sheetHtml(r); dlg.querySelector(".x-btn")?.addEventListener("click", () => modals.close(dlg)); grabToDismiss(dlg); wireSheet(dlg, r); dlg.querySelector(".sheet-inner").scrollTop = 0; liveCheck(r).catch(() => {}); }
  }));
}
el.sheet.addEventListener("closed", () => { if (state.scanOpen) resumeScan(); else el.q.focus({ preventScroll: true }); });

// ------------------------------------------------------------------ live Walmart check (public, rate-limited Worker route; no token in the client)
async function liveCheck(res) {
  const row = el.sheet.querySelector(".live-row");
  if (!row || !LIVE_URL || !prefs.live || !res.gtin) return;
  if (!navigator.onLine) { row.hidden = false; row.dataset.state = "off"; row.innerHTML = `${icon("wifi-off")}<span>Offline — showing the saved price.</span>`; return; }
  row.hidden = false; row.dataset.state = "checking";
  row.innerHTML = `${icon("refresh")}<span>Checking Walmart's price right now…</span>`;
  const ctrl = new AbortController(); const timer = setTimeout(() => ctrl.abort(), 8000);
  try {
    const r = await fetch(`${LIVE_URL}/v1/price/${res.gtin}`, { signal: ctrl.signal, headers: { accept: "application/json" } });
    clearTimeout(timer);
    if (state.sheetRes !== res || !el.sheet.open) return;
    if (r.status === 429) { row.dataset.state = "error"; row.innerHTML = `${icon("info")}<span>Live check is busy right now. The saved price is shown.</span>`; return; }
    const j = await r.json().catch(() => null);
    if (!r.ok || !j?.ok) { row.dataset.state = "none"; row.innerHTML = `${icon("info")}<span>Walmart has no live price for this barcode right now.</span>`; return; }
    const live = Math.round(Number(j.price) * 100);
    if (!Number.isFinite(live)) throw new Error("bad price");
    if (res.kind === "unknown") {
      // the saved database didn't know it, Walmart does: show the live listing as the result
      const lr = { ...res, kind: "live", priceCents: live, name: j.name || "Walmart item", brand: j.brand || "", title: [j.brand, j.name].filter(Boolean).join(" "), live: j };
      state.sheetRes = lr; state.qty = 1;
      el.sheet.innerHTML = sheetHtml(lr); el.sheet.querySelector(".x-btn")?.addEventListener("click", () => modals.close(el.sheet)); grabToDismiss(el.sheet); wireSheet(el.sheet, lr);
      const r2 = el.sheet.querySelector(".live-row"); if (r2) { r2.hidden = false; r2.dataset.state = "ok"; r2.innerHTML = `${icon("bolt")}<span>Found on Walmart.com just now${j.stock ? ` · ${esc(j.stock)}` : ""}</span>`; }
      pushRecent(lr); haptic(8);
      return;
    }
    const diff = live - res.priceCents;
    row.dataset.state = "ok";
    if (diff === 0) row.innerHTML = `${icon("bolt")}<span>Walmart right now: <b>${money(live)}</b> — same as saved</span>`;
    else {
      row.innerHTML = `${icon("bolt")}<span>Walmart right now: <b>${money(live)}</b></span><span class="delta ${diff > 0 ? "up" : "down"}">${diff > 0 ? "+" : "−"}${money(Math.abs(diff))}</span><button class="btn btn--ghost btn--sm" type="button">Use it</button>`;
      row.querySelector("button").addEventListener("click", () => {
        res.priceCents = live; res.livePrice = live;
        const pb = el.sheet.querySelector(".price-block"); if (pb) pb.innerHTML = `${bigMoney(live)}<span class="price-basis">${res.unit === "lb" ? "per lb" : "each"}</span>`;
        const pn = el.sheet.querySelector(".price-note"); if (pn) pn.textContent = "Walmart price, checked just now";
        const tot = el.sheet.querySelector("#addTotal"); if (tot) tot.textContent = money(lineTotal(res));
        row.innerHTML = `${icon("check")}<span>Using Walmart's live price <b>${money(live)}</b></span>`;
      });
    }
  } catch {
    clearTimeout(timer);
    if (state.sheetRes !== res) return;
    row.dataset.state = "error"; row.innerHTML = `${icon("info")}<span>Live check unavailable right now. The saved price is shown.</span>`;
  }
}

// ------------------------------------------------------------------ tally
function renderTallyPill() {
  const count = tally.reduce((a, t) => a + (t.unit === "lb" ? 1 : t.qty), 0);
  const total = tally.reduce((a, t) => a + t.cents, 0);
  el.tallyBtn.hidden = tally.length === 0;
  el.tallyCount.textContent = String(count);
  el.tallyTotal.textContent = money(total);
}
function addToTally(res) {
  const cents = lineTotal(res);
  tally.push({ id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, title: res.kind === "exact" || res.kind === "closest" ? titleOf(res.item) : res.title, unitCents: res.priceCents, qty: state.qty, unit: res.unit, kind: res.kind, cents, at: Date.now(), key: res.key });
  writeJson(TALLY_KEY, tally);
  renderTallyPill();
  haptic(15);
  toast(`Added ${money(cents)} · tally ${money(tally.reduce((a, t) => a + t.cents, 0))}`, { action: "View", onAction: openTally, ms: 2600 });
}
function tallyHtml() {
  const total = tally.reduce((a, t) => a + t.cents, 0);
  const rows = tally.slice().reverse().map((t) => `<li><span class="tn">${esc(t.title)}<small>${t.unit === "lb" ? `${fmtNum(t.qty)} lb × ${money(t.unitCents)}` : `${t.qty} × ${money(t.unitCents)}`} · ${esc(kindLabel({ kind: t.kind }))}</small></span><span class="tp">${money(t.cents)}</span><button class="x-btn" type="button" data-remove="${t.id}" aria-label="Remove ${esc(t.title)}">${icon("trash")}</button></li>`).join("");
  return `<div class="sheet-inner"><div class="grab" aria-hidden="true"></div>
    <div class="sheet-head"><h2 class="h2" id="tallyTitle">Running tally</h2><button class="x-btn" type="button" aria-label="Close">${icon("x")}</button></div>
    ${tally.length ? `<ul class="tally-list">${rows}</ul>` : `<p class="empty">Nothing in the tally yet. Open an item and tap <b>Add to tally</b>.</p>`}
    <div class="tally-total-row"><span>${tally.length} ${tally.length === 1 ? "line" : "lines"}</span><b class="counting">${money(total)}</b></div>
    <div class="actions"><button class="btn btn--accent" type="button" data-act="share" ${tally.length ? "" : "disabled"}>${icon("share")} Share</button><button class="btn btn--danger" type="button" data-act="clear" ${tally.length ? "" : "disabled"}>${icon("trash")} Clear</button></div>
    <p class="fine">The tally stays on this phone until you clear it. Totals use Walmart prices as of ${esc(fmtDate(priceDate(), true) || "the last check")}.</p>
  </div>`;
}
function openTally() {
  modals.open(el.tallySheet, tallyHtml());
  el.tallySheet.addEventListener("click", (e) => {
    const rm = e.target.closest("[data-remove]");
    if (rm) { tally = tally.filter((t) => t.id !== rm.dataset.remove); writeJson(TALLY_KEY, tally); renderTallyPill(); el.tallySheet.innerHTML = tallyHtml(); el.tallySheet.querySelector(".x-btn")?.addEventListener("click", () => modals.close(el.tallySheet)); grabToDismiss(el.tallySheet); haptic(5); return; }
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act === "clear") { if (confirm(`Clear ${tally.length} ${tally.length === 1 ? "line" : "lines"} from the tally?`)) { tally = []; writeJson(TALLY_KEY, tally); renderTallyPill(); modals.close(el.tallySheet); toast("Tally cleared"); } }
    else if (act === "share") shareTally();
  }, { once: false });
}
async function shareTally() {
  const total = tally.reduce((a, t) => a + t.cents, 0);
  const lines = tally.map((t) => `${t.unit === "lb" ? `${fmtNum(t.qty)} lb` : `${t.qty}×`} ${t.title} — ${money(t.cents)}`);
  const text = `SFB donation value · ${new Date().toLocaleDateString()}\n${lines.join("\n")}\nTotal: ${money(total)}\n(Walmart prices as of ${fmtDate(priceDate(), true)})`;
  try {
    if (navigator.share) await navigator.share({ title: "SFB donation value", text });
    else { await navigator.clipboard.writeText(text); toast("Copied the tally"); }
  } catch (err) { if (err?.name !== "AbortError") { try { await navigator.clipboard.writeText(text); toast("Copied the tally"); } catch { toast("Couldn't share on this device", { iconName: "info" }); } } }
}
el.tallyBtn.addEventListener("click", openTally);
renderTallyPill();

// ------------------------------------------------------------------ recent
function pushRecent(res) {
  if (res.priceCents == null) return;
  const entry = { key: res.key, kind: res.kind, title: res.kind === "exact" || res.kind === "closest" ? titleOf(res.item) : res.title, priceCents: res.priceCents, unit: res.unit, code: res.code || null, rank: res.item?.rank ?? null, at: Date.now() };
  recent = [entry, ...recent.filter((r) => r.key !== res.key)].slice(0, 8);
  writeJson(RECENT_KEY, recent);
  renderRecent();
}
function renderRecent() {
  el.recent.hidden = recent.length === 0;
  el.recentList.innerHTML = recent.slice(0, 4).map((r, i) => `<li><button class="row" type="button" data-recent="${i}"><span class="name">${esc(r.title)}</span><span class="price">${money(r.priceCents)}${r.unit === "lb" ? "<small>per lb</small>" : ""}</span><span class="meta"><span class="tag">${esc(kindLabel({ kind: r.kind }))}</span></span></button></li>`).join("");
}
el.recentList.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-recent]"); if (!b) return;
  const r = recent[Number(b.dataset.recent)]; if (!r) return;
  if (r.code && r.kind !== "exact" && r.kind !== "closest") openCode(r.code, { source: "recent" });
  else if (r.rank != null) openRank(r.rank, { source: "recent" });
  else if (r.code) openCode(r.code, { source: "recent" });
});
renderRecent();

// ------------------------------------------------------------------ settings
function settingsHtml() {
  const m = db.manifest, s = db.stats;
  const seg = ["auto", "light", "dark"].map((t) => `<button type="button" data-theme="${t}" aria-pressed="${prefs.theme === t}">${t[0].toUpperCase() + t.slice(1)}</button>`).join("");
  return `<div class="sheet-inner"><div class="grab" aria-hidden="true"></div>
    <div class="sheet-head"><h2 class="h2" id="settingsTitle">Settings</h2><button class="x-btn" type="button" aria-label="Close">${icon("x")}</button></div>
    <div class="setting"><div class="lab">Appearance<small>Auto follows the phone</small></div><div class="seg" role="group" aria-label="Appearance">${seg}</div></div>
    <div class="setting"><div class="lab">Vibrate on scan<small>A short buzz when a barcode is read</small></div><button class="switch" type="button" role="switch" aria-checked="${prefs.haptics}" data-pref="haptics" aria-label="Vibrate on scan"></button></div>
    <div class="setting"><div class="lab">Live Walmart check<small>${LIVE_URL ? "When online, confirm a scanned item's price against Walmart.com right now" : "Not configured for this deployment"}</small></div><button class="switch" type="button" role="switch" aria-checked="${prefs.live && !!LIVE_URL}" data-pref="live" aria-label="Live Walmart check" ${LIVE_URL ? "" : "disabled"}></button></div>
    <h2 class="h2">Price database</h2>
    ${m ? `<dl class="kv">
      <dt>Prices as of</dt><dd>${esc(fmtDate(priceDate(), true))}</dd>
      <dt>Items</dt><dd>${fmtInt(m.items)}</dd>
      <dt>Barcodes</dt><dd>${fmtInt(m.upcs)}</dd>
      <dt>Equivalents</dt><dd>${fmtInt(m.equivalents)}</dd>
      <dt>On this phone</dt><dd>${(m.totalGzBytes / 1048576).toFixed(1)} MB</dd>
      <dt>Opened in</dt><dd>${s?.wallMs ?? "—"} ms</dd>
      <dt>Snapshot</dt><dd class="mono">${esc(m.version)}</dd>
      <dt>App build</dt><dd class="mono">${esc(BUILD)}</dd>
    </dl>` : `<p class="note${state.dbError ? " note--warn" : ""}">${esc(state.dbError ? `The database couldn't be opened: ${state.dbError}` : "The price database hasn't finished loading.")}</p>`}
    ${m?.fixture ? `<p class="note note--warn">Sample data. This snapshot is a synthetic, full-size stand-in built in the shape of the real crawl so speed and behaviour can be proven before the first published crawl. Prices are plausible, not real.</p>` : ""}
    <div class="actions"><button class="btn btn--ghost" type="button" data-act="update">${icon("refresh")} Check for new prices</button><button class="btn btn--danger" type="button" data-act="reset">${icon("trash")} Reset app data</button></div>
    <p class="fine">Prices are Walmart.com prices for the Strongsville area captured by the food bank's price pipeline. “Equivalent value” items aren't sold at Walmart; they take the price of the closest Walmart item by type and size. Everything works offline once the database is on the phone. Non-Walmart barcodes are identified with data from Open Food Facts, Open Beauty Facts and Open Products Facts (ODbL). Barcode decoding by zxing-cpp (Apache-2.0).</p>
  </div>`;
}
function openSettings() {
  modals.open(el.settings, settingsHtml());
  el.settings.addEventListener("click", async (e) => {
    const th = e.target.closest("[data-theme]");
    if (th) { prefs.theme = th.dataset.theme; writeJson(PREFS_KEY, prefs); applyTheme(); el.settings.querySelectorAll("[data-theme]").forEach((b) => b.setAttribute("aria-pressed", String(b === th))); return; }
    const sw = e.target.closest("[data-pref]");
    if (sw) { const k = sw.dataset.pref; prefs[k] = !prefs[k]; writeJson(PREFS_KEY, prefs); sw.setAttribute("aria-checked", String(prefs[k])); haptic(5); return; }
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act === "update") {
      if (!navigator.onLine) { toast("You're offline — will check when back online", { iconName: "wifi-off" }); return; }
      const d = toast("Checking for new prices…", { ms: 0, iconName: "refresh" });
      try { const r = await db.checkForUpdate({ apply: true }); d(); toast(r.upToDate ? "Prices are up to date" : r.downloaded ? `Updated to ${fmtDate(db.manifest?.priceDate, true)}` : "Nothing new yet"); el.settings.innerHTML = settingsHtml(); el.settings.querySelector(".x-btn")?.addEventListener("click", () => modals.close(el.settings)); grabToDismiss(el.settings); }
      catch (err) { d(); toast(`Couldn't check: ${err.message}`, { iconName: "info" }); }
    } else if (act === "reset") {
      if (!confirm("Remove the downloaded prices, tally and recents from this phone? The app will re-download prices when online.")) return;
      await db.reset(); tally = []; recent = []; localStorage.removeItem(TALLY_KEY); localStorage.removeItem(RECENT_KEY);
      if ("serviceWorker" in navigator) { const regs = await navigator.serviceWorker.getRegistrations(); await Promise.all(regs.map((r) => r.unregister())); }
      for (const n of await caches.keys()) await caches.delete(n);
      location.reload();
    }
  });
}
el.settingsBtn.addEventListener("click", openSettings);
el.status.addEventListener("click", openSettings);

// ------------------------------------------------------------------ scanner
let scannerMod = null;
async function openScanner() {
  if (state.scanOpen) return;
  state.scanOpen = true;
  el.scanner.hidden = false; el.scanner.classList.remove("is-hit");
  el.scanHint.textContent = "Line the barcode up in the frame";
  el.scanTypeForm.hidden = true; el.scanTypeBtn.hidden = false; el.torchBtn.hidden = true;
  el.scanner.querySelector(".scan-denied")?.remove(); el.reticle.hidden = false;
  history.pushState({ modal: "scanner", n: (history.state?.n || 0) + 1 }, "");
  el.scanClose.focus({ preventScroll: true });
  if (!navigator.mediaDevices?.getUserMedia || !window.isSecureContext) { scanDenied("The camera needs a secure (https) page. Type the barcode digits instead."); return; }
  try {
    scannerMod ||= await import("./scanner.js");
    el.scanEngine.textContent = "starting camera";
    state.scan = await scannerMod.startScanner(el.video, el.overlay, onScanHit, (info) => {
      if (info.engine) el.scanEngine.textContent = info.engine === "native" ? "native decoder" : "zxing decoder";
      if (info.torch != null) el.torchBtn.hidden = !info.torch;
      if (info.error) console.warn("scanner:", info.error);
    });
    if (!state.scanOpen) { state.scan.stop(); return; }
  } catch (err) {
    console.warn("camera", err);
    scanDenied(err?.name === "NotAllowedError" ? "Camera access was turned off for this site. Allow it in the browser's site settings, or type the barcode." : err?.name === "NotFoundError" ? "No camera was found on this device. Type the barcode instead." : "The camera couldn't start. Type the barcode instead.");
  }
}
function scanDenied(msg) {
  el.reticle.hidden = true; el.scanEngine.textContent = ""; el.scanHint.textContent = "Enter the digits printed under the barcode";
  const d = document.createElement("div"); d.className = "scan-denied"; d.innerHTML = `<p>${esc(msg)}</p>`;
  el.scanner.insertBefore(d, el.scanner.querySelector(".scan-bottom"));
  showScanType();
}
function showScanType() { el.scanTypeForm.hidden = false; el.scanTypeBtn.hidden = true; el.scanTypeInput.value = ""; el.scanTypeInput.focus(); }
function closeScanner({ fromPop = false } = {}) {
  if (!state.scanOpen) return;
  if (!fromPop && history.state?.modal === "scanner") { history.back(); return; }
  state.scanOpen = false;
  state.scan?.stop(); state.scan = null;
  el.scanner.hidden = true;
  el.scanner.querySelector(".scan-denied")?.remove();
  if (!el.sheet.open) el.scanBtn.focus({ preventScroll: true });
}
function resumeScan() {
  if (!state.scanOpen || !state.scan) return;
  el.scanner.classList.remove("is-hit"); el.scanHint.textContent = "Line the barcode up in the frame";
  state.scan.resume();
}
async function onScanHit(hit) {
  const t0 = performance.now();
  haptic(20);
  el.scanner.classList.add("is-hit");
  el.scanHint.textContent = `Read ${formatGtin(hit.gtin?.gtin14 || hit.raw)}`;
  const res = await resolveCode(db, hit.raw, hit.format);
  if (!res) { el.scanHint.textContent = "That barcode isn't a product code"; setTimeout(resumeScan, 900); return; }
  state.source = "scan";
  openResolution(res, { source: "scan" });
  requestAnimationFrame(() => perf.scans.push({ code: hit.raw, kind: res.kind, decodeMs: hit.ms, engine: hit.engine, toPriceMs: Math.round((performance.now() - t0) * 10) / 10 }));
}
el.scanBtn.addEventListener("click", openScanner);
el.scanClose.addEventListener("click", () => closeScanner());
el.torchBtn.addEventListener("click", async () => { const on = await state.scan?.setTorch(!state.scan.torch); el.torchBtn.setAttribute("aria-pressed", String(!!on)); });
el.scanTypeBtn.addEventListener("click", showScanType);
el.scanTypeForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const v = el.scanTypeInput.value.trim(); if (!v) return;
  const res = await openCode(v, { source: "scan" });
  if (res) { state.source = "scan"; el.scanTypeInput.value = ""; }
});
document.addEventListener("visibilitychange", () => { if (document.hidden && state.scanOpen && !el.sheet.open) closeScanner(); });

// ------------------------------------------------------------------ keyboard shortcuts (desktop testing, external scanners that type digits + Enter)
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== el.q && !el.sheet.open && !el.settings.open && !el.tallySheet.open && !state.scanOpen) { e.preventDefault(); el.q.focus(); }
});

// ------------------------------------------------------------------ service worker + boot
if ("serviceWorker" in navigator && !new URLSearchParams(location.search).has("nosw")) {
  window.addEventListener("load", async () => {
    try {
      const reg = await navigator.serviceWorker.register("./sw.js");
      reg.addEventListener("updatefound", () => {
        const nw = reg.installing; if (!nw) return;
        nw.addEventListener("statechange", () => {
          if (nw.state === "installed" && navigator.serviceWorker.controller) toast("An app update is ready", { action: "Reload", ms: 0, iconName: "refresh", onAction: () => { state.pendingReload = true; nw.postMessage({ type: "SKIP_WAITING" }); } });
        });
      });
      navigator.serviceWorker.addEventListener("controllerchange", () => { if (state.pendingReload) location.reload(); });
    } catch (err) { console.warn("sw", err); }
  });
}

setStatus("loading", "Starting…");
keyboardInset();
db.start();
perf.boot.scriptMs = Math.round(performance.now());
