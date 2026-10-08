"""The last published snapshots, kept outside the data-store branch as GitHub Release assets, for one-tap rollback.

Every publish uploads build/published/* (items, manifest, stats, gates, report; shards as they are) to a release tagged
snapshot-<version> and deletes all but the newest KEEP. A rollback (pipeline plan=rollback, rollback_to = "previous" or a
version) downloads one, checks it is complete, and puts it back as build/published; deploy-app then ships it.

Uses the gh CLI with GH_TOKEN (the workflow's token, contents: write). Never touches the crawl state or the candidate.
"""
import json, os, shutil, subprocess, tempfile
from pathlib import Path

from . import store

KEEP = 3
TAG_PREFIX = "snapshot-"


class ReleaseError(RuntimeError):
    pass


def available() -> bool:
    return bool(shutil.which("gh") and os.environ.get("GITHUB_REPOSITORY")
                and (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")))


def _gh(*args, check=True):
    r = subprocess.run(["gh", *args, "-R", os.environ["GITHUB_REPOSITORY"]], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise ReleaseError(f"gh {' '.join(args[:2])} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def tag_for(version: str) -> str:
    return TAG_PREFIX + str(version)


def list_snapshots():
    """Snapshot releases, newest first: [{"tag", "version", "created"}]."""
    out = _gh("release", "list", "--limit", "100", "--json", "tagName,createdAt").stdout or "[]"
    rows = [r for r in json.loads(out) if str(r.get("tagName", "")).startswith(TAG_PREFIX)]
    rows.sort(key=lambda r: r.get("createdAt") or "", reverse=True)
    return [{"tag": r["tagName"], "version": r["tagName"][len(TAG_PREFIX):], "created": r.get("createdAt")} for r in rows]


def archive(pub_dir: Path, manifest: dict) -> str:
    """Upload the published snapshot as release snapshot-<version> (replacing a release of the same version)."""
    version = manifest.get("version")
    if not version:
        raise ReleaseError("the published manifest has no version")
    files = sorted(str(p) for p in Path(pub_dir).iterdir() if p.is_file())
    if not any(Path(f).name == "manifest.json" for f in files):
        raise ReleaseError("build/published has no manifest.json")
    tag = tag_for(version)
    if _gh("release", "view", tag, check=False).returncode == 0:
        _gh("release", "delete", tag, "--cleanup-tag", "--yes")
    gates = (manifest.get("gates") or {}).get("status")
    notes = (f"Published snapshot `{version}`: {manifest.get('items')} items, published {manifest.get('published')}, "
             f"gates {gates or 'n/a'}{', approved manually' if manifest.get('approved_manually') else ''}.\n\n"
             "Kept for rollback: run the pipeline workflow with plan=rollback and rollback_to set to this version "
             "(or `previous`). Only the newest three snapshots are kept.")
    _gh("release", "create", tag, *files, "--title", f"Snapshot {version}", "--notes", notes, "--latest=false")
    return tag


def prune(keep: int = KEEP):
    """Delete all but the newest `keep` snapshot releases. Returns the deleted tags."""
    deleted = []
    for r in list_snapshots()[keep:]:
        _gh("release", "delete", r["tag"], "--cleanup-tag", "--yes")
        deleted.append(r["tag"])
    return deleted


def pick(snapshots, target: str, current_version):
    """The snapshot to roll back to: "previous" = the newest one that is not the live version; else by version or tag."""
    target = (target or "previous").strip()
    if target == "previous":
        for s in snapshots:
            if s["version"] != current_version:
                return s
        raise ReleaseError("no earlier snapshot is kept (the live one is the only release)")
    for s in snapshots:
        if target in (s["version"], s["tag"]):
            return s
    kept = ", ".join(s["version"] for s in snapshots) or "none"
    raise ReleaseError(f"no kept snapshot {target!r} (kept: {kept})")


def download(snapshot) -> Path:
    """Download one snapshot into a temporary folder and check it is complete (manifest + every item readable)."""
    tmp = Path(tempfile.mkdtemp(prefix="sfb-rollback-"))
    _gh("release", "download", snapshot["tag"], "--dir", str(tmp))
    man = store.read_json(tmp / "manifest.json")
    if not isinstance(man, dict) or str(man.get("version")) != snapshot["version"]:
        raise ReleaseError(f"{snapshot['tag']} has no matching manifest.json")
    items = tmp / (man.get("file") or "items.jsonl.gz")
    try:
        n = sum(1 for _ in store.iter_jsonl_gz(items))
    except (OSError, EOFError, ValueError) as e:
        raise ReleaseError(f"{snapshot['tag']}: items unreadable ({e})")
    if man.get("items") is not None and n != int(man["items"]):
        raise ReleaseError(f"{snapshot['tag']}: {n} items downloaded, manifest says {man['items']}")
    return tmp
