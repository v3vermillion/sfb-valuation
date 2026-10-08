// audit-lib.mjs — in-page accessibility audit used by shots.mjs (runs inside the browser via page.evaluate).
export const AUDIT_JS = () => {
  // resolve any CSS colour (oklch, color-mix, …) to sRGB through a canvas, then WCAG relative luminance
  const cv = document.createElement("canvas"); cv.width = cv.height = 1; const cx = cv.getContext("2d", { willReadFrequently: true });
  const paintOver = (base, c) => { cx.fillStyle = base; cx.fillRect(0, 0, 1, 1); cx.fillStyle = c; cx.fillRect(0, 0, 1, 1); return Array.from(cx.getImageData(0, 0, 1, 1).data); };
  const toRgb = (c) => paintOver("#fff", c);
  const isOpaque = (c) => { const a = paintOver("#fff", c), b = paintOver("#000", c); return a[0] === b[0] && a[1] === b[1] && a[2] === b[2]; };
  // a colour the canvas cannot parse leaves fillStyle unchanged, which would silently score it as the previous colour:
  // detect that with two different sentinels and keep such text out of the contrast check (reported instead)
  const parses = (c) => { cx.fillStyle = "#010203"; cx.fillStyle = c; const a = cx.fillStyle; cx.fillStyle = "#040506"; cx.fillStyle = c; return !(a === "#010203" && cx.fillStyle === "#040506"); };
  const lum = (c) => { const [r, g, b] = Array.from(toRgb(c)).slice(0, 3).map((v) => { v = v / 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };

  const bgOf = (el) => { let e = el; while (e) { const cs = getComputedStyle(e); const bg = cs.backgroundColor; if (bg && bg !== "transparent" && (!parses(bg) || isOpaque(bg))) return bg; if (cs.backgroundImage && cs.backgroundImage !== "none") return null; e = e.parentElement; } return getComputedStyle(document.body).backgroundColor; };
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && r.bottom > 0 && r.top < innerHeight; };
  const out = { controls: [], smallTargets: [], smallText: [], lowContrast: [] };
  const unparsed = new Map();
  for (const el of document.querySelectorAll("button, a, input, [role=button], [role=switch]")) {
    if (!visible(el)) continue;
    const name = el.getAttribute("aria-label") || el.textContent.trim() || el.getAttribute("placeholder") || (el.labels && el.labels[0]?.textContent) || "";
    const r = el.getBoundingClientRect();
    const id = el.id || el.className || el.tagName;
    out.controls.push({ id, name, w: Math.round(r.width), h: Math.round(r.height) });
    if (!name) out.controls[out.controls.length - 1].missingName = true;
    if ((r.width < 44 || r.height < 44) && !(el.tagName === "A" && el.classList.contains("skip"))) out.smallTargets.push({ id, w: Math.round(r.width), h: Math.round(r.height) });
  }
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const t = walker.currentNode; if (!t.textContent.trim()) continue;
    const el = t.parentElement; if (!el || seen.has(el) || !visible(el)) continue; seen.add(el);
    const cs = getComputedStyle(el); const size = parseFloat(cs.fontSize);
    const tag = `${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]}`;
    if (size < 13) out.smallText.push({ tag, size, text: t.textContent.trim().slice(0, 30) });
    const bg = bgOf(el);
    const bad = [cs.color, bg].filter((c) => c && !parses(c));
    if (bad.length) { for (const c of bad) unparsed.set(c, tag); continue; }
    const l1 = lum(cs.color), l2 = bg ? lum(bg) : null;
    if (l1 != null && l2 != null) { const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); const bold = parseInt(cs.fontWeight) >= 600; const large = size >= 24 || (size >= 18.66 && bold); const need = large ? 3 : 4.5; if (ratio < need) out.lowContrast.push({ tag, ratio: +ratio.toFixed(2), need, size, fg: cs.color, bg, text: t.textContent.trim().slice(0, 30) }); }
  }
  if (unparsed.size) out.unparsedColors = [...unparsed].map(([color, tag]) => ({ color, tag }));
  return out;
};

// ---- page errors vs browser notes (used by shots.mjs; pure, tested in tests/audit-lib.test.mjs)
// A real page error is an uncaught exception, an unhandled promise rejection, or a console.error that is not on the list
// below. The list holds only exact messages a browser itself logs about markup it deliberately does not support, each
// with the reason it is harmless; they are reported as notes, never counted as errors. Anything else stays an error.
export const BROWSER_NOTES = [
  {
    match: /^Viewport argument key "interactive-widget" not recognized and ignored\.?$/,
    why: "WebKit does not implement the viewport meta's interactive-widget key and says so once per page. The key is kept on purpose: it makes Chrome on Android shrink the layout viewport above the keyboard (so 92dvh sheets and the fixed dock stay visible); Safari ignores it and the app's visualViewport keyboard inset (--kb) covers iOS.",
  },
];

/** A console.error's text -> the matching browser note ({ message, why }), or null when it must count as a page error. */
export function browserNote(text) {
  const t = String(text ?? "").trim();
  const n = BROWSER_NOTES.find((b) => b.match.test(t));
  return n ? { message: t, why: n.why } : null;
}

/** Fold per-screen notes into one entry per message: { message, why, pages: [screen, ...] }. */
export function foldNotes(pages) {
  const by = new Map();
  for (const p of pages) for (const n of p.notes || []) {
    const e = by.get(n.message) || { message: n.message, why: n.why, pages: [] };
    if (!e.pages.includes(p.page)) e.pages.push(p.page);
    by.set(n.message, e);
  }
  return [...by.values()];
}
