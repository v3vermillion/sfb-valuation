"""Price history: a baseline at the first publish, then one change log per publish.

Called by qa.publish() BEFORE build/published is replaced, so both the outgoing and the incoming
snapshot are still on disk. Format and the per-item median recipe: docs/HISTORY.md.

  history/baseline-<run_id>.jsonl.gz   [{id, upc, price, promo}]            first publish
  history/changes-<run_id>.jsonl.gz    [{id, upc, old, new, promo, date}]   every later publish
  history/index.json                   [{run_id, date, kind, rows, file}]   append-only
"""
from pathlib import Path

from . import store

INDEX = "index.json"


def _promo(row) -> bool:
    return "promo_price" in (row.get("flags") or [])


def _dir(root) -> Path:
    """history/ under the store root (store.ROOT when root is None)."""
    return Path(root if root is not None else store.ROOT) / "history"


def _index_at(hist: Path) -> list:
    data = store.read_json(hist / INDEX, [])
    return list(data) if isinstance(data, list) else []


def read_index(root=None) -> list:
    """The publish index under <root>/history/ (root defaults to store.ROOT); [] when absent or unreadable."""
    return _index_at(_dir(root))


def _append_index(hist: Path, entry: dict):
    index = _index_at(hist)
    index.append(entry)
    store.write_json(hist / INDEX, index)


def _write_baseline(hist: Path, run_id: str, date: str, rows) -> dict:
    """rows: iterable of (id, upc, price, promo) tuples."""
    name = f"baseline-{run_id}.jsonl.gz"
    n = store.write_jsonl_gz(hist / name, ({"id": i, "upc": u, "price": p, "promo": m} for i, u, p, m in rows))
    entry = {"run_id": run_id, "date": date, "kind": "baseline", "rows": n, "file": name}
    _append_index(hist, entry)
    return entry


def record(prev_rows, new_rows, run_id: str, date: str, root=None, prev_run_id=None) -> dict:
    """Record the publish of `new_rows` (an iterable of snapshot rows) replacing `prev_rows`
    (an iterable, or None at the first publish). Files go under <root>/history/ (root defaults to
    store.ROOT). Returns the index entry written for this publish.

    - no previous snapshot -> baseline-<run_id>
    - previous snapshot but no history yet (history introduced after the first publish, or the
      directory was lost) -> a baseline is written from the previous snapshot first, then the changes,
      so a replay always has a starting point
    - otherwise -> changes-<run_id>: changed prices, new rows (old null) and removed rows (new null)
    """
    hist = _dir(root)
    prev = {}
    for r in prev_rows or ():
        prev[r["id"]] = (r.get("upc"), r.get("price"), _promo(r))

    if not prev:
        return _write_baseline(hist, run_id, date, ((r["id"], r.get("upc"), r.get("price"), _promo(r)) for r in new_rows))

    if not _index_at(hist):
        _write_baseline(hist, str(prev_run_id or f"{run_id}-prev"), date,
                        ((i, u, p, m) for i, (u, p, m) in sorted(prev.items(), key=lambda kv: str(kv[0]))))

    def changes():
        seen = set()
        for r in new_rows:
            i = r["id"]
            seen.add(i)
            new_price, promo = r.get("price"), _promo(r)
            old = prev.get(i)
            if old is None:
                yield {"id": i, "upc": r.get("upc"), "old": None, "new": new_price, "promo": promo, "date": date}
            elif old[1] != new_price:
                yield {"id": i, "upc": r.get("upc"), "old": old[1], "new": new_price, "promo": promo, "date": date}
        for i, (upc, price, promo) in prev.items():
            if i not in seen:
                yield {"id": i, "upc": upc, "old": price, "new": None, "promo": promo, "date": date}

    name = f"changes-{run_id}.jsonl.gz"
    n = store.write_jsonl_gz(hist / name, changes())
    entry = {"run_id": run_id, "date": date, "kind": "changes", "rows": n, "file": name}
    _append_index(hist, entry)
    return entry
