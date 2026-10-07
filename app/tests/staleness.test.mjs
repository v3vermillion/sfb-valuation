import { test } from "node:test";
import assert from "node:assert/strict";
import { AMBER_DAYS, RED_DAYS, daysSince, stalenessLevel, stalenessText } from "../public/js/staleness.js";

const NOW = Date.UTC(2026, 9, 7, 15, 30);   // 2026-10-07 15:30 UTC, a weekday afternoon at the food bank
const daysAgo = (n) => new Date(NOW - n * 86_400_000).toISOString().slice(0, 10);

test("thresholds are the ones the design names: amber at 14 days, red at 45", () => {
  assert.equal(AMBER_DAYS, 14);
  assert.equal(RED_DAYS, 45);
});

test("daysSince counts whole UTC days from the snapshot's price date", () => {
  assert.equal(daysSince("2026-10-07", NOW), 0);
  assert.equal(daysSince("2026-10-06", NOW), 1);
  assert.equal(daysSince("2026-09-23", NOW), 14);
  assert.equal(daysSince("2026-08-23", NOW), 45);
  assert.equal(daysSince("2026-10-08", NOW), -1);                       // a phone clock behind the pipeline: never stale
  assert.equal(daysSince("2026-10-07", new Date(NOW)), 0);              // Date or epoch ms both work
  assert.equal(daysSince("2026-09-23T04:05:06Z", NOW), 14);             // a full timestamp is read by its date part
  assert.equal(daysSince("  2026-09-23 ", NOW), 14);
});

test("daysSince is null for anything that is not a date", () => {
  for (const bad of [null, undefined, "", "soon", "2026-13-01", "2026-02-31", "20260923", 42, {}]) assert.equal(daysSince(bad, NOW), null, String(bad));
  assert.equal(daysSince("2026-09-23", Number.NaN), null);
  assert.equal(daysSince("2026-09-23", "yesterday"), null);
});

test("stalenessLevel: fresh below 14 days, amber from 14, red from 45", () => {
  assert.equal(stalenessLevel(daysAgo(0), NOW), "fresh");
  assert.equal(stalenessLevel(daysAgo(13), NOW), "fresh");
  assert.equal(stalenessLevel(daysAgo(14), NOW), "amber");
  assert.equal(stalenessLevel(daysAgo(30), NOW), "amber");
  assert.equal(stalenessLevel(daysAgo(44), NOW), "amber");
  assert.equal(stalenessLevel(daysAgo(45), NOW), "red");
  assert.equal(stalenessLevel(daysAgo(400), NOW), "red");
});

test("stalenessLevel: a date in the future, a missing date or garbage never raises a banner", () => {
  assert.equal(stalenessLevel(daysAgo(-3), NOW), "fresh");
  assert.equal(stalenessLevel("", NOW), "fresh");
  assert.equal(stalenessLevel(null, NOW), "fresh");
  assert.equal(stalenessLevel("not a date", NOW), "fresh");
});

test("stalenessLevel defaults `now` to the clock", () => {
  const today = new Date().toISOString().slice(0, 10);
  assert.equal(stalenessLevel(today), "fresh");
  assert.equal(stalenessLevel("2000-01-01"), "red");
});

test("stalenessText says it in plain words and is empty when fresh", () => {
  assert.equal(stalenessText("fresh", 3), "");
  assert.equal(stalenessText("amber", 14), "Prices are 14 days old");
  assert.equal(stalenessText("amber", 30), "Prices are 30 days old");
  assert.equal(stalenessText("red", 45), "Prices are 45 days old — values may be out of date");
  assert.equal(stalenessText("red", 1), "Prices are 1 day old — values may be out of date");   // grammar holds for any count
  assert.equal(stalenessText("amber", "16"), "Prices are 16 days old");                         // tolerant of a string count
  assert.equal(stalenessText("amber", undefined), "Prices are 0 days old");                     // never throws, never NaN
  assert.equal(stalenessText("bogus", 99), "");
});
