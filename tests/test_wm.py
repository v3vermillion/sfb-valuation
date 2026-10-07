"""Walmart client pacing: a 429 slows the client down for the run; a long run of successes eases it back."""
import unittest
from unittest import mock

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
    """Answers each request with the next scripted status code."""
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.requests = 0

    def get(self, url, headers=None, timeout=None):
        self.requests += 1
        return _Resp(self.statuses.pop(0))


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
        c, _ = _client([429] + [200] * 49 + [429] + [200] * 30 + [500] + [200] * 20 + [200] * 30)
        for _ in range(49):                           # 49 ok after the first 429: no easing yet
            c.get("/x")
        self.assertAlmostEqual(c.min_interval, 1.25 * 1.15)
        c.get("/x")                                   # second 429 resets the streak and slows again
        self.assertAlmostEqual(c.min_interval, 1.25 * 1.15 ** 2)
        for _ in range(29):                           # 30 ok
            c.get("/x")
        c.get("/x")                                   # 500 (retried) -> 200: the streak restarts at 1
        for _ in range(19):                           # 20 ok since the 500
            c.get("/x")
        self.assertAlmostEqual(c.min_interval, 1.25 * 1.15 ** 2, msg="no easing before 50 consecutive successes")
        for _ in range(30):                           # 50 ok since the 500
            c.get("/x")
        self.assertAlmostEqual(c.min_interval, 1.25 * 1.15 ** 2 * 0.9)

    def test_never_below_the_starting_interval_without_a_429(self):
        c, logs = _client([200] * 120, min_interval=2.0)
        for _ in range(120):
            c.get("/x")
        self.assertEqual(c.min_interval, 2.0)
        self.assertEqual(c.base_interval, 2.0)
        self.assertFalse([l for l in logs if l.startswith("pace:")])

    def test_429_backoff_and_wait_cap_are_unchanged(self):
        c, _ = _client([429, 429, 200])
        c.get("/x")
        throttle_sleeps = [s for s in self.sleeps if s >= 5]  # pacing waits are far shorter than the 5 s backoff
        self.assertEqual(len(throttle_sleeps), 2)
        self.assertTrue(5 <= throttle_sleeps[0] <= 7 and 10 <= throttle_sleeps[1] <= 12, throttle_sleeps)
        self.assertAlmostEqual(c.throttle_waited, sum(throttle_sleeps))
        self.assertAlmostEqual(c.min_interval, min(1.25 * 1.15 ** 2, 5.0))
        capped, _ = _client([429, 200], max_throttle_wait=0)
        with self.assertRaises(wm.Throttled):
            capped.get("/x")


if __name__ == "__main__":
    unittest.main()
