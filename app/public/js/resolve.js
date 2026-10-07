// resolve.js — turns a scanned/typed code or a chosen search hit into a priced resolution, following
// docs/WORKFLOW.md: exact item (incl. retired UPCs) → store-printed price label → produce PLU →
// equivalent value (basis item shown) → closest match (flagged). A resolution always carries a price unless
// the code is simply unknown, in which case the UI offers the name search and the live Walmart check.

import { classifyCode, formatGtin, toGtin14 } from "./barcode.js";

export const KIND_LABEL = {
  exact: "Exact item",
  closest: "Closest match",
  "store-label": "Store price label",
  plu: "Produce code",
  equivalent: "Equivalent value",
  live: "Live Walmart price",
  unknown: "Not in database",
  "not-ready": "Prices still loading",
};

export function kindLabel(res) {
  if (res.kind === "exact" && res.item?.retired) return "Exact item · older barcode";
  return KIND_LABEL[res.kind] || res.kind;
}

/** Walmart names usually already start with the brand ("Great Value Peanut Butter…"); never print it twice. */
export function splitTitle(item) {
  const brand = (item.brand || "").trim(), name = (item.name || "").trim();
  if (!brand) return { pre: "", brand: "", rest: name };
  const i = name.toLowerCase().indexOf(brand.toLowerCase());
  if (i >= 0) return { pre: name.slice(0, i), brand: name.slice(i, i + brand.length), rest: name.slice(i + brand.length) };   // "(2 pack) Great Value …"
  return { pre: "", brand, rest: ` ${name}` };
}
export function titleOf(item) {
  const { pre, brand, rest } = splitTitle(item);
  return (pre + brand + rest).trim();
}

export function sizeText(item) {
  if (item.size && item.unit) return `${fmtNum(item.size)} ${item.unit}`;
  return "";
}

export function fmtNum(n) {
  if (n == null || Number.isNaN(n)) return "";
  const r = Math.round(n * 100) / 100;
  return Number.isInteger(r) ? String(r) : String(r).replace(/0+$/, "");
}

/** Resolution from a search hit the volunteer tapped. */
export function fromItem(item, { closest = false, query = "", dropped = [] } = {}) {
  return {
    kind: closest ? "closest" : "exact",
    code: item.upc, gtin: item.upc, item, others: [],
    priceCents: item.priceCents,
    unit: item.basis === "lb" ? "lb" : "each",
    title: titleOf(item),
    key: item.upc ? `g:${item.upc}` : `r:${item.rank}`,
    query, dropped,
  };
}

/** Pick the listing for a barcode: the one whose Walmart id the caller wants, else the primary (first). */
function pickListing(items, preferId) {
  if (preferId != null) { const i = items.findIndex((it) => String(it.id) === String(preferId)); if (i > 0) return [items[i], ...items.filter((_, k) => k !== i)]; }
  return items;
}

/**
 * Resolve any code (scanned or typed digits). Returns null when the text isn't a code at all.
 * @param {{lookupPlu:Function, lookupUpc:Function}} db
 * @param {object} [opts] scanned: the code came from the camera (no typed-input heuristics); preferId: Walmart id to prefer among listings
 */
export async function resolveCode(db, raw, format, { scanned = false, preferId = null } = {}) {
  const cls = classifyCode(raw, format, { scanned });
  if (cls.kind === "text") return null;

  if (cls.kind === "plu") {
    const e = await db.lookupPlu(cls.plu);
    if (e?.notReady) return { kind: "not-ready", code: cls.digits, title: "Prices are still loading", priceCents: null, unit: "each", key: `n:${cls.digits}` };
    if (e) {
      return {
        kind: "plu", code: cls.digits, plu: cls, entry: e, item: e.item || null,
        priceCents: Math.round(e.price * 100), unit: e.unit === "lb" ? "lb" : "each",
        title: (cls.organic ? "Organic " : "") + e.name, key: `p:${cls.digits}`,
      };
    }
    return { kind: "unknown", code: cls.digits, codeType: "PLU", title: `Produce code ${cls.digits}`, priceCents: null, unit: "each", key: `u:${cls.digits}` };
  }

  if (cls.kind === "store-label") {
    if (cls.priceCents > 0) {
      return {
        kind: "store-label", code: cls.digits, label: cls, priceCents: cls.priceCents, unit: "each",
        title: "Store-priced item (meat, deli, bakery or weighed produce)", key: `l:${cls.digits}`,
      };
    }
    // a 2-prefix code with no price encoded is a manufacturer's variable-measure code: try the catalog, never show $0.00
    const g = toGtin14(cls.digits, undefined, { scanned: true });
    const r = g ? await db.lookupUpc(g.key) : null;
    if (r?.notReady) return { kind: "not-ready", code: cls.digits, title: "Prices are still loading", priceCents: null, unit: "each", key: `n:${cls.digits}` };
    if (r?.items?.length) { const [item, ...others] = pickListing(r.items, preferId); return { ...fromItem(item), others, gtin: g.gtin14, code: cls.digits, scanned: g }; }
    return { kind: "unknown", code: cls.digits, gtin: g?.gtin14 || null, codeType: "store-label", noPrice: true, title: `Label ${formatGtin(cls.digits)}`, priceCents: null, unit: "each", key: `u:${cls.digits}` };
  }

  // GTIN (try the alternate 8-digit interpretation too, so UPC-E and EAN-8 keyed rows are both found)
  let r = await db.lookupUpc(cls.key);
  if (r?.notReady) return { kind: "not-ready", code: cls.digits, gtin: cls.gtin14, title: "Prices are still loading", priceCents: null, unit: "each", key: `n:${cls.gtin14}` };
  let gtin = cls.gtin14;
  if (!r?.items?.length && !r?.equivalent && cls.altKey) {
    const r2 = await db.lookupUpc(cls.altKey);
    if (r2?.items?.length || r2?.equivalent) { r = r2; gtin = String(cls.altKey).padStart(14, "0"); }
  }
  if (r?.items?.length) {
    const [item, ...others] = pickListing(r.items, preferId);
    return { ...fromItem(item), others, gtin, code: cls.digits, scanned: cls };
  }
  if (r?.equivalent) {
    const e = r.equivalent;
    const title = [e.brand, e.name].filter(Boolean).join(" ") + (e.quantity ? `, ${e.quantity}` : "");
    return { kind: "equivalent", code: cls.digits, gtin, equiv: e, priceCents: e.estCents, unit: "each", title, key: `e:${gtin}`, scanned: cls };
  }
  return {
    kind: "unknown", code: cls.digits, gtin: cls.gtin14, codeType: cls.type, checkOk: cls.checkOk,
    title: `Barcode ${formatGtin(cls.gtin14)}`, priceCents: null, unit: "each", key: `u:${cls.gtin14}`, scanned: cls,
  };
}

/** Human notes that explain the price's provenance; shown under the title. */
export function notesFor(res, ctx = {}) {
  const notes = [];
  const it = res.item;
  if (res.kind === "closest") {
    notes.push({ tone: "warn", text: `Closest match. Nothing matched all of “${res.query}”${res.dropped?.length ? ` — “${res.dropped.join(" ")}” was ignored` : ""}. Check the type and size against the item in your hand.` });
  }
  if (res.kind === "equivalent") {
    const e = res.equiv;
    notes.push({ tone: "equiv", text: `Not sold at Walmart. Valued at the price of the closest Walmart equivalent by type and size (${e.confidence === "high" ? "close match" : e.confidence === "medium" ? "fair match" : "rough match"}).` });
    if (!e.basis) notes.push({ tone: "warn", text: "The Walmart item this estimate was based on is no longer listed, so treat the value as approximate." });
  }
  if (res.kind === "store-label") {
    notes.push({ tone: "", text: "This barcode was printed by a store scale and carries the price itself. It isn't a catalog item, so the price is read straight from the label." });
    if (res.label.checkOk === false) notes.push({ tone: "warn", text: "The barcode's check digit doesn't match, so a digit may have been mistyped. Compare with the printed price on the label." });
    else if (!res.label.verified) notes.push({ tone: "warn", text: "The price digits couldn't be verified. Compare with the printed price on the label." });
  }
  if (res.kind === "plu") {
    if (res.entry.source === "typical") notes.push({ tone: "warn", text: "No produce listing matched this code in the latest snapshot, so this is the typical Walmart price kept with the app." });
    if (res.plu.organic) notes.push({ tone: "", text: "Organic (9-prefix). Priced as the conventional item." });
  }
  if (res.kind === "not-ready") {
    notes.push({ tone: "warn", text: "The price database is still opening on this phone. Try the code again in a moment." });
  }
  if (res.kind === "unknown") {
    if (res.codeType === "PLU") notes.push({ tone: "warn", text: "This produce code isn't in the app's list. Type the produce name to value it." });
    else if (res.noPrice) notes.push({ tone: "warn", text: "This label carries no price and isn't in the catalog. Read the printed price from the label, or type the name to find the closest item." });
    else {
      notes.push({ tone: "warn", text: "This barcode isn't in the saved database and has no equivalent on file. Type the name and size from the label to find the closest item." });
      if (res.checkOk === false) notes.push({ tone: "warn", text: "The check digit doesn't match, so a digit may have been mistyped." });
    }
  }
  if (it) {
    if (it.retired) notes.push({ tone: "", text: "This is an older barcode for the item. Walmart has since reissued it; the price shown is the current one." });
    if (it.carried) notes.push({ tone: "", text: `Walmart didn't list a price when checked on ${ctx.priceDateLong || "the last check"}, so the previous price was carried over.` });
    if (it.promo) notes.push({ tone: "", text: "This was a Rollback or sale price when checked." });
    if (it.unavailable) notes.push({ tone: "", text: "Out of stock online when checked. The price is the last one listed." });
    if (it.sizeConflict) notes.push({ tone: "", text: "Walmart's listing shows two sizes. The one in the title is used." });
    if (!it.primary && (res.kind === "exact" || res.kind === "closest")) notes.push({ tone: "", text: "Walmart lists this barcode more than once; this is one of the other listings." });
  }
  return notes;
}
