"""crawler/releases.py and the pipeline's snapshot archive + plan=rollback, with gh replaced by an in-memory fake."""
import json, os, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest import mock

import crawler.releases as releases
from tests.test_ci import PlanBase, iso, state, dec, manifest
import crawler.ci as ci


class FakeGH:
    """Releases as {tag: {"files": {name: bytes}, "created": n}}; answers the gh calls releases.py makes."""

    def __init__(self):
        self.rel, self.n, self.calls, self.fail_create = {}, 0, [], False

    def __call__(self, *args, check=True):
        self.calls.append(args)
        ok = lambda out="": subprocess.CompletedProcess(args, 0, out, "")
        bad = lambda err: (_ for _ in ()).throw(releases.ReleaseError(err)) if check else subprocess.CompletedProcess(args, 1, "", err)
        cmd, a = args[1], list(args[2:])
        if cmd == "list":
            return ok(json.dumps([{"tagName": t, "createdAt": f"2026-10-{r['created']:02d}T00:00:00Z"} for t, r in self.rel.items()]))
        if cmd == "view":
            return ok() if a[0] in self.rel else bad("release not found")
        if cmd == "delete":
            return ok() if self.rel.pop(a[0], None) is not None else bad("release not found")
        if cmd == "create":
            if self.fail_create:
                return bad("HTTP 403: Resource not accessible by integration")
            tag, files = a[0], a[1:a.index("--title")]
            self.n += 1
            self.rel[tag] = {"files": {Path(f).name: Path(f).read_bytes() for f in files}, "created": self.n}
            return ok()
        if cmd == "download":
            if a[0] not in self.rel:
                return bad("release not found")
            d = Path(a[a.index("--dir") + 1])
            for name, data in self.rel[a[0]]["files"].items():
                (d / name).write_bytes(data)
            return ok()
        raise AssertionError(f"unexpected gh call {args}")


class Releases(PlanBase):
    def setUp(self):
        super().setUp()
        import importlib
        importlib.reload(releases)
        self.gh = FakeGH()
        for p in (mock.patch.object(releases, "_gh", self.gh), mock.patch.object(releases, "available", lambda: True)):
            p.start(); self.addCleanup(p.stop)

    def publish(self, version, items=3, day=None):
        pub = self.root / "build" / "published"
        if pub.exists():
            shutil.rmtree(pub)
        self.store.write_jsonl_gz(pub / "items.jsonl.gz", [{"id": i, "v": version} for i in range(items)])
        self.write("build/published/manifest.json", {"version": version, "items": items, "file": "items.jsonl.gz",
                                                     "published": iso(day if day is not None else 0)})
        return pub

    def live(self):
        return self.read("build/published/manifest.json")

    def live_items(self):
        return list(self.store.iter_jsonl_gz(self.root / "build" / "published" / "items.jsonl.gz"))

    # archive / prune / pick
    def test_archive_keeps_the_newest_three(self):
        for v in ("run-1", "run-2", "run-3", "run-4"):
            releases.archive(self.publish(v), self.live())
            releases.prune()
        self.assertEqual([s["version"] for s in releases.list_snapshots()], ["run-4", "run-3", "run-2"])

    def test_archive_of_the_same_version_replaces_it(self):
        releases.archive(self.publish("run-1", items=2), self.live())
        releases.archive(self.publish("run-1", items=5), self.live())
        self.assertEqual(len(self.gh.rel), 1)
        self.assertEqual(json.loads(self.gh.rel["snapshot-run-1"]["files"]["manifest.json"])["items"], 5)

    def test_archive_uploads_shards_as_they_are(self):
        pub = self.publish("run-1")
        (pub / "items.jsonl.gz.s001").write_bytes((pub / "items.jsonl.gz").read_bytes())
        releases.archive(pub, self.live())
        self.assertIn("items.jsonl.gz.s001", self.gh.rel["snapshot-run-1"]["files"])

    def test_archive_refuses_a_snapshot_without_a_version(self):
        with self.assertRaises(releases.ReleaseError):
            releases.archive(self.publish("run-1"), {"items": 3})

    def test_pick(self):
        snaps = [{"tag": f"snapshot-run-{n}", "version": f"run-{n}"} for n in (3, 2, 1)]
        self.assertEqual(releases.pick(snaps, "previous", "run-3")["version"], "run-2")
        self.assertEqual(releases.pick(snaps, "previous", "run-2")["version"], "run-3")   # after a rollback: the newer one
        self.assertEqual(releases.pick(snaps, "", "run-3")["version"], "run-2")
        self.assertEqual(releases.pick(snaps, "run-1", "run-3")["version"], "run-1")
        self.assertEqual(releases.pick(snaps, "snapshot-run-1", "run-3")["version"], "run-1")
        with self.assertRaisesRegex(releases.ReleaseError, "kept: run-3, run-2, run-1"):
            releases.pick(snaps, "run-9", "run-3")
        with self.assertRaisesRegex(releases.ReleaseError, "no earlier snapshot"):
            releases.pick(snaps[:1], "previous", "run-3")

    def test_download_rejects_an_incomplete_release(self):
        releases.archive(self.publish("run-1", items=3), self.live())
        man = json.loads(self.gh.rel["snapshot-run-1"]["files"]["manifest.json"]); man["items"] = 4
        self.gh.rel["snapshot-run-1"]["files"]["manifest.json"] = json.dumps(man).encode()
        with self.assertRaisesRegex(releases.ReleaseError, "3 items downloaded, manifest says 4"):
            releases.download({"tag": "snapshot-run-1", "version": "run-1"})
        del self.gh.rel["snapshot-run-1"]["files"]["items.jsonl.gz"]
        with self.assertRaisesRegex(releases.ReleaseError, "items unreadable"):
            releases.download({"tag": "snapshot-run-1", "version": "run-1"})

    # the pipeline: publish archives, rollback restores
    def publish_through_ci(self, version):
        self.write("state/run.json", state("built", run_id=version))
        self.candidate("# report\n\nStatus: ready\n")
        with mock.patch.object(self.qa, "finalize", lambda: "ready", create=True), \
             mock.patch.object(self.qa, "publish", lambda approve=False: (self.publish(version), True)[1]):
            return self.run_plan("--plan", "finish")

    def test_publish_archives_and_resolves(self):
        o, _ = self.publish_through_ci("run-1")
        self.assertIn("snapshot-run-1", self.gh.rel)
        self.assertIn("snapshot-archive", o["resolve"])
        self.assertIn("kept for rollback as release `snapshot-run-1`", Path(os.environ["GITHUB_STEP_SUMMARY"]).read_text())

    def test_a_failed_archive_alerts_but_keeps_the_publish(self):
        self.gh.fail_create = True
        o, _ = self.publish_through_ci("run-1")
        self.assertEqual(o["alert"], "snapshot-archive"); self.assertEqual(o["next"], "continue")
        self.assertIn("HTTP 403", self.body(o))
        self.assertEqual(self.live()["version"], "run-1")

    def test_rollback_to_previous_restores_the_snapshot_and_leaves_the_crawl_alone(self):
        for v in ("run-1", "run-2"):
            self.publish_through_ci(v)
        crawl_state = state("crawling", run_id="run-3", departments=[{"id": "1", "page": 40}])
        self.write("state/run.json", crawl_state)
        self.candidate()
        cand = sorted(p.name for p in (self.root / "build" / "candidate").iterdir())
        o, _ = self.run_plan("--plan", "rollback")
        man = self.live()
        self.assertEqual(man["version"], "run-1")
        self.assertEqual(man["rolled_back"]["from"], "run-2"); self.assertEqual(man["rolled_back"]["to"], "run-1")
        self.assertEqual(man["rolled_back_at"], man["rolled_back"]["at"])
        self.assertEqual({r["v"] for r in self.live_items()}, {"run-1"})
        self.assertEqual(self.read("state/run.json"), crawl_state)
        self.assertEqual(sorted(p.name for p in (self.root / "build" / "candidate").iterdir()), cand)
        self.assertIn("Rolled back", Path(os.environ["GITHUB_STEP_SUMMARY"]).read_text())
        self.assertEqual(o.get("next"), "")
        # rolling "previous" again goes forward to the newest kept snapshot
        self.run_plan("--plan", "rollback")
        self.assertEqual(self.live()["version"], "run-2")

    def test_rollback_to_a_named_version(self):
        for v in ("run-1", "run-2", "run-3"):
            self.publish_through_ci(v)
        self.run_plan("--plan", "rollback", "--rollback-to", "run-1")
        self.assertEqual(self.live()["version"], "run-1")

    def test_rollback_refuses_unknown_or_broken_and_leaves_the_live_snapshot(self):
        self.publish_through_ci("run-1"); self.publish_through_ci("run-2")
        with self.assertRaisesRegex(SystemExit, "rollback refused: no kept snapshot 'run-9'"):
            self.run_plan("--plan", "rollback", "--rollback-to", "run-9")
        del self.gh.rel["snapshot-run-1"]["files"]["items.jsonl.gz"]
        with self.assertRaisesRegex(SystemExit, "items unreadable"):
            self.run_plan("--plan", "rollback")
        self.assertEqual(self.live()["version"], "run-2")
        self.assertEqual({r["v"] for r in self.live_items()}, {"run-2"})

    def test_rollback_without_gh_says_so(self):
        with mock.patch.object(releases, "available", lambda: False):
            with self.assertRaisesRegex(SystemExit, "needs the gh CLI"):
                self.run_plan("--plan", "rollback")


class RollbackPause(unittest.TestCase):
    def test_new_crawls_wait_one_core_period_after_a_rollback(self):
        m = manifest(40); m["rolled_back_at"] = iso(2)
        self.assertNotIn(dec(state("published"), man=m), ("start-full", "start-core"))
        m["rolled_back_at"] = iso(8)
        self.assertEqual(dec(state("published"), man=m), "start-full")
        m = manifest(10); m["rolled_back_at"] = "garbage"
        self.assertEqual(dec(state("published"), man=m), "start-core")


if __name__ == "__main__":
    unittest.main()
