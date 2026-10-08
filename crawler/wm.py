"""Walmart I/O Affiliate API client: request signing, pacing, retries.

Env: WM_CONSUMER_ID, WM_PRIVATE_KEY (PKCS#8 PEM, or base64 body), WM_KEY_VERSION (default "1").

Pacing has three layers, all measured against request start times:
  min_interval   seconds between consecutive requests (1.25 s; a 429 raises it 15% up to 5 s,
                 50 consecutive successes ease it back 10% at a time, never below the start value)
  max_per_min    optional sliding-window cap: a request waits until fewer than max_per_min requests
                 fall inside the last 60 s. Applied on top of min_interval, never instead of it.
                 crawl.run sets it from state.pace.per_min, which crawler/throttle.py infers from the
                 event log of the previous run.
  429 back-off   5 s doubling to 300 s (+0-2 s jitter) per consecutive 429; Throttled once a run has
                 waited max_throttle_wait (45 min) in total.
Every HTTP attempt and every 429 back-off sleep is appended to `events` so the run can be analysed
afterwards: (request_start_epoch, status) with status 200/429/5xx or 0 for a network error, and
(epoch, "sleep", seconds) for each back-off sleep. drain_events() hands the list over and clears it.
"""
import base64, os, random, time
from collections import deque
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

HOST = "https://developer.api.walmart.com"
API = HOST + "/api-proxy/service/affil/product/v2"


RECOVER_AFTER = 50      # consecutive successful requests before the pace eases
RECOVER_STEP = 0.10     # fraction of min_interval removed at each easing
WINDOW_S = 60.0         # length of the sliding window max_per_min applies to
CAP_CUT_PCT = 85        # a 429 under a cap lowers it to this percentage for the rest of the run ...
CAP_FLOOR = 6           # ... never below this (throttle.MIN_PER_MIN); recovery raises it back towards the start cap


class Throttled(Exception):
    """Raised when Walmart keeps returning 429 beyond the allowed wait budget."""


def _load_key(raw: str):
    raw = raw.replace("\\n", "\n").strip()
    if "BEGIN" not in raw:
        body = "".join(raw.split())
        raw = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(body[i:i + 64] for i in range(0, len(body), 64)) + "\n-----END PRIVATE KEY-----"
    return serialization.load_pem_private_key(raw.encode(), password=None)


class Walmart:
    def __init__(self, consumer_id=None, private_key=None, key_version=None,
                 min_interval=1.25, max_throttle_wait=45 * 60, session=None, log=print, max_per_min=None):
        self.consumer_id = consumer_id or os.environ["WM_CONSUMER_ID"].strip()
        self.key = _load_key(private_key or os.environ["WM_PRIVATE_KEY"])
        self.key_version = (key_version or os.environ.get("WM_KEY_VERSION") or "1").strip()
        self.min_interval = min_interval          # seconds between requests (429 seen at ~1/s)
        self.base_interval = min_interval         # the floor pacing recovers back to
        self.max_throttle_wait = max_throttle_wait  # total 429 wait allowed per run before pausing
        self.max_per_min = int(max_per_min) if max_per_min else None  # sliding-window cap; None = interval only
        self.base_per_min = self.max_per_min       # the cap the run started with; in-run recovery stops there
        self._ok_streak = 0                       # consecutive 200s since the last non-success
        self.throttle_waited = 0.0                # seconds slept in 429 back-off this run
        self.cap_waited = 0.0                     # seconds waited for the sliding window to make room
        self.calls = 0
        self.n429 = 0
        self.events = []                          # see module docstring; drained by crawl.run
        self._window = deque()                    # request start times inside the last WINDOW_S seconds
        self._last = 0.0
        self.s = session or requests.Session()
        self.log = log

    def _headers(self):
        ts = str(int(time.time() * 1000))
        msg = f"{self.consumer_id}\n{ts}\n{self.key_version}\n".encode()
        sig = self.key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
        return {
            "WM_CONSUMER.ID": self.consumer_id,
            "WM_CONSUMER.INTIMESTAMP": ts,
            "WM_SEC.KEY_VERSION": self.key_version,
            "WM_SEC.AUTH_SIGNATURE": base64.b64encode(sig).decode(),
            "Accept": "application/json",
        }

    @staticmethod
    def url(path_or_url: str) -> str:
        if path_or_url.startswith("http"):
            return path_or_url
        if path_or_url.startswith("/api-proxy/"):
            return HOST + path_or_url
        return API + path_or_url

    def _wait_for_window(self):
        """Block until fewer than max_per_min requests started inside the last WINDOW_S seconds."""
        while True:
            now = time.time()
            while self._window and self._window[0] <= now - WINDOW_S:
                self._window.popleft()
            if len(self._window) < self.max_per_min:
                return
            wait = self._window[0] + WINDOW_S - now
            if wait > 0:
                time.sleep(wait)
                self.cap_waited += wait

    def _record(self, status):
        self.events.append((round(self._last, 3), status))

    def get(self, path_or_url: str) -> dict:
        backoff = 5.0
        server_errors = 0
        while True:
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            if self.max_per_min:
                self._wait_for_window()
            self._last = time.time()
            if self.max_per_min:
                self._window.append(self._last)
            self.calls += 1
            try:
                r = self.s.get(self.url(path_or_url), headers=self._headers(), timeout=60)
            except requests.RequestException as e:
                self._record(0)
                self._ok_streak = 0
                server_errors += 1
                if server_errors > 5:
                    raise
                self.log(f"network error ({e}); retry in {backoff:.0f}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
                continue
            self._record(r.status_code)
            if r.status_code == 200:
                try:
                    data = r.json()
                except ValueError:
                    # a truncated or HTML body behind a 200: retried like a server error, never a crash
                    data, r.status_code = None, 502
                if data is not None or r.status_code == 200:
                    self._recover_pace()
                    return data
            self._ok_streak = 0
            if r.status_code == 429:
                self.n429 += 1
                if self.throttle_waited >= self.max_throttle_wait:
                    raise Throttled(f"429 persisted; waited {self.throttle_waited/60:.0f} min this run")
                sleep = backoff + random.uniform(0, 2)
                self.log(f"429 rate limited; sleeping {sleep:.0f}s")
                self.events.append((round(time.time(), 3), "sleep", round(sleep, 3)))
                time.sleep(sleep)
                self.throttle_waited += sleep
                backoff = min(backoff * 2, 300)
                self.min_interval = min(self.min_interval * 1.15, 5.0)  # slow down for the rest of the run
                if self.max_per_min:
                    # the interval alone cannot go below 12/min, so a cap one step above a tight limit would keep
                    # tripping it for the whole run: the cap itself comes down too (and recovers below)
                    self.max_per_min = max(min(CAP_FLOOR, self.max_per_min), self.max_per_min * CAP_CUT_PCT // 100)
                continue
            if r.status_code >= 500:
                server_errors += 1
                if server_errors > 5:
                    r.raise_for_status()
                self.log(f"HTTP {r.status_code}; retry in {backoff:.0f}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
                continue
            raise RuntimeError(f"HTTP {r.status_code} for {path_or_url}: {r.text[:500]}")

    def _recover_pace(self):
        """A 429 raises min_interval for the rest of the run (see get); this lets it come back down.
        After every RECOVER_AFTER consecutive successful requests the interval drops by RECOVER_STEP,
        never below the interval the client started with."""
        self._ok_streak += 1
        if self._ok_streak % RECOVER_AFTER:
            return
        if self.min_interval > self.base_interval:
            self.min_interval = max(self.base_interval, self.min_interval * (1 - RECOVER_STEP))
            self.log(f"pace: {self._ok_streak} ok in a row; interval back to {self.min_interval:.2f}s")
        if self.max_per_min and self.base_per_min and self.max_per_min < self.base_per_min:
            self.max_per_min = min(self.base_per_min, max(self.max_per_min + 1, self.max_per_min * 110 // 100))
            self.log(f"pace: {self._ok_streak} ok in a row; cap back to {self.max_per_min}/min")

    ITEMS_CHUNK = 20   # the /items endpoint accepts up to 20 ids per request

    def get_items(self, ids) -> list:
        """Fetch items by Walmart item id: `/items?ids=<comma list>`, at most ITEMS_CHUNK ids per
        request, every request through `get` (so the pacing, 429 back-off and retries apply).
        Returns the concatenated item dicts; ids Walmart no longer knows are simply absent."""
        ids = [str(i).strip() for i in (ids or []) if str(i).strip()]
        out = []
        for i in range(0, len(ids), self.ITEMS_CHUNK):
            page = self.get(f"/items?ids={','.join(ids[i:i + self.ITEMS_CHUNK])}")
            items = page.get("items") if isinstance(page, dict) else page
            out.extend(it for it in (items or []) if isinstance(it, dict))
        return out

    def drain_events(self) -> list:
        """Return the events recorded since the last drain and forget them."""
        events, self.events = self.events, []
        return events

    def stats(self) -> dict:
        return {"requests": self.calls, "status_429": self.n429,
                "sleep_s": round(self.throttle_waited, 1), "cap_wait_s": round(self.cap_waited, 1),
                "max_per_min": self.max_per_min, "min_interval": round(self.min_interval, 3)}
