"""Price history: baseline at the first publish, a change log at every later one, an append-only index."""
import importlib, json, os, shutil, tempfile, unittest
from pathlib import Path


def r(i, price, promo=False, upc=None):
    return {"id": i, "upc": upc or f"{i:014d}", "price": price, "flags": ["promo_price"] if promo else [], "name": f"item {i}"}


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["SFB_STORE"] = str(self.tmp); os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.history
        importlib.reload(crawler.store); importlib.reload(crawler.history)
        self.store, self.history = crawler.store, crawler.history
        self.hist = self.tmp / "history"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def rows(self, name):
        return list(self.store.iter_jsonl_gz(self.hist / name))

    def index(self):
        return json.loads((self.hist / "index.json").read_text())

    def test_first_publish_writes_a_baseline(self):
        new = [r(1, 1.0), r(2, 2.5, promo=True), r(3, 0.5)]
        entry = self.history.record(None, iter(new), "run-1", "2026-10-07")
        self.assertEqual(entry, {"run_id": "run-1", "date": "2026-10-07", "kind": "baseline", "rows": 3, "file": "baseline-run-1.jsonl.gz"})
        self.assertEqual(self.rows("baseline-run-1.jsonl.gz"),
                         [{"id": 1, "upc": "00000000000001", "price": 1.0, "promo": False},
                          {"id": 2, "upc": "00000000000002", "price": 2.5, "promo": True},
                          {"id": 3, "upc": "00000000000003", "price": 0.5, "promo": False}])
        self.assertEqual(self.index(), [entry])
        # an empty previous iterator is also a first publish
        shutil.rmtree(self.hist)
        self.assertEqual(self.history.record(iter([]), iter(new), "run-1", "2026-10-07")["kind"], "baseline")

    def test_later_publish_writes_changes_only(self):
        prev = [r(1, 1.0), r(2, 2.5, promo=True), r(3, 0.5), r(4, 4.0)]
        self.history.record(None, iter(prev), "run-1", "2026-10-07")
        new = [r(1, 1.0), r(2, 2.0), r(3, 0.75, promo=True), r(5, 5.0)]        # 1 same, 2 and 3 changed, 4 removed, 5 new
        entry = self.history.record(iter(prev), iter(new), "run-2", "2026-10-14")
        self.assertEqual(entry, {"run_id": "run-2", "date": "2026-10-14", "kind": "changes", "rows": 4, "file": "changes-run-2.jsonl.gz"})
        ch = {c["id"]: c for c in self.rows("changes-run-2.jsonl.gz")}
        self.assertEqual(set(ch), {2, 3, 4, 5})
        self.assertEqual(ch[2], {"id": 2, "upc": "00000000000002", "old": 2.5, "new": 2.0, "promo": False, "date": "2026-10-14"})
        self.assertEqual(ch[3], {"id": 3, "upc": "00000000000003", "old": 0.5, "new": 0.75, "promo": True, "date": "2026-10-14"})
        self.assertEqual(ch[4], {"id": 4, "upc": "00000000000004", "old": 4.0, "new": None, "promo": False, "date": "2026-10-14"})
        self.assertEqual(ch[5], {"id": 5, "upc": "00000000000005", "old": None, "new": 5.0, "promo": False, "date": "2026-10-14"})
        self.assertEqual([e["kind"] for e in self.index()], ["baseline", "changes"])
        # nothing changed -> an empty changes file, still indexed
        entry = self.history.record(iter(new), iter(new), "run-3", "2026-10-21")
        self.assertEqual(entry["rows"], 0); self.assertEqual(self.rows("changes-run-3.jsonl.gz"), [])
        self.assertEqual(len(self.index()), 3)

    def test_previous_snapshot_without_history_gets_a_baseline_first(self):
        prev = [r(1, 1.0), r(2, 2.0)]
        new = [r(1, 1.5), r(2, 2.0)]
        entry = self.history.record(iter(prev), iter(new), "run-2", "2026-10-14", prev_run_id="run-1")
        self.assertEqual(entry["kind"], "changes")
        idx = self.index()
        self.assertEqual([(e["kind"], e["run_id"], e["rows"]) for e in idx], [("baseline", "run-1", 2), ("changes", "run-2", 1)])
        self.assertEqual(self.rows("baseline-run-1.jsonl.gz"), [{"id": 1, "upc": "00000000000001", "price": 1.0, "promo": False},
                                                                {"id": 2, "upc": "00000000000002", "price": 2.0, "promo": False}])
        # without a previous version name the baseline is named after this run
        shutil.rmtree(self.hist)
        self.history.record(iter(prev), iter(new), "run-2", "2026-10-14")
        self.assertEqual(self.index()[0]["file"], "baseline-run-2-prev.jsonl.gz")

    def test_root_argument_and_index_recovery(self):
        other = self.tmp / "elsewhere"                      # a store root: files go under <root>/history/
        self.history.record(None, iter([r(1, 1.0)]), "run-1", "2026-10-07", root=other)
        self.assertTrue((other / "history" / "baseline-run-1.jsonl.gz").exists()); self.assertFalse(self.hist.exists())
        self.assertEqual(self.history.read_index(other)[0]["file"], "baseline-run-1.jsonl.gz")
        (other / "history" / "index.json").write_text("{}")          # not a list: treated as empty
        self.assertEqual(self.history.read_index(other), [])
        self.assertEqual(self.history.read_index(self.tmp / "nowhere"), [])


if __name__ == "__main__":
    unittest.main()
