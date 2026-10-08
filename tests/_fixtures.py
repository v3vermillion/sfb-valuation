"""Shared helpers for the qa / audit / history / review tests: a synthetic store with a candidate snapshot."""
import importlib, json, os, shutil, tempfile
from collections import Counter
from pathlib import Path

RUN_ID = "20261007-120000-core"
FOOD_ID, PETS_ID = "976759", "5440"
GATES_DEFAULTS = {
    "dept_size_tolerance": 0.3, "sentinel_misses_max": 0, "live_sample": 500, "live_match_min": 0.97,
    "size_parse_min": 0.95, "unit_outliers_max": 0.005, "unit_outlier_group_min": 50,
    "price_drift_max": 0.02, "item_count_min_ratio": 0.9, "category_count_tolerance": 0.2, "category_count_min_rows": 200,
    "sample_review": {"required": True, "max_junk_rate": 0.05, "sample_size": 300},
    "audit_sample": 500, "audit_match_min": 0.95,
}
SENTINEL = {"q": "gv corn", "all": ["great value", "corn"], "size": [15.25, "oz"]}


def row(i, **kw):
    r = {"id": i, "upc": f"{i:014d}", "name": f"Food item {i}, 10 oz", "brand": "Brand", "size": 10.0, "unit": "oz",
         "pack": 1, "base_qty": 10.0, "base_unit": "oz", "price": 2.0 + (i % 7) * 0.5, "basis": "each",
         "cat": "6", "dept": "Food", "path": "Home Page/Food/Pantry", "variants": [], "store_brand": False,
         "stock": "Available", "online": True, "offer": "ONLINE_AND_STORE", "size_src": "name", "flags": []}
    r.update(kw)
    if "unit_price" not in kw:
        r["unit_price"] = round(r["price"] / (r["base_qty"] * r["pack"]), 4) if r.get("base_qty") and r.get("pack") else None
    r.setdefault("primary", bool(r.get("upc")))
    return r


def snapshot_rows(n_food=120, n_pets=60):
    rows = [row(1000 + i) for i in range(n_food)]
    rows.append(row(15544057, upc="00078742054261", name="Great Value Whole Kernel Sweet Corn, 15.25 oz Can", brand="Great Value",
                    size=15.25, base_qty=15.25, price=0.87))
    rows += [row(2000 + i, name=f"Pet item {i}, 5 lb", size=5.0, unit="lb", base_qty=80.0, price=10.0 + (i % 5),
                 cat="19", dept="Pets", path="Home Page/Pets/Dog food") for i in range(n_pets)]
    return rows


def make_state(run_id=RUN_ID, status="built", food_pages=10, pets_pages=4):
    return {"run_id": run_id, "plan": "core", "status": status, "started": "2026-10-07T10:00:00+00:00",
            "updated": "2026-10-07T12:00:00+00:00", "calls": 14, "throttle_wait_s": 0,
            "departments": [
                {"id": FOOD_ID, "name": "Food", "status": "done", "next": None, "pages": food_pages, "items": 130, "parts": 1, "total_pages": food_pages},
                {"id": PETS_ID, "name": "Pets", "status": "done", "next": None, "pages": pets_pages, "items": 60, "parts": 1, "total_pages": pets_pages},
            ]}


def make_stats(rows, run_id=RUN_ID):
    return {"built": "2026-10-07T12:00:00+00:00", "run_id": run_id, "plan": "core", "items": len(rows),
            "upcs": len({r["upc"] for r in rows if r.get("upc")}), "carried_over": sum("carried_over" in r["flags"] for r in rows),
            "raw_by_department": dict(Counter(r["dept"] for r in rows)),
            "kept_by_category": dict(Counter(r["cat"] for r in rows)),
            "kept_by_department": dict(Counter(r["dept"] for r in rows)),
            "rejects_by_department": {"Food": {"media_misfiled": 1}}, "flags": dict(Counter(f for r in rows for f in r["flags"])),
            "upc_price_conflicts": 0, "upc_price_conflict_examples": []}


class FakeWM:
    """Answers get_items with the snapshot price unless overridden; can fail after N calls."""
    def __init__(self, rows, prices=None, fail_after=None, exc=None, missing=()):
        self.price = {str(r["id"]): r["price"] for r in rows}
        self.price.update({str(k): v for k, v in (prices or {}).items()})
        self.fail_after, self.exc, self.missing = fail_after, exc, {str(m) for m in missing}
        self.calls = 0
        self.requested = []

    def get_items(self, ids):
        if self.fail_after is not None and self.calls >= self.fail_after:
            from crawler.wm import Throttled
            raise self.exc or Throttled("429 persisted")
        self.calls += 1
        ids = [str(i) for i in ids]
        self.requested.append(ids)
        return [{"itemId": int(i), "salePrice": self.price[i], "stock": "Available"} for i in ids if i in self.price and i not in self.missing]


class StoreCase:
    """Mixin: a temp SFB_STORE with reloaded crawler modules, temp sentinels and gates files."""
    def setup_store(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SFB_STORE"] = self.tmp; os.environ["SFB_NO_COMMIT"] = "1"
        self.saved_env = {k: os.environ.pop(k, None) for k in ("WM_CONSUMER_ID", "WM_PRIVATE_KEY", "ANTHROPIC_API_KEY", "SFB_REVIEW_MODEL")}
        import crawler.store, crawler.history, crawler.review, crawler.qa, crawler.audit
        for m in (crawler.store, crawler.history, crawler.review, crawler.qa, crawler.audit):
            importlib.reload(m)
        self.store, self.history, self.review, self.qa, self.audit = crawler.store, crawler.history, crawler.review, crawler.qa, crawler.audit
        self.root = Path(self.tmp)
        self.sent = self.root / "sentinels.json"
        self.sent.write_text(json.dumps({"sentinels": [SENTINEL]}))
        self.gates_file = self.root / "gates.json"
        self.write_gates()
        self.qa.SENTINELS = self.sent
        self.qa.GATES = self.gates_file

    def teardown_store(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self.saved_env.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def write_gates(self, **over):
        cfg = json.loads(json.dumps(GATES_DEFAULTS))
        for k, v in over.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
        self.gates_file.write_text(json.dumps(cfg))

    def write_candidate(self, rows, state=None, stats=None):
        self.store.write_json(self.store.ROOT / "state" / "run.json", state or make_state())
        self.store.write_jsonl_gz(self.qa.CAND / "items.jsonl.gz", rows)
        self.store.write_json(self.qa.CAND / "stats.json", stats or make_stats(rows))

    def write_published(self, rows, stats=None, version="20260901-000000-full"):
        self.store.write_jsonl_gz(self.qa.PUB / "items.jsonl.gz", rows)
        self.store.write_json(self.qa.PUB / "stats.json", stats or make_stats(rows, run_id=version))
        self.store.write_json(self.qa.PUB / "manifest.json", {"version": version, "published": "2026-09-01T00:00:00+00:00",
                                                              "items": len(rows), "upcs": len(rows), "file": "items.jsonl.gz"})

    def gates(self):
        return self.store.read_json(self.qa.CAND / "gates.json")

    def state(self):
        return self.store.read_json(self.store.ROOT / "state" / "run.json")

    def verdict(self, run_id=RUN_ID, **kw):
        v = {"status": "pass", "systematic_junk": False, "junk_rate": 0.0, "junk_examples": [], "notes": "clean", "run_id": run_id, "model": "m"}
        v.update(kw)
        self.store.write_json(self.qa.CAND / "review-verdict.json", v)
        return v
