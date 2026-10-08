"""Throttle analysis: what Walmart's rate limit looks like, judged from a run's event log, and the
per-minute cap the next run should start with.

  python -m crawler.throttle store/throttle/<run_id>.events.jsonl [--cap N] [--json]

Events come from wm.Walmart: [t, status] per HTTP attempt (status 200/429/5xx, 0 = network error)
and [t, "sleep", seconds] per 429 back-off sleep, t = epoch seconds of the request start.

Reading the counts: a limiter that allows N requests per 60 s rejects a request only when at least
N requests precede it inside that minute, so for every genuine per-minute 429 the count of requests
in the preceding 60 s is >= N and the smallest such count is the tightest estimate of N. Two
corrections keep one odd 429 from dragging the cap to the floor for a whole run: a 429 preceded by
far fewer requests than the others (under half the median count) is left out of the minimum, and
the busiest clean minute (a 60 s window with no 429 in it or in the 60 s after it) is a lower bound
for N, so when it ran faster than the 429 counts suggest, those 429s were not per-minute rejections
(a Walmart hiccup, a shared quota, a longer window) and the bound takes over. When most 429s had two
or more requests in the preceding second the limiter is per-second and the request spacing, not the
per-minute cap, is the lever.

Recommendation (`per_min`; None means keep the cap the run had):
  no 429s under a cap     -> cap + 10% (at least +1, at most 48/min); nothing to raise without a cap
                             or at the ceiling; nothing to judge from under 120 s of traffic
  429s that cost < 2% of the run in back-off -> unchanged (lowering the cap 15% would cost more)
  >= 3 per-minute 429s    -> 85% of the inferred limit, clamped to 6..48, never above 85% of the cap
  other 429s under a cap  -> cap - 15% (at least 6)
  otherwise               -> unchanged

Why the first real crawl needed this (2026-10-07): 576 calls in 61 minutes with 1544 s of 429
back-off, i.e. 42% of the run asleep; the interval-only pacing cannot find the limit, it only
backs away from it after each hit.
"""
import argparse, json, statistics
from bisect import bisect_left, bisect_right
from pathlib import Path

WINDOWS = (1, 10, 60, 300)   # seconds before each 429 in which requests are counted
MIN_PER_MIN = 6              # floor of the cap: below this a full crawl takes days
MAX_PER_MIN = 48             # 60 s / 1.25 s interval: a cap above this changes nothing
MARGIN_PCT = 85              # pace at this percentage of the inferred limit
PROBE_UP_PCT = 110           # a clean capped run raises its cap to this percentage (at least +1)
BACK_OFF_PCT = 85            # a capped run with costly but uninferable 429s lowers it to this percentage
INCIDENTAL_LOSS = 0.02       # back-off under this share of the run is tolerated: lowering the cap 15%
BOUND_TOLERATED_LOSS = 0.10  # 429s that came after fewer requests than a clean minute under the cap are not the
                             # cap's doing (an outage, another client on the key): tolerated up to this share
                             # costs 15% of the next run, far more than the seconds these 429s cost
MIN_SPAN_S = 120             # a clean run shorter than this proves nothing about the limit


def load_events(path) -> list:
    """Read a .events.jsonl file; a torn last line (interrupted append) is skipped."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, list) and len(e) >= 2:
            out.append(e)
    return out


def _pct(n, pct):
    """n * pct / 100 rounded down, in exact integer arithmetic (int(20 * 1.1) is a floating-point gamble)."""
    return int(n) * pct // 100


def _count(sorted_ts, lo, hi):
    """Number of timestamps with lo < t < hi: a request exactly w seconds before another is outside its
    w-second window, as in wm.Walmart's own sliding window."""
    return bisect_left(sorted_ts, hi) - bisect_right(sorted_ts, lo)


def _count_from(sorted_ts, lo, hi):
    """Number of timestamps with lo <= t < hi (a window that starts at a request includes it)."""
    return bisect_left(sorted_ts, hi) - bisect_left(sorted_ts, lo)


def _spread(values):
    if not values:
        return None
    return {"min": min(values), "median": statistics.median(values), "max": max(values)}


def _safe_rate(reqs, oks, bad, t_end):
    """Largest number of successes in a 60 s window that had no 429 and was followed by 60 clean
    seconds, counting only windows the log actually covers. A lower bound for the sustainable rate."""
    best = None
    for s in reqs:
        if s + 120 > t_end:
            break
        if _count_from(bad, s, s + 120):
            continue
        n = _count_from(oks, s, s + 60)
        if best is None or n > best:
            best = n
    return best


def _recommend(n429, lost_share, pattern, limit, bound, cap, span_s):
    """The next run's cap and a one-line reason, by the rules in the module docstring.
    None means: nothing to infer, keep the cap the run had."""
    if n429 == 0:
        if span_s < MIN_SPAN_S:
            return None, f"only {span_s:.0f} s of traffic: too short to judge"
        if cap is None:
            return None, "no 429s without a cap: the request interval alone holds"
        if cap >= MAX_PER_MIN:
            return None, f"no 429s at the {MAX_PER_MIN}/min ceiling"
        nxt = min(MAX_PER_MIN, max(cap + 1, _pct(cap, PROBE_UP_PCT)))
        return nxt, f"no 429s under the {cap}/min cap: probing up 10%"
    if lost_share < INCIDENTAL_LOSS:
        return None, f"{n429} x 429 cost {lost_share:.1%} of the run: incidental"
    if bound and cap is not None and lost_share < BOUND_TOLERATED_LOSS:
        return None, (f"{n429} x 429 came after fewer requests than a clean minute under the {cap}/min cap "
                      f"({lost_share:.1%} lost): not the cap's doing")
    if pattern == "per-minute" and n429 >= 3 and limit:
        nxt = _pct(limit, MARGIN_PCT)
        if cap is not None:
            nxt = min(nxt, _pct(cap, BACK_OFF_PCT))
        clamped = max(MIN_PER_MIN, min(MAX_PER_MIN, nxt))
        reason = f"0.85 x inferred limit {limit}/min"
        if bound:
            reason += ", the busiest clean minute: the 429s came after fewer requests and were not per-minute rejections"
        if clamped != nxt:
            reason += f", clamped to {clamped}"
        return clamped, reason
    if cap is not None:
        if n429 < 2 or span_s < MIN_SPAN_S:
            return None, f"{n429} x 429 in {span_s:.0f} s under the {cap}/min cap: too little to lower it on"
        return max(MIN_PER_MIN, _pct(cap, BACK_OFF_PCT)), f"{n429} x 429 under the {cap}/min cap: lowering 15%"
    if pattern == "per-second":
        return None, "per-second pattern: the request spacing, not a per-minute cap, is the lever"
    return None, f"{n429} x 429: too few to infer a limit and no cap to lower"


def analyze(events, cap=None) -> dict:
    """Summarise one run's events and recommend the next per-minute cap (`per_min`; None = no change).

    Keys: totals (events, requests, ok, status_429, status_5xx, network_errors, span_s, sleep_s,
    lost_share, ok_per_min); pattern (None / "per-minute" / "per-second"); limit_per_min (the inferred
    per-minute limit the recommendation uses), limit_from_429s (smallest kept 60 s count before a 429),
    limit_per_min_median, limit_per_s, safe_per_min (busiest clean minute), consistent (False when the
    clean minute beat the 429 counts); windows (min/median/max request counts in the 1/10/60/300 s
    before each 429), gap_s (seconds between consecutive 429s), per_429 (one row per 429);
    cap (the run's), per_min (recommendation), reason."""
    cap = int(cap) if cap else None
    reqs, oks, bad, sleeps = [], [], [], []
    n5xx = nerr = 0
    t_end = None
    for e in sorted(events, key=lambda e: float(e[0])):
        t = float(e[0])
        if e[1] == "sleep":
            sleeps.append(float(e[2]))
            t_end = max(t_end or t, t + float(e[2]))
            continue
        t_end = max(t_end or t, t)
        reqs.append(t)
        status = int(e[1])
        if status == 200:
            oks.append(t)
        elif status == 429:
            bad.append(t)
        elif status >= 500:
            n5xx += 1
        elif status == 0:
            nerr += 1
    span = (t_end - reqs[0]) if reqs else 0.0
    sleep_s = sum(sleeps)
    per_429, prev = [], None
    for t in bad:
        row = {"t": t, "since_prev_s": None if prev is None else round(t - prev, 3)}
        for w in WINDOWS:
            row[f"req_{w}s"] = _count(reqs, t - w, t)
        row["ok_60s"] = _count(oks, t - 60, t)
        per_429.append(row)
        prev = t
    windows = {f"{w}s": _spread([r[f"req_{w}s"] for r in per_429]) for w in WINDOWS}
    safe = _safe_rate(reqs, oks, bad, t_end) if reqs else None
    pattern = limit = from_429s = limit_median = limit_s = consistent = None
    bound = False
    if per_429:
        bursty = sum(1 for r in per_429 if r["req_1s"] >= 2)
        pattern = "per-second" if bursty * 2 > len(per_429) else "per-minute"
        counts = [r["req_60s"] for r in per_429]
        limit_median = statistics.median(counts)
        kept = [c for c in counts if c >= limit_median / 2] or counts
        from_429s = limit = min(kept)
        if pattern == "per-second":
            limit_s = min(r["req_1s"] for r in per_429 if r["req_1s"] >= 2)
        elif safe is not None:
            consistent = safe <= from_429s
            if not consistent:
                limit, bound = safe, True
    lost_share = (sleep_s / span) if span > 0 else 0.0
    per_min, reason = _recommend(len(bad), lost_share, pattern, limit, bound, cap, span)
    return {
        "events": len(events), "requests": len(reqs), "ok": len(oks), "status_429": len(bad),
        "status_5xx": n5xx, "network_errors": nerr,
        "span_s": round(span, 1), "sleep_s": round(sleep_s, 1), "lost_share": round(lost_share, 4),
        "ok_per_min": round(len(oks) / (span / 60), 2) if span > 0 else None,
        "pattern": pattern, "limit_per_min": limit, "limit_from_429s": from_429s,
        "limit_per_min_median": limit_median, "limit_per_s": limit_s,
        "safe_per_min": safe, "consistent": consistent,
        "windows": windows,
        "gap_s": _spread([r["since_prev_s"] for r in per_429 if r["since_prev_s"] is not None]),
        "per_429": per_429,
        "cap": cap, "per_min": per_min, "reason": reason,
    }


def report(a: dict) -> str:
    """A few lines for the job summary."""
    if not a["requests"]:
        return "Throttle: no requests recorded."
    mins = a["span_s"] / 60
    rate = f"{a['ok_per_min']:.1f} ok/min" if a["ok_per_min"] is not None else "rate n/a"
    if a["status_429"]:
        first = (f"Throttle: {a['status_429']} x 429 in {mins:.0f} min; {a['sleep_s'] / 60:.1f} min lost to back-off "
                 f"({a['lost_share']:.0%} of the run). {a['requests']} requests, {a['ok']} ok ({rate}).")
    else:
        first = f"Throttle: no 429s in {mins:.0f} min; {a['requests']} requests, {a['ok']} ok ({rate})."
    safe = "" if a["safe_per_min"] is None else f"; busiest clean minute {a['safe_per_min']} ok"
    if a["pattern"] == "per-minute":
        w = a["windows"]["60s"]
        second = (f"Limit: per-minute pattern; 429s came after {w['min']}-{w['max']} requests in the preceding 60 s "
                  f"(median {w['median']:g}); inferred limit {a['limit_per_min']}/min{safe}.")
        if a["consistent"] is False:
            second += (" The clean minute ran faster than the 429 counts suggest: not a simple per-minute window "
                       "(Walmart hiccup, shared quota or longer window); the clean rate is the bound.")
    elif a["pattern"] == "per-second":
        second = (f"Limit: per-second pattern; most 429s had >= 2 requests in the preceding second "
                  f"(inferred {a['limit_per_s']}/s): the request spacing, not the per-minute cap, is the lever{safe}.")
    else:
        second = f"Limit: nothing to infer (no 429s){safe}."
    this = f"this run: {a['cap']}/min cap" if a["cap"] else "this run: no cap (1.25 s interval only)"
    if a["per_min"] is None:
        third = f"Pace: unchanged ({this}); {a['reason']}."
    else:
        third = f"Pace: next cap {a['per_min']}/min ({a['reason']}); {this}."
    return "\n".join((first, second, third))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Analyse a crawl's throttle event log.")
    ap.add_argument("events", help="store/throttle/<run_id>.events.jsonl")
    ap.add_argument("--cap", type=int, default=None, help="the per-minute cap the run used, if any")
    ap.add_argument("--json", action="store_true", help="also print the full analysis as JSON")
    a = ap.parse_args(argv)
    analysis = analyze(load_events(a.events), cap=a.cap)
    print(report(analysis))
    if a.json:
        print(json.dumps(analysis, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
