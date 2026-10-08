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


# GitHub rejects a pushed file over 100 MB and warns over 50 MB. A .jsonl.gz larger than SHARD_BYTES is written as
# shards <name>.s000, <name>.s001, ... (each a complete gzip stream; concatenated they are one valid gzip stream, so
# any reader can also just chain them). Readers go through jsonl_files()/iter_jsonl_gz(), which accept either form.
SHARD_BYTES = int(os.environ.get("SFB_SHARD_BYTES") or 45 * 1024 * 1024)
FILE_LIMIT_BYTES = 95 * 1024 * 1024          # checkpoint refuses to push a file above this (GitHub's limit is 100 MB)
STORE_ALERT_BYTES = 1024 ** 3                 # ci raises [data-store-size] above 1 GB of files on the branch


def shards(path: Path):
    path = Path(path)
    if not path.parent.exists():
        return []
    return sorted(p for p in path.parent.glob(path.name + ".s[0-9][0-9][0-9]"))


def jsonl_files(path: Path):
    """The file itself, or its shards in order, or [] when neither exists."""
    path = Path(path)
    return [path] if path.exists() else shards(path)


def jsonl_exists(path: Path) -> bool:
    return bool(jsonl_files(path))


def iter_jsonl_gz(path: Path):
    files = jsonl_files(path)
    if not files:
        raise FileNotFoundError(path)
    for p in files:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def write_jsonl_gz(path: Path, rows, shard_bytes=None):
    """Write rows as one .jsonl.gz, or as shards when the compressed size passes shard_bytes (default SHARD_BYTES).
    Written to temporary names first; stale shards or a stale single file from an earlier write are removed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    limit = shard_bytes or SHARD_BYTES
    tmp_names, n = [], 0
    raw = gz = None

    def open_next():
        nonlocal raw, gz
        t = path.parent / f".{path.name}.tmp{len(tmp_names):03d}"
        tmp_names.append(t)
        raw = open(t, "wb")
        gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)

    def close():
        gz.close(); raw.close()

    open_next()
    for r in rows:
        gz.write((json.dumps(r, separators=(",", ":")) + "\n").encode("utf-8"))
        n += 1
        if n % 2000 == 0 and raw.tell() >= limit:
            close(); open_next()
    close()
    for old in shards(path):
        old.unlink()
    if len(tmp_names) == 1:
        tmp_names[0].replace(path)
    else:
        if path.exists():
            path.unlink()
        for i, t in enumerate(tmp_names):
            t.replace(path.parent / f"{path.name}.s{i:03d}")
    return n


def oversized_files(limit=None):
    """Files in the store (outside .git) larger than limit (default FILE_LIMIT_BYTES), as [(relative path, bytes)],
    largest first."""
    limit = FILE_LIMIT_BYTES if limit is None else limit
    out = []
    for p in ROOT.rglob("*"):
        if ".git" in p.relative_to(ROOT).parts or not p.is_file():
            continue
        size = p.stat().st_size
        if size > limit:
            out.append((str(p.relative_to(ROOT)), size))
    return sorted(out, key=lambda x: -x[1])


def tree_bytes():
    """Total size of the files on the data-store branch (outside .git): what every checkout downloads."""
    return sum(p.stat().st_size for p in ROOT.rglob("*")
               if p.is_file() and ".git" not in p.relative_to(ROOT).parts)


def checkpoint(message: str):
    """Commit and push the store so a later run can resume. No-op outside a git checkout."""
    if not (ROOT / ".git").exists() or os.environ.get("SFB_NO_COMMIT"):
        return
    def git(*a):
        return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
    too_big = oversized_files()
    if too_big:
        # GitHub would reject the push; say exactly which file and stop before committing anything
        listing = ", ".join(f"{p} ({s / 1048576:.0f} MB)" for p, s in too_big[:5])
        raise RuntimeError(f"refusing to push: {listing} exceed {FILE_LIMIT_BYTES / 1048576:g} MB (GitHub rejects files over "
                           "100 MB); write it with store.write_jsonl_gz so it is sharded")
    git("add", "-A")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    git("commit", "-q", "-m", message)
    for attempt in range(3):
        if git("push", "-q", "origin", "HEAD:data-store").returncode == 0:
            return
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("could not push store checkpoint")
