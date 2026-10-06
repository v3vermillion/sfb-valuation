"""Persistent working store (the `data-store` git branch, checked out at ./store).

Layout:
  state/run.json                 current crawl run: plan, per-department cursor/status
  raw/<run_id>/<dept>/part-NNNN.jsonl.gz   slimmed raw items as fetched
  build/                         latest processed snapshot + manifest + report
  identify/                      Open Food Facts US subset + equivalence table
"""
import gzip, json, os, subprocess, time
from pathlib import Path

ROOT = Path(os.environ.get("SFB_STORE", "store"))
CONFIG = Path(__file__).resolve().parent.parent / "data" / "categories.json"

KEEP_FIELDS = ("itemId", "parentItemId", "upc", "name", "brandName", "size", "salePrice", "msrp",
               "categoryPath", "categoryNode", "marketplace", "stock", "availableOnline", "offerType",
               "sellerInfo", "clearance", "flashDeal", "limitedTimeDeal", "bundle", "preOrder")


def config():
    return json.loads(CONFIG.read_text())


def slim(item: dict) -> dict:
    out = {k: item[k] for k in KEEP_FIELDS if k in item and item[k] not in (None, "")}
    attrs = item.get("attributes") or {}
    keep = {k: v for k, v in attrs.items() if any(t in k.lower() for t in ("size", "count", "flavor", "scent", "pack", "variant"))}
    if keep:
        out["attrs"] = keep
    return out


def read_json(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
    tmp.replace(path)


def iter_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_jsonl_gz(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
            n += 1
    return n


def checkpoint(message: str):
    """Commit and push the store so a later run can resume. No-op outside a git checkout."""
    if not (ROOT / ".git").exists() or os.environ.get("SFB_NO_COMMIT"):
        return
    def git(*a):
        return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
    git("add", "-A")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    git("commit", "-q", "-m", message)
    for attempt in range(3):
        if git("push", "-q", "origin", "HEAD:data-store").returncode == 0:
            return
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("could not push store checkpoint")
