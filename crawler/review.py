"""Claude sample review: a second pair of eyes on a random sample of the candidate snapshot.

  python -m crawler.review run        # reads build/candidate/review-sample.jsonl, writes review-verdict.json, exit 0 always

qa.check() writes the sample (write_sample). This command asks the model whether the sample shows
systematic junk (data/review-criteria.md) and writes a verdict that qa.finalize() folds into the gates:
  {"status": "pass"|"fail", "systematic_junk", "junk_rate", "junk_examples", "notes", "run_id", "model", ...}
  {"status": "skipped", "reason": "ANTHROPIC_API_KEY missing"}      no key in the environment
  {"status": "error", "reason": ...}                                 API, network or parsing failure (a hold)
Env: ANTHROPIC_API_KEY (required for a verdict), SFB_REVIEW_MODEL (default claude-sonnet-5-5).
The exit code is 0 in every case: the pipeline's finish step reads the verdict and decides.
"""
import argparse, json, os, random, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import store

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 12000                # first attempt: the model's thinking over 300 rows shares this cap with the answer
MAX_TOKENS_RETRY = 20000          # one retry when the answer was still cut off (kept under the non-streaming comfort zone)
TIMEOUT_S = 300
RETRIES = 3                       # attempts for 429 / 5xx / connection errors
RETRY_WAIT_S = (10, 30)
DATA = Path(__file__).resolve().parent.parent / "data"
CRITERIA = DATA / "review-criteria.md"
CAND = store.ROOT / "build" / "candidate"
SAMPLE_FIELDS = ("id", "upc", "brand", "name", "size", "unit", "pack", "price", "unit_price", "base_unit",
                 "dept", "stock", "flags", "path")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------------------- sample

def compact(row, categories=None) -> dict:
    out = {k: row.get(k) for k in SAMPLE_FIELDS if row.get(k) not in (None, "", [])}
    cat = row.get("cat")
    if cat is not None:
        out["category"] = (categories or {}).get(str(cat), str(cat))
    return out


def write_sample(rows, run_id, n=300, path=None) -> list:
    """Pick n rows at random (deterministic for a run_id) and write them as compact JSON lines."""
    # barcode-only placeholders and withheld prices are not shown as priced items, so they are not reviewed as such
    rows = [r for r in rows if "placeholder" not in (r.get("flags") or []) and not r.get("price_withheld")]
    n = max(0, int(n))
    picked = rows if len(rows) <= n else random.Random(str(run_id)).sample(rows, n)
    picked.sort(key=lambda r: str(r.get("id")))
    try:
        categories = store.config().get("categories") or {}
    except (OSError, ValueError):
        categories = {}
    sample = [compact(r, categories) for r in picked]
    path = Path(path) if path else CAND / "review-sample.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(s, separators=(",", ":")) + "\n" for s in sample))
    return sample


def read_sample(path=None) -> list:
    path = Path(path) if path else CAND / "review-sample.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


# ----------------------------------------------------------------------------- prompt + parsing

def build_messages(criteria: str, sample: list):
    system = ("You audit a product price snapshot for a food bank's donation valuation app. "
              "Judge the sample strictly by the criteria below and answer with one JSON object only.\n\n" + criteria.strip())
    lines = "\n".join(json.dumps(s, separators=(",", ":")) for s in sample)
    user = (f"Here are {len(sample)} rows sampled at random from the candidate snapshot, one JSON object per line. "
            "Review every row against the criteria. Then return ONLY this JSON object, nothing else:\n"
            '{"systematic_junk": true|false, "junk_rate": <share of junk rows, 0 to 1>, '
            '"junk_examples": [{"id": <item id>, "why": "<short reason>"}], "notes": "<one or two sentences>", '
            '"miscategorized_rate": <share of rows whose category does not fit, 0 to 1>, '
            '"miscategorized_examples": [{"id": <item id>, "category": "<as given>", "should_be": "<category>"}]}\n\n'
            f"ROWS:\n{lines}")
    return system, [{"role": "user", "content": user}]


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "yes", "y", "1"):
            return True
        if s in ("false", "no", "n", "0", ""):
            return False
    raise ValueError(f"systematic_junk is not a boolean: {v!r}")


def _to_rate(v):
    if isinstance(v, bool):
        raise ValueError("junk_rate is a boolean")
    if isinstance(v, str):
        s = v.strip().rstrip("%").strip()
        pct = v.strip().endswith("%")
        v = float(s)
        if pct:
            v /= 100
    if not isinstance(v, (int, float)):
        raise ValueError(f"junk_rate is not a number: {v!r}")
    v = float(v)
    if v != v:
        raise ValueError("junk_rate is NaN")
    if 1 < v <= 100:        # a percentage given as a number
        v /= 100
    if v < 0 or v > 1:
        raise ValueError(f"junk_rate out of range: {v}")
    return round(v, 4)


def _json_candidates(text: str):
    t = text.strip()
    yield t
    for m in re.finditer(r"```(?:json)?\s*(.*?)```", t, re.S):
        yield m.group(1).strip()
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b > a:
        yield t[a:b + 1]


def parse_verdict(text: str) -> dict:
    """Pull the JSON object out of the model's answer and normalise it. Raises ValueError when no usable object."""
    if not text or not text.strip():
        raise ValueError("empty response")
    obj, first, last = None, None, None
    for cand in _json_candidates(text):
        try:
            o = json.loads(cand)
        except ValueError as e:
            last = e
            continue
        if isinstance(o, dict):
            if "junk_rate" in o and "systematic_junk" in o:
                obj = o          # the verdict, even when an echoed {id, why} example object came first
                break
            first = first if first is not None else o
    if obj is None:
        obj = first          # no complete verdict: the first object gives the precise "missing" error below
    if obj is None:
        raise ValueError(f"no JSON object in response ({last})")
    if "junk_rate" not in obj:
        raise ValueError("junk_rate missing")
    if "systematic_junk" not in obj:
        raise ValueError("systematic_junk missing")
    ex = obj.get("junk_examples") or []
    if isinstance(ex, dict):
        ex = [ex]
    if not isinstance(ex, list):
        ex = [str(ex)]
    examples = []
    for e in ex[:50]:
        if isinstance(e, dict):
            examples.append({"id": e.get("id"), "why": str(e.get("why") or e.get("reason") or "")[:200]})
        else:
            examples.append({"id": None, "why": str(e)[:200]})
    out = {"systematic_junk": _to_bool(obj["systematic_junk"]), "junk_rate": _to_rate(obj["junk_rate"]),
           "junk_examples": examples, "notes": str(obj.get("notes") or "")[:2000]}
    if obj.get("miscategorized_rate") is not None:       # measured, never a gate (docs/CATEGORIES.md is the guide)
        try:
            out["miscategorized_rate"] = _to_rate(obj["miscategorized_rate"])
            mex = obj.get("miscategorized_examples") or []
            out["miscategorized_examples"] = [{"id": e.get("id"), "category": str(e.get("category") or "")[:60],
                                               "should_be": str(e.get("should_be") or "")[:60]}
                                              for e in mex[:25] if isinstance(e, dict)]
        except ValueError:
            pass
    return out


def response_text(data: dict) -> str:
    return "".join(b.get("text") or "" for b in (data.get("content") or []) if isinstance(b, dict) and b.get("type") == "text")


# ----------------------------------------------------------------------------- API

class ReviewError(Exception):
    """The API did not give a usable answer; str(e) is a safe reason (never includes the key).
    kind: "auth" (401, invalid or revoked key), "permission" (403, key not allowed), "credits" (402 billing_error, or
    the 400 "credit balance is too low" older accounts get), or "api" (anything else)."""

    def __init__(self, message, kind="api"):
        super().__init__(message)
        self.kind = kind


def error_kind(status: int, body: str) -> str:
    """Classify a non-retryable API error so the alert can name the fix (new key vs add credits)."""
    try:
        err = (json.loads(body or "{}") or {}).get("error") or {}
    except ValueError:
        err = {}
    etype = str(err.get("type") or "") if isinstance(err, dict) else ""
    text = f"{etype} {err.get('message') if isinstance(err, dict) else ''} {body or ''}".lower()
    if status == 401 or etype == "authentication_error":
        return "auth"
    if status == 402 or etype == "billing_error" or "credit balance" in text:
        return "credits"
    if status == 403 or etype == "permission_error":
        return "permission"
    return "api"


def call_api(payload: dict, api_key: str, sleep=time.sleep) -> dict:
    headers = {"content-type": "application/json", "x-api-key": api_key, "anthropic-version": API_VERSION}
    last = None
    for attempt in range(RETRIES):
        if attempt:
            sleep(RETRY_WAIT_S[min(attempt - 1, len(RETRY_WAIT_S) - 1)])
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT_S)
        except requests.RequestException as e:
            last = f"network error: {type(e).__name__}: {str(e)[:200]}"
            continue
        if r.status_code == 200:
            try:
                data = r.json()
            except ValueError:
                raise ReviewError("response is not JSON")
            if not isinstance(data, dict):
                raise ReviewError("response is not a JSON object")
            return data
        body = (r.text or "")[:300].replace("\n", " ")
        if r.status_code == 429 or r.status_code >= 500:
            last = f"HTTP {r.status_code}: {body}"
            continue
        raise ReviewError(f"HTTP {r.status_code}: {body}", kind=error_kind(r.status_code, r.text or ""))
    raise ReviewError(f"gave up after {RETRIES} attempts; last: {last}")


def _max_junk_rate():
    """sample_review.max_junk_rate: from the thresholds qa.check recorded for this candidate, else from
    data/gates.json via qa.gates_config (imported lazily: qa imports this module). None = no limit."""
    g = store.read_json(CAND / "gates.json") or {}
    sr = (g.get("thresholds") or {}).get("sample_review")
    if not isinstance(sr, dict):
        from . import qa
        sr = qa.gates_config().get("sample_review") or {}
    return sr.get("max_junk_rate", 0.05)


def _run_id():
    state = store.read_json(store.ROOT / "state" / "run.json") or {}
    stats = store.read_json(CAND / "stats.json") or {}
    return stats.get("run_id") or state.get("run_id")


def run(api_key=None, model=None, sample=None, out_path=None, sleep=time.sleep) -> dict:
    """Review the sample and write build/candidate/review-verdict.json. Returns the verdict."""
    out_path = Path(out_path) if out_path else CAND / "review-verdict.json"
    api_key = (api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")).strip()
    model = (model or os.environ.get("SFB_REVIEW_MODEL") or DEFAULT_MODEL).strip()
    verdict = {"run_id": _run_id(), "model": model, "checked": _now()}
    if not api_key:
        verdict.update(status="skipped", reason="ANTHROPIC_API_KEY missing")
        store.write_json(out_path, verdict)
        print("review skipped: ANTHROPIC_API_KEY missing")
        return verdict
    sample = read_sample() if sample is None else list(sample)
    verdict["sample_rows"] = len(sample)
    if not sample:
        verdict.update(status="error", reason="review sample is empty or missing (run qa check first)")
        store.write_json(out_path, verdict)
        print(verdict["reason"])
        return verdict
    criteria = CRITERIA.read_text() if CRITERIA.exists() else "Judge whether the rows are sellable consumer items with sensible names, sizes and prices."
    system, messages = build_messages(criteria, sample)
    payload = {"model": model, "max_tokens": MAX_TOKENS, "system": system, "messages": messages}
    try:
        for attempt in range(2):
            data = call_api(payload, api_key, sleep=sleep)
            text = response_text(data)
            usage = data.get("usage") or {}
            verdict["usage"] = {k: usage.get(k) for k in ("input_tokens", "output_tokens") if k in usage}
            verdict["max_tokens"] = payload["max_tokens"]
            if data.get("stop_reason") == "refusal":
                raise ReviewError("model refused the request")
            try:
                parsed = parse_verdict(text)
                break
            except ValueError as e:
                if data.get("stop_reason") != "max_tokens":
                    raise ReviewError(f"unparseable response: {e}; text: {text[:300]!r}")
                if attempt or payload["max_tokens"] >= MAX_TOKENS_RETRY:
                    raise ReviewError(f"response truncated at max_tokens={payload['max_tokens']}; {e}")
                # the model's thinking shares max_tokens with the answer; give it room once
                print(f"review answer cut off at max_tokens={payload['max_tokens']}; retrying with {MAX_TOKENS_RETRY}")
                payload = dict(payload, max_tokens=MAX_TOKENS_RETRY)
    except ReviewError as e:
        verdict.update(status="error", reason=str(e)[:500], error_kind=e.kind)
        store.write_json(out_path, verdict)
        print(f"review error: {verdict['reason']}")
        return verdict
    max_junk = _max_junk_rate()
    ok = not parsed["systematic_junk"] and (max_junk is None or parsed["junk_rate"] <= max_junk)
    verdict.update(parsed, status="pass" if ok else "fail", max_junk_rate=max_junk)
    store.write_json(out_path, verdict)
    print(f"review {verdict['status']}: junk rate {parsed['junk_rate']:.1%}, systematic {parsed['systematic_junk']}, "
          f"{len(parsed['junk_examples'])} examples ({model})")
    return verdict


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
