import { test } from "node:test";
import assert from "node:assert/strict";
import { BROWSER_NOTES, browserNote, foldNotes } from "../tools/audit-lib.mjs";

test("WebKit's interactive-widget viewport message is a browser note, with the reason the key is kept", () => {
  const n = browserNote('Viewport argument key "interactive-widget" not recognized and ignored.');
  assert.ok(n);
  assert.match(n.why, /Android/);
  assert.ok(browserNote('  Viewport argument key "interactive-widget" not recognized and ignored  '), "surrounding space and a missing full stop do not matter");
});

test("anything else stays a page error: other viewport keys, our own errors, empty text", () => {
  for (const t of [
    'Viewport argument key "foo" not recognized and ignored.',
    'Viewport argument key "interactive-widget" not recognized and ignored. TypeError: x is undefined',
    "TypeError: undefined is not an object (evaluating 'el.sheet.open')",
    "Unhandled promise rejection: download failed",
    "",
    null,
  ]) assert.equal(browserNote(t), null, String(t));
  for (const b of BROWSER_NOTES) { assert.ok(b.match instanceof RegExp); assert.ok(b.match.source.startsWith("^") && b.match.source.endsWith("$"), "exact messages only"); }
});

test("notes fold into one entry per message with the screens that logged it", () => {
  const msg = 'Viewport argument key "interactive-widget" not recognized and ignored.';
  const why = browserNote(msg).why;
  const folded = foldNotes([
    { page: "webkit-light-390x844", notes: [{ message: msg, why }] },
    { page: "webkit-light-390x844-1-home", lowContrast: [] },
    { page: "webkit-dark-390x844", errors: ["boom"], notes: [{ message: msg, why }] },
  ]);
  assert.deepEqual(folded, [{ message: msg, why, pages: ["webkit-light-390x844", "webkit-dark-390x844"] }]);
  assert.deepEqual(foldNotes([]), []);
});
