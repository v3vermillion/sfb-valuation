// staleness.js — how old are the prices on this phone, in a volunteer's words.
// Pure functions, no DOM: app.js renders the banner, tests/staleness.test.mjs pins the thresholds.
// The pipeline stamps every snapshot with priceDate (YYYY-MM-DD, UTC). A snapshot is "amber" from 14 days
// and "red" from 45 days: amber means the phone should be updated when it is next online, red means the
// values may no longer match the shelf and the volunteer should update before trusting them.

export const AMBER_DAYS = 14;
export const RED_DAYS = 45;

const DAY_MS = 86_400_000;

/** Whole days between a YYYY-MM-DD price date (UTC) and `now`; null when the date is missing or not a date. */
export function daysSince(priceDateISO, now = Date.now()) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(priceDateISO ?? "").trim());
  if (!m) return null;
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const d = new Date(t);
  // reject 2026-02-31 and friends: Date.UTC silently rolls them over
  if (d.getUTCFullYear() !== Number(m[1]) || d.getUTCMonth() !== Number(m[2]) - 1 || d.getUTCDate() !== Number(m[3])) return null;
  const nowMs = now instanceof Date ? now.getTime() : Number(now);
  if (!Number.isFinite(nowMs)) return null;
  return Math.floor((nowMs - t) / DAY_MS);
}

/** "fresh" | "amber" (>= 14 days) | "red" (>= 45 days). A missing or unreadable date is "fresh": nothing to say about it. */
export function stalenessLevel(priceDateISO, now = Date.now()) {
  const days = daysSince(priceDateISO, now);
  if (days == null || days < AMBER_DAYS) return "fresh";
  return days >= RED_DAYS ? "red" : "amber";
}

/** The banner's headline for a level; empty when fresh. Plain words, no jargon. */
export function stalenessText(level, days) {
  if (level !== "amber" && level !== "red") return "";
  const n = Math.max(0, Math.floor(Number(days) || 0));
  const age = `${n} ${n === 1 ? "day" : "days"} old`;
  return level === "red" ? `Prices are ${age} — values may be out of date` : `Prices are ${age}`;
}
