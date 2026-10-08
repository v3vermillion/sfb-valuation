"""Acceptance gates: every gate passes and holds on small synthetic snapshots; finalize; publish + history."""
import json, unittest
from unittest import mock

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from _fixtures import StoreCase, FakeWM, snapshot_rows, make_state, make_stats, row, RUN_ID, FOOD_ID, PETS_ID
import crawler.wm as wm_mod


class Gates(StoreCase, unittest.TestCase):
    def setUp(self):
        self.setup_store()
        self.rows = snapshot_rows()
        self.write_candidate(self.rows)

    def tearDown(self):
        self.teardown_store()

    # ---- the happy path and the gates.json contract
    def test_all_deterministic_gates_pass_and_review_is_pending(self):
        wm = FakeWM(self.rows)
        self.assertEqual(self.qa.check(wm=wm), "review")
        g = self.gates()
        self.assertEqual(set(g) >= {"run_id", "gates", "passed_deterministic", "status", "config_hash", "checked", "transient", "thresholds"}, True)
        self.assertEqual(g["run_id"], RUN_ID); self.assertTrue(g["passed_deterministic"]); self.assertEqual(g["status"], "review")
        self.assertEqual(len(g["config_hash"]), 64); self.assertFalse(g["transient"])
        for name in self.qa.DETERMINISTIC:
            x = g["gates"][name]
            self.assertTrue(x["pass"], name); self.assertEqual(set(x), {"pass", "value", "threshold", "detail"})
        self.assertIsNone(g["gates"]["sample_review"]["pass"]); self.assertEqual(g["gates"]["sample_review"]["threshold"], 0.05)
        self.assertEqual(g["gates"]["live_match"]["value"], 1.0); self.assertEqual(g["gates"]["sentinels"]["value"], 0)
        self.assertEqual(g["gates"]["size_parse"]["value"], 1.0); self.assertEqual(g["gates"]["unit_outliers"]["value"], 0.0)
        self.assertEqual(g["gates"]["price_drift"]["detail"], "no previous snapshot")
        self.assertEqual(self.state()["status"], "built")
        report = (self.qa.CAND / "report.md").read_text()
        self.assertIn("Status: **review**", report); self.assertIn("PASS live_match", report); self.assertIn("PENDING sample_review", report)
        sample = [json.loads(l) for l in (self.qa.CAND / "review-sample.jsonl").read_text().splitlines()]
        self.assertEqual(len(sample), len(self.rows))
        self.assertEqual(sample[0]["category"], "Canned & Jarred", "sample rows carry the category name")
        # 181 eligible rows -> 10 calls of at most 20 ids
        self.assertEqual(len(wm.requested), 10); self.assertTrue(all(len(c) <= 20 for c in wm.requested))

    def test_review_not_required_returns_ready(self):
        self.write_gates(sample_review={"required": False})
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows)), "ready")
        g = self.gates()
        self.assertTrue(g["gates"]["sample_review"]["pass"]); self.assertIn("not required", g["gates"]["sample_review"]["detail"])
        self.assertTrue(self.qa.publish())

    def test_check_removes_stale_artifacts_from_a_previous_run(self):
        self.verdict(run_id="older-run")
        (self.qa.CAND / "report.md").write_text("old")
        self.qa.check(wm=FakeWM(self.rows))
        self.assertFalse((self.qa.CAND / "review-verdict.json").exists())
        self.assertNotEqual((self.qa.CAND / "report.md").read_text(), "old")

    def test_config_hash_follows_the_config_files(self):
        h1 = self.qa.config_hash()
        self.write_gates(live_match_min=0.9)
        h2 = self.qa.config_hash()
        self.assertNotEqual(h1, h2); self.assertEqual(h2, self.qa.config_hash())
        self.sent.write_text(json.dumps({"sentinels": []}))
        self.assertNotEqual(h2, self.qa.config_hash())

    # ---- sentinels
    def test_missing_sentinel_holds(self):
        rows = [r for r in self.rows if r["id"] != 15544057]
        self.write_candidate(rows)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "hold")
        g = self.gates()
        self.assertFalse(g["gates"]["sentinels"]["pass"]); self.assertEqual(g["gates"]["sentinels"]["value"], 1)
        self.assertIn("gv corn", g["gates"]["sentinels"]["detail"]); self.assertFalse(g["transient"])
        self.assertEqual(self.state()["status"], "needs_review")
        self.assertIn("MISSING: gv corn", (self.qa.CAND / "report.md").read_text())

    def test_sentinel_with_zero_price_does_not_count(self):
        rows = [dict(r, price=0) if r["id"] == 15544057 else r for r in self.rows]
        self.write_candidate(rows)
        self.qa.check(wm=FakeWM(rows))
        self.assertFalse(self.gates()["gates"]["sentinels"]["pass"])

    def test_null_threshold_is_measure_only(self):
        rows = [r for r in self.rows if r["id"] != 15544057]
        self.write_candidate(rows)
        self.write_gates(sentinel_misses_max=None)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "review")
        x = self.gates()["gates"]["sentinels"]
        self.assertTrue(x["pass"]); self.assertEqual(x["value"], 1); self.assertIsNone(x["threshold"]); self.assertTrue(x["detail"].startswith("measure-only"))

    # ---- live match
    def test_live_mismatches_hold_and_are_reported(self):
        changed = {r["id"]: round(r["price"] * 1.5, 2) for r in self.rows[:20]}   # 20 of 181 eligible rows -> 89%
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows, prices=changed)), "hold")
        g = self.gates(); x = g["gates"]["live_match"]
        self.assertFalse(x["pass"]); self.assertLess(x["value"], 0.97); self.assertAlmostEqual(x["value"], 161 / 181, places=3)
        self.assertIn("within 5%", x["detail"])
        live = g["extras"]["live"]
        self.assertEqual(live["checked"], 181); self.assertEqual(len(live["examples"]), 20)
        self.assertEqual(live["examples"][0]["live"], changed[live["examples"][0]["id"]])
        self.assertIn("Live price differences", (self.qa.CAND / "report.md").read_text())

    def test_items_walmart_no_longer_knows_count_as_mismatches(self):
        missing = [r["id"] for r in self.rows[:10]]
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows, missing=missing)), "hold")
        x = self.gates()["gates"]["live_match"]
        self.assertAlmostEqual(x["value"], 171 / 181, places=3); self.assertIn("missing live: 10", x["detail"])

    def test_small_differences_count_as_within_5pct_only(self):
        changed = {r["id"]: round(r["price"] + 0.02, 2) for r in self.rows[:3]}
        self.qa.check(wm=FakeWM(self.rows, prices=changed))
        live = self.gates()["extras"]["live"]
        self.assertEqual(live["exact"], 178); self.assertEqual(live["within_5pct"], 181)

    def test_live_check_not_run_without_credentials_holds(self):
        self.assertEqual(self.qa.check(), "hold")
        x = self.gates()["gates"]["live_match"]
        self.assertFalse(x["pass"]); self.assertIsNone(x["value"]); self.assertIn("WM_CONSUMER_ID", x["detail"])
        self.assertFalse(self.gates()["transient"], "a missing secret is not transient")
        self.write_gates(live_match_min=None)
        self.assertEqual(self.qa.check(), "review")
        self.assertTrue(self.gates()["gates"]["live_match"]["pass"])

    def test_live_check_builds_a_client_when_credentials_exist(self):
        fake = FakeWM(self.rows)
        with mock.patch.dict("os.environ", {"WM_CONSUMER_ID": "cid", "WM_PRIVATE_KEY": "key"}), \
             mock.patch("crawler.wm.Walmart", return_value=fake) as ctor:
            self.assertEqual(self.qa.check(), "review")
        ctor.assert_called_once(); self.assertEqual(fake.calls, 10)

    def test_live_check_unavailable_is_a_transient_hold(self):
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows, fail_after=0)), "hold")
        g = self.gates(); x = g["gates"]["live_match"]
        self.assertFalse(x["pass"]); self.assertIsNone(x["value"]); self.assertIn("unavailable", x["detail"]); self.assertIn("Throttled", x["detail"])
        self.assertTrue(g["transient"]); self.assertIn("transient hold", (self.qa.CAND / "report.md").read_text())
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows, fail_after=0, exc=requests.ConnectionError("reset"))), "hold")
        self.assertIn("ConnectionError", self.gates()["gates"]["live_match"]["detail"])

    def test_live_check_uses_a_partial_result_when_most_rows_were_checked(self):
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows, fail_after=7)), "review")   # 140 of 181 rows checked
        x = self.gates()["gates"]["live_match"]
        self.assertTrue(x["pass"]); self.assertEqual(x["value"], 1.0); self.assertIn("stopped early", x["detail"]); self.assertIn("140/", x["detail"].replace("140/140", "140/"))
        self.assertFalse(self.gates()["transient"])

    def test_transient_flag_needs_every_other_gate_to_pass(self):
        rows = [r for r in self.rows if r["id"] != 15544057]
        self.write_candidate(rows)
        self.qa.check(wm=FakeWM(rows, fail_after=0))
        self.assertFalse(self.gates()["transient"])

    def test_live_sample_selection(self):
        rows = self.rows + [row(5000, flags=["promo_price"]), row(5001, flags=["carried_over"]), row(5002, upc=None),
                            row(5003, stock="Out of stock"), row(5004, primary=False)]
        ids = {r["id"] for r in self.qa.live_sample_rows(rows, 1000, "seed")}
        self.assertEqual(len(ids), 181); self.assertTrue(ids.isdisjoint({5000, 5001, 5002, 5003, 5004}))
        with_carried = {r["id"] for r in self.qa.live_sample_rows(rows, 1000, "seed", include_carried=True)}
        self.assertEqual(with_carried, ids | {5001}, "the audit keeps carried-over rows; promo/out-of-stock/no-UPC stay out")
        a = [r["id"] for r in self.qa.live_sample_rows(rows, 50, RUN_ID)]
        b = [r["id"] for r in self.qa.live_sample_rows(rows, 50, RUN_ID)]
        c = [r["id"] for r in self.qa.live_sample_rows(rows, 50, "other")]
        self.assertEqual(a, b); self.assertEqual(len(a), 50); self.assertNotEqual(a, c)
        self.write_gates(live_sample=40)
        wm = FakeWM(self.rows)
        self.qa.check(wm=wm)
        self.assertEqual(sum(len(c) for c in wm.requested), 40)

    # ---- size parse
    def test_size_parse_below_threshold_holds(self):
        rows = [dict(r, size=None, unit=None, base_qty=None, base_unit=None, unit_price=None, flags=["no_size"]) if i < 13 else r
                for i, r in enumerate(self.rows)]       # 13 of 121 Food rows unparsed -> 89%
        self.write_candidate(rows)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "hold")
        x = self.gates()["gates"]["size_parse"]
        self.assertFalse(x["pass"]); self.assertAlmostEqual(x["value"], 108 / 121, places=3); self.assertIn("108/121", x["detail"])
        self.write_gates(size_parse_min=None)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "review")

    def test_size_parse_counts_rows_sized_by_their_basis(self):
        # sold by the pound or sold each: the basis is the size, so these are not parse failures
        rows = [dict(r, size=None, unit=None, base_qty=None, base_unit=None, unit_price=None,
                     basis="lb" if i < 5 else r.get("basis"), flags=(["sold_each", "no_size"] if 5 <= i < 13 else ["no_size"]))
                if i < 15 else r for i, r in enumerate(self.rows)]
        self.write_candidate(rows)
        self.qa.check(wm=FakeWM(rows))
        x = self.gates()["gates"]["size_parse"]
        self.assertAlmostEqual(x["value"], 119 / 121, places=3)
        self.assertIn("5 sold by the pound, 8 sold each", x["detail"])

    def test_size_parse_ignores_other_departments(self):
        rows = [dict(r, base_qty=None, unit_price=None) if r["dept"] == "Pets" else r for r in self.rows]
        self.write_candidate(rows)
        self.qa.check(wm=FakeWM(rows))
        self.assertEqual(self.gates()["gates"]["size_parse"]["value"], 1.0)

    # ---- unit outliers
    def test_unit_outliers_hold(self):
        rows = [dict(r, unit_price=r["unit_price"] * 50) if i < 2 else r for i, r in enumerate(self.rows)]
        self.write_candidate(rows)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "hold")
        g = self.gates(); x = g["gates"]["unit_outliers"]
        self.assertFalse(x["pass"]); self.assertAlmostEqual(x["value"], 2 / 181, places=4)
        self.assertEqual({o["id"] for o in g["extras"]["unit_outliers"]}, {1000, 1001})
        self.assertIn("Unit-price outliers", (self.qa.CAND / "report.md").read_text())
        self.write_gates(unit_outliers_max=None)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "review")

    def test_unit_outliers_need_a_group_of_50(self):
        rows = [dict(r, unit_price=r["unit_price"] * 50) if r["id"] == 2000 else r for r in self.rows]   # Pets group has 60 rows
        share, total, out = self.qa.unit_outlier_stats(rows, 50)
        self.assertEqual([o["id"] for o in out], [2000]); self.assertEqual(total, 181)
        share, total, out = self.qa.unit_outlier_stats(rows, 61)
        self.assertEqual(out, [])
        self.assertEqual(self.qa.unit_outlier_stats([], 50), (0.0, 0, []))

    # ---- departments complete
    def test_department_with_nothing_kept_holds(self):
        rows = [r for r in self.rows if r["dept"] != "Pets"]
        self.write_candidate(rows)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "hold")
        x = self.gates()["gates"]["departments_complete"]
        self.assertFalse(x["pass"]); self.assertEqual(x["value"], 1); self.assertIn("Pets: 0 items kept", x["detail"])

    def test_unfinished_department_holds(self):
        st = make_state(); st["departments"][1]["status"] = "crawling"
        self.write_candidate(self.rows, state=st)
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows)), "hold")
        self.assertIn("Pets: status crawling", self.gates()["gates"]["departments_complete"]["detail"])

    def test_department_dropped_from_scope_is_ignored(self):
        st = make_state(); st["departments"].append({"id": "999", "name": "Gone", "status": "pending", "pages": 0, "items": 0})
        self.write_candidate(self.rows, state=st)
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows)), "review")
        self.assertIn("2 departments checked", self.gates()["gates"]["departments_complete"]["detail"])

    def test_sizing_comparison(self):
        self.store.write_json(self.qa.SIZING, {FOOD_ID: {"name": "Food", "total_pages": 20}, PETS_ID: {"name": "Pets", "total_pages": 4}})
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows)), "hold")       # Food crawled 10 pages of 20 sized
        x = self.gates()["gates"]["departments_complete"]
        self.assertFalse(x["pass"]); self.assertIn("Food: 10 pages vs 20 sized (-50%)", x["detail"]); self.assertIn("sizing used", x["detail"])
        self.store.write_json(self.qa.SIZING, {FOOD_ID: {"total_pages": 12}, PETS_ID: {"total_pages": 4}})
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows)), "review")     # -17% is inside ±30%
        self.store.write_json(self.qa.SIZING, {FOOD_ID: {"total_pages": 20}})
        self.write_gates(dept_size_tolerance=None)
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows)), "review", "null tolerance skips the page comparison")
        rows = [r for r in self.rows if r["dept"] != "Pets"]
        self.write_candidate(rows)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "hold", "but an empty department still fails")

    # ---- against the published snapshot
    def test_gates_against_previous_snapshot(self):
        prev = snapshot_rows(n_food=200, n_pets=60)
        self.write_published(prev)
        # same rows -> all three pass
        self.write_candidate(prev)
        self.assertEqual(self.qa.check(wm=FakeWM(prev)), "review")
        g = self.gates()
        self.assertEqual(g["gates"]["item_count"]["value"], 1.0); self.assertEqual(g["gates"]["price_drift"]["value"], 0.0)
        self.assertEqual(g["gates"]["category_counts"]["value"], 0.0)
        # 20% fewer items -> item_count holds (0.8 < 0.9); Food category 201 -> 161 is -20% exactly: within tolerance
        fewer = [r for r in prev if not (1040 <= r["id"] < 1080) and not (2040 <= r["id"] < 2060)]
        self.write_candidate(fewer)
        self.assertEqual(self.qa.check(wm=FakeWM(fewer)), "hold")
        g = self.gates()
        self.assertFalse(g["gates"]["item_count"]["pass"]); self.assertAlmostEqual(g["gates"]["item_count"]["value"], 201 / 261, places=3)
        self.assertTrue(g["gates"]["category_counts"]["pass"])
        # drift: 10 of 261 prices doubled (3.8% > 2%)
        drifted = [dict(r, price=r["price"] * 2) if 1000 <= r["id"] < 1010 else r for r in prev]
        self.write_candidate(drifted)
        self.assertEqual(self.qa.check(wm=FakeWM(drifted)), "hold")
        g = self.gates()
        self.assertFalse(g["gates"]["price_drift"]["pass"]); self.assertAlmostEqual(g["gates"]["price_drift"]["value"], 10 / 261, places=4)
        self.assertEqual(len(g["extras"]["drift"]), 10)
        self.assertIn("Price changes > 50%", (self.qa.CAND / "report.md").read_text())
        # category: Food (201 published rows) down to 160 (-20.4%) while the item count (560 of 601) still passes
        big = snapshot_rows(n_food=200, n_pets=400)
        self.write_published(big)
        cats = [r for r in big if not (1000 <= r["id"] < 1041)]
        self.write_candidate(cats)
        self.assertEqual(self.qa.check(wm=FakeWM(cats)), "hold")
        g = self.gates()
        self.assertFalse(g["gates"]["category_counts"]["pass"]); self.assertTrue(g["gates"]["item_count"]["pass"])
        self.assertAlmostEqual(g["gates"]["category_counts"]["value"], 41 / 201, places=4)
        self.assertEqual(g["extras"]["unstable"], [{"cat": "6", "old": 201, "new": 160}])
        self.assertIn("Category count changes", (self.qa.CAND / "report.md").read_text())
        self.write_gates(category_count_tolerance=None, price_drift_max=None, item_count_min_ratio=None)
        self.assertEqual(self.qa.check(wm=FakeWM(cats)), "review")

    def test_category_gate_ignores_small_categories(self):
        prev = snapshot_rows(n_food=120, n_pets=60)      # every category under 200 rows
        self.write_published(prev)
        cand = [r for r in prev if r["dept"] != "Pets"] + [row(2000, cat="19", dept="Pets")]
        self.write_candidate(cand)
        self.qa.check(wm=FakeWM(cand))
        self.assertTrue(self.gates()["gates"]["category_counts"]["pass"])


class Finalize(StoreCase, unittest.TestCase):
    def setUp(self):
        self.setup_store()
        self.rows = snapshot_rows()
        self.write_candidate(self.rows)
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows)), "review")

    def tearDown(self):
        self.teardown_store()

    def test_pass_verdict_makes_the_candidate_ready(self):
        self.verdict(junk_rate=0.02, junk_examples=[{"id": 1, "why": "x"}], notes="two odd rows")
        self.assertEqual(self.qa.finalize(), "ready")
        g = self.gates(); x = g["gates"]["sample_review"]
        self.assertEqual(g["status"], "ready"); self.assertTrue(x["pass"]); self.assertEqual(x["value"], 0.02)
        self.assertIn("1 examples", x["detail"]); self.assertIn("two odd rows", x["detail"]); self.assertIn("finalized", g)
        self.assertEqual(self.state()["status"], "built"); self.assertFalse(g["transient"])
        self.assertIn("Status: **ready**", (self.qa.CAND / "report.md").read_text())

    def test_fail_verdicts_hold(self):
        self.verdict(status="fail", systematic_junk=True, junk_rate=0.01)
        self.assertEqual(self.qa.finalize(), "hold")
        self.assertIn("systematic junk: yes", self.gates()["gates"]["sample_review"]["detail"])
        self.assertEqual(self.state()["status"], "needs_review"); self.assertFalse(self.gates()["transient"])
        self.verdict(status="pass", junk_rate=0.08)              # the model said pass but the rate is over David's limit
        self.assertEqual(self.qa.finalize(), "hold")
        self.write_gates(sample_review={"max_junk_rate": None})
        self.qa.check(wm=FakeWM(self.rows)); self.verdict(status="pass", junk_rate=0.5)
        self.assertEqual(self.qa.finalize(), "ready", "null max_junk_rate: only systematic junk holds")

    def test_missing_or_stale_verdict_holds(self):
        self.assertEqual(self.qa.finalize(), "hold")
        self.assertIn("no review verdict", self.gates()["gates"]["sample_review"]["detail"])
        self.verdict(run_id="some-other-run")
        self.assertEqual(self.qa.finalize(), "hold")
        self.assertIn("no review verdict", self.gates()["gates"]["sample_review"]["detail"])

    def test_skipped_names_the_missing_secret(self):
        self.verdict(status="skipped", reason="ANTHROPIC_API_KEY missing")
        self.assertEqual(self.qa.finalize(), "hold")
        self.assertIn("ANTHROPIC_API_KEY", self.gates()["gates"]["sample_review"]["detail"]); self.assertFalse(self.gates()["transient"])
        self.write_gates(sample_review={"required": False})
        self.qa.check(wm=FakeWM(self.rows)); self.verdict(status="skipped", reason="ANTHROPIC_API_KEY missing")
        self.assertEqual(self.qa.finalize(), "ready")

    def test_error_is_a_transient_hold(self):
        self.verdict(status="error", reason="HTTP 529: overloaded")
        self.assertEqual(self.qa.finalize(), "hold")
        g = self.gates()
        self.assertTrue(g["transient"]); self.assertIn("overloaded", g["gates"]["sample_review"]["detail"])
        self.write_gates(sample_review={"required": False})
        self.qa.check(wm=FakeWM(self.rows)); self.verdict(status="error", reason="HTTP 529")
        self.assertEqual(self.qa.finalize(), "ready")

    def test_finalize_after_a_deterministic_hold_stays_held(self):
        rows = [r for r in self.rows if r["id"] != 15544057]
        self.write_candidate(rows)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "hold")
        self.verdict()
        self.assertEqual(self.qa.finalize(), "hold")
        g = self.gates()
        self.assertTrue(g["gates"]["sample_review"]["pass"]); self.assertFalse(g["gates"]["sentinels"]["pass"]); self.assertFalse(g["transient"])


class Publish(StoreCase, unittest.TestCase):
    def setUp(self):
        self.setup_store()
        self.rows = snapshot_rows()
        self.write_candidate(self.rows)

    def tearDown(self):
        self.teardown_store()

    def test_publish_requires_ready_and_records_history(self):
        with self.assertRaises(SystemExit):
            self.qa.publish()
        self.assertEqual(self.qa.check(wm=FakeWM(self.rows)), "review")
        self.assertFalse(self.qa.publish()); self.assertFalse(self.qa.PUB.exists())
        self.verdict(); self.assertEqual(self.qa.finalize(), "ready")
        with mock.patch.object(self.qa.history, "record", wraps=self.qa.history.record) as rec:
            self.assertTrue(self.qa.publish())
        rec.assert_called_once()
        args, kwargs = rec.call_args
        self.assertIsNone(args[0], "no previous rows at the first publish"); self.assertEqual(args[2], RUN_ID)
        self.assertEqual(kwargs["prev_run_id"], None)
        man = self.store.read_json(self.qa.PUB / "manifest.json")
        self.assertEqual(man["version"], RUN_ID); self.assertEqual(man["items"], len(self.rows)); self.assertTrue(man["gates_passed"])
        self.assertFalse(man["approved_manually"]); self.assertEqual(man["file"], "items.jsonl.gz")
        self.assertEqual(man["gates"]["status"], "ready"); self.assertEqual(man["gates"]["failed"], []); self.assertEqual(len(man["gates"]["config_hash"]), 64)
        self.assertEqual(man["history"]["kind"], "baseline"); self.assertEqual(man["history"]["rows"], len(self.rows))
        self.assertTrue((self.store.ROOT / "history" / man["history"]["file"]).exists())
        self.assertTrue((self.qa.PUB / "items.jsonl.gz").exists()); self.assertTrue((self.qa.PUB / "gates.json").exists())
        self.assertEqual(self.state()["status"], "published")

    def test_second_publish_records_changes_and_passes_the_previous_version(self):
        self.qa.check(wm=FakeWM(self.rows)); self.verdict(); self.qa.finalize(); self.assertTrue(self.qa.publish())
        rows2 = [dict(r, price=9.99) if r["id"] == 1000 else r for r in self.rows]
        self.write_candidate(rows2, state=make_state(run_id="run-2"), stats=make_stats(rows2, run_id="run-2"))
        self.qa.check(wm=FakeWM(rows2)); self.verdict(run_id="run-2"); self.qa.finalize()
        with mock.patch.object(self.qa.history, "record", wraps=self.qa.history.record) as rec:
            self.assertTrue(self.qa.publish())
        self.assertEqual(rec.call_args.kwargs["prev_run_id"], RUN_ID)
        man = self.store.read_json(self.qa.PUB / "manifest.json")
        self.assertEqual(man["version"], "run-2"); self.assertEqual(man["history"]["kind"], "changes"); self.assertEqual(man["history"]["rows"], 1)

    def test_full_published_survives_core_publishes(self):
        full = "20261001-060000-full"
        self.write_candidate(self.rows, state=make_state(run_id=full), stats=make_stats(self.rows, run_id=full))
        self.qa.check(wm=FakeWM(self.rows)); self.verdict(run_id=full); self.qa.finalize(); self.assertTrue(self.qa.publish())
        man1 = self.store.read_json(self.qa.PUB / "manifest.json")
        self.assertEqual(man1["full_published"], man1["published"])
        core = "20261008-070000-core"
        self.write_candidate(self.rows, state=make_state(run_id=core), stats=make_stats(self.rows, run_id=core))
        self.qa.check(wm=FakeWM(self.rows)); self.verdict(run_id=core); self.qa.finalize()
        with mock.patch.object(self.qa, "_now", lambda: "2026-10-08T07:30:00+00:00"):
            self.assertTrue(self.qa.publish())
        man2 = self.store.read_json(self.qa.PUB / "manifest.json")
        self.assertEqual(man2["published"], "2026-10-08T07:30:00+00:00")
        self.assertEqual(man2["full_published"], man1["full_published"], "a core publish keeps the last full date")

    def test_publish_refuses_gates_from_another_run(self):
        self.qa.check(wm=FakeWM(self.rows)); self.verdict(); self.assertEqual(self.qa.finalize(), "ready")
        self.write_candidate(self.rows, state=make_state(run_id="run-2"), stats=make_stats(self.rows, run_id="run-2"))
        with self.assertRaises(SystemExit) as cm:
            self.qa.publish(approve=True)
        self.assertIn("run `check` first", str(cm.exception)); self.assertFalse(self.qa.PUB.exists())

    def test_approve_overrides_a_hold(self):
        rows = [r for r in self.rows if r["id"] != 15544057]
        self.write_candidate(rows)
        self.assertEqual(self.qa.check(wm=FakeWM(rows)), "hold")
        self.assertFalse(self.qa.publish())
        self.assertTrue(self.qa.publish(approve=True))
        man = self.store.read_json(self.qa.PUB / "manifest.json")
        self.assertFalse(man["gates_passed"]); self.assertTrue(man["approved_manually"]); self.assertEqual(man["gates"]["failed"], ["sentinels"])

    def test_cli(self):
        self.qa.main(["check"])
        self.assertEqual(self.gates()["status"], "hold", "no credentials: live check cannot run")
        self.qa.main(["finalize"])
        self.qa.main(["publish", "--approve"])
        self.assertTrue((self.qa.PUB / "manifest.json").exists())


_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()


class _Resp:
    def __init__(self, payload):
        self.status_code, self.payload, self.text = 200, payload, ""

    def json(self):
        return self.payload


class _Session:
    def __init__(self):
        self.urls = []

    def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        ids = url.split("ids=")[1].split(",")
        return _Resp({"items": [{"itemId": int(i), "salePrice": 1.0} for i in ids]})


class GetItems(unittest.TestCase):
    def test_chunks_of_20_through_get(self):
        s = _Session()
        c = wm_mod.Walmart(consumer_id="cid", private_key=_KEY, key_version="1", session=s, log=lambda *_: None, min_interval=0)
        items = c.get_items(list(range(1, 46)) + ["", " 46 "])
        self.assertEqual(len(s.urls), 3); self.assertEqual(c.calls, 3)
        self.assertTrue(all(u.startswith(wm_mod.API + "/items?ids=") for u in s.urls))
        self.assertEqual([len(u.split("ids=")[1].split(",")) for u in s.urls], [20, 20, 6])
        self.assertEqual([i["itemId"] for i in items], list(range(1, 47)))
        self.assertEqual(c.get_items([]), []); self.assertEqual(len(s.urls), 3)

    def test_list_responses_and_junk_are_tolerated(self):
        c = wm_mod.Walmart(consumer_id="cid", private_key=_KEY, key_version="1", session=_Session(), log=lambda *_: None, min_interval=0)
        with mock.patch.object(c, "get", return_value=[{"itemId": 1}, "junk", None]):
            self.assertEqual(c.get_items([1]), [{"itemId": 1}])
        with mock.patch.object(c, "get", return_value={"items": None}):
            self.assertEqual(c.get_items([1]), [])


if __name__ == "__main__":
    unittest.main()


class UnitOutlierExtremes(unittest.TestCase):
    def test_extreme_low_ratio_does_not_divide_by_zero(self):
        from crawler.qa import unit_outlier_stats
        rows = [{"id": i, "name": f"row {i}", "cat": "7", "base_unit": "ct", "unit_price": 1.0} for i in range(60)]
        rows.append({"id": 998, "name": "tiny", "cat": "7", "base_unit": "ct", "unit_price": 0.0001})   # ratio 0.0001
        rows.append({"id": 999, "name": "huge", "cat": "7", "base_unit": "ct", "unit_price": 50.0})
        share, total, outliers = unit_outlier_stats(rows, group_min=50)
        self.assertEqual(total, 62)
        self.assertEqual([o["id"] for o in outliers], [998, 999], "the 10000x-low row sorts before the 50x-high row")
        self.assertAlmostEqual(share, 2 / 62, places=5)
        zero = [{"id": 1, "cat": "7", "base_unit": "ct", "unit_price": 0.0}] * 60
        self.assertEqual(unit_outlier_stats(zero, group_min=50)[1], 0, "zero unit prices are not unit-priced rows")


if __name__ == "__main__":
    unittest.main()


class PublishDuringCrawl(unittest.TestCase):
    """plan=approve while a newer crawl runs must publish the candidate without touching that crawl's state."""
    def setUp(self):
        import importlib, os, tempfile
        from pathlib import Path
        self.tmp = tempfile.mkdtemp()
        os.environ["SFB_STORE"] = self.tmp; os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.qa, crawler.history
        for m in (crawler.store, crawler.history, crawler.qa):
            importlib.reload(m)
        self.store, self.qa = crawler.store, crawler.qa
        root = Path(self.tmp)
        self.store.write_jsonl_gz(root / "build" / "candidate" / "items.jsonl.gz",
                                  [{"id": 1, "upc": "00078742054261", "name": "corn", "price": 0.87, "flags": [], "cat": "6", "dept": "Food"}])
        self.store.write_json(root / "build" / "candidate" / "stats.json", {"run_id": "run-A", "items": 1, "upcs": 1, "built": "x", "plan": "full"})
        self.store.write_json(root / "build" / "candidate" / "gates.json", {"run_id": "run-A", "status": "hold", "passed_deterministic": False,
                                                                          "gates": {}, "config_hash": "h", "checked": "x"})
        self.store.write_json(root / "state" / "run.json", {"run_id": "run-B", "plan": "full", "status": "crawling",
                                                            "departments": [{"id": "976759", "name": "Food", "status": "crawling", "pages": 649,
                                                                             "items": 129800, "parts": 6, "next": "/x", "total_pages": 1579}]})

    def tearDown(self):
        import shutil; shutil.rmtree(self.tmp)

    def test_approve_publishes_candidate_and_leaves_the_running_crawl_alone(self):
        from pathlib import Path
        self.assertTrue(self.qa.publish(approve=True))
        manifest = self.store.read_json(Path(self.tmp) / "build" / "published" / "manifest.json")
        self.assertEqual(manifest["version"], "run-A")
        state = self.store.read_json(Path(self.tmp) / "state" / "run.json")
        self.assertEqual(state["run_id"], "run-B"); self.assertEqual(state["status"], "crawling")
        self.assertEqual(state["departments"][0]["pages"], 649)

    def test_publish_marks_its_own_run(self):
        from pathlib import Path
        self.store.write_json(Path(self.tmp) / "state" / "run.json", {"run_id": "run-A", "plan": "full", "status": "needs_review", "departments": []})
        self.assertTrue(self.qa.publish(approve=True))
        self.assertEqual(self.store.read_json(Path(self.tmp) / "state" / "run.json")["status"], "published")
