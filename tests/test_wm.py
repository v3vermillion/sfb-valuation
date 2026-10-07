"""Walmart client pacing: a 429 slows the client down for the run; a long run of successes eases it back."""
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


if __name__ == "__main__":
    unittest.main()
