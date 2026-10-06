"""Walmart I/O Affiliate API client: request signing, pacing, retries.

Env: WM_CONSUMER_ID, WM_PRIVATE_KEY (PKCS#8 PEM, or base64 body), WM_KEY_VERSION (default "1").
"""
import base64, os, random, time
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

HOST = "https://developer.api.walmart.com"
API = HOST + "/api-proxy/service/affil/product/v2"


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
                 min_interval=1.25, max_throttle_wait=45 * 60, session=None, log=print):
        self.consumer_id = consumer_id or os.environ["WM_CONSUMER_ID"].strip()
        self.key = _load_key(private_key or os.environ["WM_PRIVATE_KEY"])
        self.key_version = (key_version or os.environ.get("WM_KEY_VERSION") or "1").strip()
        self.min_interval = min_interval          # seconds between requests (429 seen at ~1/s)
        self.max_throttle_wait = max_throttle_wait  # total 429 wait allowed per run before pausing
        self.throttle_waited = 0.0
        self.calls = 0
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

    def get(self, path_or_url: str) -> dict:
        backoff = 5.0
        server_errors = 0
        while True:
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            self.calls += 1
            try:
                r = self.s.get(self.url(path_or_url), headers=self._headers(), timeout=60)
            except requests.RequestException as e:
                server_errors += 1
                if server_errors > 5:
                    raise
                self.log(f"network error ({e}); retry in {backoff:.0f}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
                continue
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                if self.throttle_waited >= self.max_throttle_wait:
                    raise Throttled(f"429 persisted; waited {self.throttle_waited/60:.0f} min this run")
                sleep = backoff + random.uniform(0, 2)
                self.log(f"429 rate limited; sleeping {sleep:.0f}s")
                time.sleep(sleep)
                self.throttle_waited += sleep
                backoff = min(backoff * 2, 300)
                self.min_interval = min(self.min_interval * 1.15, 5.0)  # slow down for the rest of the run
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
