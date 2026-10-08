"""Walmart client pacing: a 429 slows the client down for the run; a long run of successes eases it back;
an optional per-minute cap holds requests to a sliding 60 s window; every attempt and back-off sleep is logged."""
import unittest
from unittest import mock

import requests

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import crawler.wm as wm

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()


class _Resp:
    def __init__(self, status):
        self.status_code = status
        self.text = ""

    def json(self):
        return {"items": []}

    def raise_for_status(self):
        raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    """Answers each request with the next scripted status code, or raises it when it is an exception."""
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.requests = 0

    def get(self, url, headers=None, timeout=None):
        self.requests += 1
        nxt = self.statuses.pop(0)
        if isinstance(nxt, BaseException):
            raise nxt
        return _Resp(nxt)


def _client(statuses, **kw):
    logs = []
    c = wm.Walmart(consumer_id="cid", private_key=_KEY, key_version="1", session=_Session(statuses), log=logs.append, **kw)
    return c, logs


class Pacing(unittest.TestCase):
    def setUp(self):
        self.sleeps = []
        p = mock.patch("crawler.wm.time.sleep", side_effect=self.sleeps.append)
        p.start(); self.addCleanup(p.stop)

    def test_429_raises_the_interval_and_successes_bring_it_back_to_the_floor(self):
        c, logs = _client([429] + [200] * 150)
        c.get("/x")                                   # 429 then 200
        self.assertAlmostEqual(c.min_interval, 1.25 * 1.15)
        for _ in range(49):                           # 50 consecutive successes in total
            c.get("/x")
        self.assertAlmostEqual(c.min_interval, 1.25 * 1.15 * 0.9)
        for _ in range(50):                           # 100: the next 10% step would go under the floor
            c.get("/x")
        self.assertEqual(c.min_interval, 1.25)
        for _ in range(50):                           # 150: stays on the floor, no more log lines
            c.get("/x")
        self.assertEqual(c.min_interval, 1.25)
        self.assertEqual(len([l for l in logs if l.startswith("pace:")]), 2)

    def test_the_streak_restarts_after_any_non_success(self):
        slowed = 1.25 * 1.15 ** 2
        c, _ = _client([429] + [200] * 49 + [429] + [200] * 30 + [500] + [200] * 20
                       + [requests.ConnectionError("connection reset")] + [200] * 50)
        for _ in range(49):                           # 49 ok after the first 429: no easing yet
            c.get("/x")
        self.assertAlmostEqual(c.min_interval, 1.25 * 1.15)
        c.get("/x")                                   # second 429 resets the streak and slows again
        self.assertAlmostEqual(c.min_interval, slowed)
        for _ in range(29):                           # 30 ok
            c.get("/x")
        c.get("/x")                                   # 500 (retried) -> 200: the streak restarts at 1
        for _ in range(19):                           # 20 ok since the 500
            c.get("/x")
        self.assertAlmostEqual(c.min_interval, slowed, msg="no easing before 50 consecutive successes")
        c.get("/x")                                   # network error (retried) -> 200: restarts at 1 again
        for _ in range(48):                           # 49 ok since the network error
            c.get("/x")
        self.assertAlmostEqual(c.min_interval, slowed, msg="a network error must restart the streak")
        c.get("/x")                                   # 50th consecutive success
        self.assertAlmostEqual(c.min_interval, slowed * 0.9)

    def test_never_below_the_starting_interval_without_a_429(self):
        c, logs = _client([200] * 120, min_interval=2.0)
        for _ in range(120):
            c.get("/x")
        self.assertEqual(c.min_interval, 2.0)
        self.assertEqual(c.base_interval, 2.0)
        self.assertFalse([l for l in logs if l.startswith("pace:")])

    def test_429_backoff_and_wait_cap_are_unchanged(self):
        c, _ = _client([429, 429, 429, 200])
        c.get("/x")
        throttle_sleeps = [s for s in self.sleeps if s >= 5]  # pacing waits are far shorter than the 5 s backoff
        self.assertEqual(len(throttle_sleeps), 3)
        for got, base in zip(throttle_sleeps, (5, 10, 20)):   # doubling back-off plus up to 2 s of jitter
            self.assertTrue(base <= got <= base + 2, throttle_sleeps)
        self.assertAlmostEqual(c.throttle_waited, sum(throttle_sleeps))
        self.assertAlmostEqual(c.min_interval, 1.25 * 1.15 ** 3)
        capped, _ = _client([429, 200], max_throttle_wait=0)
        with self.assertRaises(wm.Throttled):
            capped.get("/x")

    def test_interval_ceiling_holds_and_recovery_starts_from_it(self):
        c, _ = _client([429] * 10 + [200] * 50)       # 1.25 * 1.15**10 would be 5.06 s: the 5 s ceiling applies
        c.get("/x")
        self.assertEqual(c.min_interval, 5.0)
        self.assertLess(c.throttle_waited, c.max_throttle_wait, "ten 429s stay inside the 45-minute cap")
        for _ in range(49):
            c.get("/x")
        self.assertAlmostEqual(c.min_interval, 4.5)


class _Clock:
    """time.time/time.sleep replacement: sleeping advances the clock by exactly the requested amount."""
    def __init__(self, start=1000.0):
        self.t = start
        self.sleeps = []

    def time(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


class _BadJson(_Resp):
    def json(self):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


class NonJson(unittest.TestCase):
    def test_a_200_with_a_body_that_is_not_json_is_retried_like_a_server_error(self):
        sleeps = []
        p = mock.patch("crawler.wm.time.sleep", side_effect=sleeps.append); p.start(); self.addCleanup(p.stop)
        c, logs = _client([200, 200])
        c.s.get = mock.Mock(side_effect=[_BadJson(200), _Resp(200)])
        self.assertEqual(c.get("/x"), {"items": []})
        self.assertEqual(c.calls, 2)
        self.assertTrue(any("HTTP 502" in m for m in logs), logs)
        self.assertEqual(c._ok_streak, 1, "only the parsed success counts towards pace recovery")

    def test_a_200_that_never_parses_gives_up_after_the_server_error_retries(self):
        p = mock.patch("crawler.wm.time.sleep"); p.start(); self.addCleanup(p.stop)
        c, _ = _client([])
        c.s.get = mock.Mock(side_effect=[_BadJson(200)] * 6)
        with self.assertRaises(RuntimeError):
            c.get("/x")
        self.assertEqual(c.calls, 6)


class Window(unittest.TestCase):
    def setUp(self):
        self.clock = _Clock()
        for name, fn in (("crawler.wm.time.time", self.clock.time), ("crawler.wm.time.sleep", self.clock.sleep)):
            p = mock.patch(name, side_effect=fn)
            p.start(); self.addCleanup(p.stop)

    def test_requests_beyond_the_cap_wait_exactly_until_the_oldest_leaves_the_window(self):
        c, _ = _client([200] * 10, max_per_min=4)
        for _ in range(10):
            c.get("/x")
        starts = [t for t, _ in c.events]
        self.assertEqual(starts, [1000, 1001.25, 1002.5, 1003.75, 1060, 1061.25, 1062.5, 1063.75, 1120, 1121.25])
        # the 1.25 s interval sleep comes first, then the window wait makes up the rest of the minute
        self.assertEqual(self.clock.sleeps, [1.25] * 4 + [55.0] + [1.25] * 4 + [55.0] + [1.25])
        self.assertEqual(c.cap_waited, 110.0)
        self.assertEqual(c.min_interval, 1.25, "the cap never touches the interval pacing")
        self.assertEqual(c.stats()["max_per_min"], 4)

    def test_the_interval_is_still_enforced_under_a_loose_cap(self):
        c, _ = _client([200] * 6, max_per_min=1000)
        for _ in range(6):
            c.get("/x")
        self.assertEqual(self.clock.sleeps, [1.25] * 5)
        self.assertEqual(c.cap_waited, 0.0)

    def test_no_cap_means_the_interval_alone(self):
        c, _ = _client([200] * 6)
        for _ in range(6):
            c.get("/x")
        self.assertIsNone(c.max_per_min)
        self.assertEqual(self.clock.sleeps, [1.25] * 5)
        self.assertEqual(c.cap_waited, 0.0)
        self.assertEqual(len(c._window), 0, "no timestamps are kept without a cap")

    def test_a_429_lowers_the_cap_for_the_run_and_successes_raise_it_back_to_the_start(self):
        c, logs = _client([429, 429] + [200] * 400, max_per_min=40)
        c.get("/x")                                   # two 429s, then a success
        self.assertEqual(c.max_per_min, 28, "40 -> 34 -> 28: the interval alone cannot pace below 12/min")
        self.assertEqual(c.base_per_min, 40)
        for _ in range(49):                           # 50 consecutive successes
            c.get("/x")
        self.assertEqual(c.max_per_min, 30)           # +10% (at least +1)
        for _ in range(350):                          # 30 -> 33 -> 36 -> 39 -> 40, then it stays
            c.get("/x")
        self.assertEqual(c.max_per_min, 40, "never above the cap the run started with")
        self.assertTrue(any("cap back to" in m for m in logs))

    def test_the_in_run_cut_never_raises_a_cap_below_the_floor_and_stops_at_it(self):
        c, _ = _client([429, 200], max_per_min=3)
        c.get("/x")
        self.assertEqual(c.max_per_min, 3)
        c, _ = _client([429] * 6 + [200], max_per_min=8)
        c.get("/x")
        self.assertEqual(c.max_per_min, 6)

    def test_a_429_retry_counts_against_the_window_too(self):
        c, _ = _client([429, 200, 200, 200, 200], max_per_min=3)
        c.get("/x")                                   # 429 at 1000 (+~5-7 s back-off), 200 at ~1006
        c.get("/x")                                   # third request in the window
        c.get("/x")                                   # must wait until the 429'd attempt leaves at 1060
        self.assertEqual(c.events[0][1], 429)
        self.assertEqual(round(c.events[-1][0]), 1060)
        self.assertAlmostEqual(c.cap_waited, 1060 - (c.events[-2][0] + c.min_interval), places=3)

    def test_every_attempt_and_every_back_off_sleep_is_logged(self):
        c, _ = _client([429, 200, 500, requests.ConnectionError("reset"), 200])
        c.get("/x")                                   # 429 -> back-off -> 200
        c.get("/x")                                   # 500 -> retry -> network error -> retry -> 200
        kinds = [e[1] for e in c.events]
        self.assertEqual(kinds, [429, "sleep", 200, 500, 0, 200])
        t429, sleep, ok1, e500, err, ok2 = c.events
        self.assertEqual(t429[0], 1000.0)
        self.assertEqual(sleep[0], 1000.0, "the sleep is stamped when it starts")
        self.assertTrue(5 <= sleep[2] <= 7, sleep)
        self.assertAlmostEqual(sleep[2], c.throttle_waited, places=2)
        self.assertAlmostEqual(ok1[0], 1000.0 + sleep[2], places=2)
        self.assertTrue(all(len(e) == 2 for e in (t429, ok1, e500, err, ok2)))
        self.assertEqual(c.stats(), {"requests": 5, "status_429": 1, "sleep_s": round(c.throttle_waited, 1),
                                     "cap_wait_s": 0.0, "max_per_min": None, "min_interval": round(1.25 * 1.15, 3)})
        drained = c.drain_events()
        self.assertEqual(len(drained), 6)
        self.assertEqual(c.events, [])
        self.assertEqual(c.drain_events(), [])

    def test_a_fatal_status_is_logged_before_it_is_raised(self):
        c, _ = _client([404], max_per_min=0)
        self.assertIsNone(c.max_per_min, "0 means no cap, like None")
        with self.assertRaises(RuntimeError):
            c.get("/x")
        self.assertEqual(c.events, [(1000.0, 404)])
        self.assertEqual(c.stats()["requests"], 1)


if __name__ == "__main__":
    unittest.main()
