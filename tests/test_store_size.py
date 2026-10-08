"""GitHub rejects files over 100 MB: large .jsonl.gz files are written as gzip shards, readers accept either form,
checkpoint refuses to push an oversized file, and ci raises [data-store-size] past 1 GB."""
import gzip, importlib, os, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest import mock


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp)
        os.environ["SFB_STORE"] = str(self.tmp)
        import crawler.store
        self.store = importlib.reload(crawler.store)

    def rows(self, n):
        return ({"id": i, "name": f"item {i} " + "x" * (i % 97), "price": i / 7} for i in range(n))

    def test_large_files_are_sharded_and_read_back_in_order(self):
        p = self.tmp / "build" / "candidate" / "items.jsonl.gz"
        n = self.store.write_jsonl_gz(p, self.rows(30000), shard_bytes=64 * 1024)
        shards = self.store.shards(p)
        self.assertGreater(len(shards), 2); self.assertFalse(p.exists())
        self.assertTrue(all(s.stat().st_size < 64 * 1024 + 128 * 1024 for s in shards), "each shard stays near the limit")
        self.assertTrue(self.store.jsonl_exists(p))
        self.assertEqual([r["id"] for r in self.store.iter_jsonl_gz(p)], list(range(30000))); self.assertEqual(n, 30000)
        # the shards are complete gzip members: concatenated they are one valid stream
        joined = gzip.decompress(b"".join(s.read_bytes() for s in shards)).decode().splitlines()
        self.assertEqual(len(joined), 30000)
        # rewriting small replaces the shards with one file, and back again
        self.store.write_jsonl_gz(p, self.rows(10))
        self.assertTrue(p.exists()); self.assertEqual(self.store.shards(p), [])
        self.store.write_jsonl_gz(p, self.rows(30000), shard_bytes=64 * 1024)
        self.assertFalse(p.exists()); self.assertGreater(len(self.store.shards(p)), 2)
        self.assertFalse(list(p.parent.glob(".*tmp*")), "no temporary files left behind")

    def test_small_files_keep_their_name_and_globs_never_see_shards(self):
        raw = self.tmp / "raw" / "run" / "1"
        self.store.write_jsonl_gz(raw / "part-0001.jsonl.gz", self.rows(5))
        self.store.write_jsonl_gz(raw / "part-0002.jsonl.gz", self.rows(30000), shard_bytes=64 * 1024)
        self.assertEqual(sorted(p.name for p in raw.glob("part-*.jsonl.gz")), ["part-0001.jsonl.gz"],
                         "shard names (.sNNN) never match the *.jsonl.gz globs, so nothing is read twice")
        self.assertFalse(self.store.jsonl_exists(self.tmp / "missing.jsonl.gz"))
        with self.assertRaises(FileNotFoundError):
            list(self.store.iter_jsonl_gz(self.tmp / "missing.jsonl.gz"))

    def test_checkpoint_refuses_an_oversized_file_before_committing(self):
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)
        os.environ.pop("SFB_NO_COMMIT", None)
        self.addCleanup(os.environ.__setitem__, "SFB_NO_COMMIT", "1")
        (self.tmp / "big.bin").write_bytes(b"0" * 4096)
        with mock.patch.object(self.store, "FILE_LIMIT_BYTES", 1024):
            with self.assertRaises(RuntimeError) as cm:
                self.store.checkpoint("x")
        self.assertIn("big.bin", str(cm.exception)); self.assertIn("100 MB", str(cm.exception))
        log = subprocess.run(["git", "-C", str(self.tmp), "log", "--oneline"], capture_output=True, text=True)
        self.assertEqual(log.stdout, "", "nothing was committed")


class SizeWatch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp)
        os.environ["SFB_STORE"] = str(self.tmp); os.environ["SFB_NO_COMMIT"] = "1"
        import crawler.store, crawler.ci
        self.store = importlib.reload(crawler.store); self.ci = importlib.reload(crawler.ci)
        (self.tmp / "raw").mkdir(); (self.tmp / "raw" / "a.bin").write_bytes(b"0" * 3000)
        (self.tmp / "build").mkdir(); (self.tmp / "build" / "b.bin").write_bytes(b"0" * 1000)
        self.ci._reset_outputs("continue")

    def test_alerts_past_the_limit_with_the_breakdown_and_the_proposal(self):
        with mock.patch.object(self.store, "STORE_ALERT_BYTES", 2000):
            self.ci._size_watch()
        o = self.ci._outputs
        self.assertEqual(o["alert"], "data-store-size")
        body = Path(o["alert_body_file"]).read_text()
        self.assertIn("raw 0 MB", body); self.assertIn("Cloudflare R2", body); self.assertIn("needs your decision", body)

    def test_resolves_under_the_limit(self):
        self.ci._size_watch()
        self.assertEqual(self.ci._outputs["alert"], "none"); self.assertIn("data-store-size", self.ci._outputs["resolve"])


if __name__ == "__main__":
    unittest.main()
