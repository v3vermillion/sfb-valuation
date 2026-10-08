"""Weekly live audit: due() timing and run() against a fake Walmart."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from _fixtures import StoreCase, FakeWM, snapshot_rows

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


class Due(StoreCase, unittest.TestCase):
    def setUp(self):
        self.setup_store()

    def tearDown(self):
        self.teardown_store()

    def latest(self, **kw):
        self.store.write_json(self.store.ROOT / "audit" / "latest.json", kw)

    def test_due_when_missing_fresh_or_old(self):
        cfg = {"audit_every_days": 7}
        self.assertTrue(self.audit.due(self.store.ROOT, cfg, NOW), "no audit yet")
        self.latest(checked=(NOW - timedelta(days=1)).isoformat())
        self.assertFalse(self.audit.due(self.store.ROOT, cfg, NOW))
        self.latest(checked=(NOW - timedelta(days=7)).isoformat())
        self.assertTrue(self.audit.due(self.store.ROOT, cfg, NOW))
        self.latest(checked=(NOW - timedelta(days=6, hours=23)).isoformat())
        self.assertFalse(self.audit.due(self.store.ROOT, cfg, NOW))
        self.assertTrue(self.audit.due(self.store.ROOT, {"audit_every_days": 3}, NOW))

    def test_unreadable_input_biases_towards_running(self):
        self.latest(checked="not a date")
        self.assertTrue(self.audit.due(self.store.ROOT, {"audit_every_days": 7}, NOW))
        self.latest(nothing=1)
        self.assertTrue(self.audit.due(self.store.ROOT, {}, NOW))
        (self.store.ROOT / "audit" / "latest.json").write_text("[]")
        self.assertTrue(self.audit.due(self.store.ROOT, None, NOW))
        self.latest(checked=(NOW - timedelta(days=5)).isoformat())
        self.assertFalse(self.audit.due(self.store.ROOT, None, NOW), "no cfg: default 7 days")
        self.assertFalse(self.audit.due(self.store.ROOT, {"audit_every_days": "seven"}, NOW), "bad value: default 7 days")
        self.latest(checked="2026-10-08T12:00:00Z")
        self.assertFalse(self.audit.due(self.store.ROOT, {"audit_every_days": 7}, NOW), "Z suffix parses")


class Run(StoreCase, unittest.TestCase):
    def setUp(self):
        self.setup_store()
        self.rows = snapshot_rows()

    def tearDown(self):
        self.teardown_store()

    def test_without_a_published_snapshot(self):
        res = self.audit.run(wm=FakeWM(self.rows))
        self.assertEqual(res["status"], "skipped"); self.assertFalse(res["alert"]); self.assertFalse((self.audit.AUDIT / "latest.json").exists())

    def test_audit_writes_dated_and_latest_files(self):
        self.write_published(self.rows, version="v1")
        wm = FakeWM(self.rows)
        res = self.audit.run(wm=wm)
        self.assertEqual(res["status"], "ok"); self.assertEqual(res["version"], "v1"); self.assertFalse(res["alert"])
        self.assertEqual(res["match_rate"], 1.0); self.assertEqual(res["within_5pct"], 1.0); self.assertEqual(res["outlier_share"], 0.0)
        self.assertEqual(res["sample"], 181); self.assertEqual(res["checked_rows"], 181); self.assertEqual(res["calls"], 10)
        self.assertEqual(res["audit_match_min"], 0.95)
        latest = self.store.read_json(self.audit.AUDIT / "latest.json")
        dated = self.store.read_json(self.audit.AUDIT / f"{res['date']}.json")
        self.assertEqual(latest, res); self.assertEqual(dated, res)
        self.assertFalse(self.audit.due(self.store.ROOT, {"audit_every_days": 7}))

    def test_sample_size_and_daily_seed(self):
        self.write_published(self.rows)
        wm = FakeWM(self.rows)
        self.audit.run(wm=wm, n=40)
        self.assertEqual(sum(len(c) for c in wm.requested), 40)
        self.write_gates(audit_sample=25)
        wm = FakeWM(self.rows)
        self.audit.run(wm=wm)
        self.assertEqual(sum(len(c) for c in wm.requested), 25)
        a = [i for c in wm.requested for i in c]
        wm = FakeWM(self.rows)
        with mock.patch.object(self.audit, "_now", return_value=NOW + timedelta(days=7)):
            self.audit.run(wm=wm)
        self.assertNotEqual(a, [i for c in wm.requested for i in c], "a later audit samples different rows")

    def test_regression_alerts_unless_threshold_is_null(self):
        self.write_published(self.rows)
        changed = {r["id"]: r["price"] * 2 for r in self.rows[:20]}
        res = self.audit.run(wm=FakeWM(self.rows, prices=changed))
        self.assertTrue(res["alert"]); self.assertAlmostEqual(res["match_rate"], 161 / 181, places=3)
        self.assertEqual(len(res["drift_examples"]), 20); self.assertEqual(res["drift_examples"][0]["live"], changed[res["drift_examples"][0]["id"]])
        self.write_gates(audit_match_min=None)
        res = self.audit.run(wm=FakeWM(self.rows, prices=changed))
        self.assertFalse(res["alert"]); self.assertIsNone(res["audit_match_min"])

    def test_outlier_recount(self):
        rows = [dict(r, unit_price=r["unit_price"] * 60) if r["id"] in (1000, 1001, 1002) else r for r in self.rows]
        self.write_published(rows)
        res = self.audit.run(wm=FakeWM(rows))
        self.assertEqual(res["outlier_rows"], 3); self.assertAlmostEqual(res["outlier_share"], 3 / 181, places=4)
        self.assertEqual({o["id"] for o in res["outlier_examples"]}, {1000, 1001, 1002})

    def test_no_credentials_skips_without_writing(self):
        self.write_published(self.rows)
        res = self.audit.run()
        self.assertEqual(res["status"], "skipped"); self.assertIn("credentials", res["reason"]); self.assertFalse(res["alert"])
        self.assertFalse((self.audit.AUDIT / "latest.json").exists())
        fake = FakeWM(self.rows)
        with mock.patch.dict("os.environ", {"WM_CONSUMER_ID": "cid", "WM_PRIVATE_KEY": "key"}), \
             mock.patch("crawler.wm.Walmart", return_value=fake):
            self.assertEqual(self.audit.run()["status"], "ok")

    def test_live_failure_is_an_error_result_without_a_record_but_partial_results_count(self):
        self.write_published(self.rows)
        res = self.audit.run(wm=FakeWM(self.rows, fail_after=2))
        self.assertEqual(res["status"], "error"); self.assertFalse(res["alert"]); self.assertIn("Throttled", res["reason"])
        self.assertEqual(res["checked_rows"], 40); self.assertFalse((self.audit.AUDIT / "latest.json").exists())
        self.assertTrue(self.audit.due(self.store.ROOT, {"audit_every_days": 7}), "nothing recorded: the next run tries again")
        res = self.audit.run(wm=FakeWM(self.rows, fail_after=8))
        self.assertEqual(res["status"], "ok"); self.assertEqual(res["checked_rows"], 160); self.assertIn("Throttled", res["live_error"])
        self.assertTrue((self.audit.AUDIT / "latest.json").exists())

    def test_carried_over_rows_are_audited(self):
        rows = [dict(r, flags=["carried_over"]) if r["dept"] == "Pets" else r for r in self.rows]
        self.write_published(rows)
        wm = FakeWM(rows)
        res = self.audit.run(wm=wm)
        self.assertEqual(res["sample"], 181, "the gate skips carried-over rows, the audit does not")
        self.assertTrue({"2000", "2001"} <= {i for c in wm.requested for i in c})

    def test_cli(self):
        self.write_published(self.rows)
        fake = FakeWM(self.rows)
        with mock.patch.object(self.audit.qa, "walmart_client", return_value=fake):
            self.audit.main(["--sample", "30"])
        self.assertEqual(sum(len(c) for c in fake.requested), 30)


if __name__ == "__main__":
    unittest.main()
