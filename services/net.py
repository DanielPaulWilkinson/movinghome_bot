"""Tiny HTTP helper: one place for the User-Agent, timeouts, polite delays and a
JSON response cache. Tests pass a fake object with the same two methods, so no
test touches the network."""
import hashlib
import json
import os
import time
from typing import Any, Dict, Optional

import requests

from logger.logger import getMyLogger

log = getMyLogger(__name__)

USER_AGENT = "movinghome_bot/2.0 (personal house-hunting report; +https://github.com/DanielPaulWilkinson/movinghome_bot)"


class Net:
    def __init__(self, cache_dir: Optional[str] = "data/cache", contact: Optional[str] = None,
                 cache_hours: float = 24 * 7):
        self.cache_dir = cache_dir
        self.cache_hours = cache_hours
        self.session = requests.Session()
        ua = USER_AGENT + (f" contact: {contact}" if contact else "")
        self.session.headers["User-Agent"] = ua
        self._last_call: Dict[str, float] = {}

    def _wait(self, host_key: str, min_interval: float):
        last = self._last_call.get(host_key, 0.0)
        delay = min_interval - (time.monotonic() - last)
        if delay > 0:
            time.sleep(delay)
        self._last_call[host_key] = time.monotonic()

    def _cache_path(self, url: str, params: Optional[dict]) -> Optional[str]:
        if not self.cache_dir:
            return None
        key = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
        return os.path.join(self.cache_dir, "http", key + ".json")

    def get_json(self, url: str, params: Optional[dict] = None, min_interval: float = 0.2,
                 cache: bool = True) -> Any:
        """GET and decode JSON. Returns None on any error (enrichment is best-effort)."""
        path = self._cache_path(url, params) if cache else None
        if path and os.path.exists(path) and time.time() - os.path.getmtime(path) < self.cache_hours * 3600:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        self._wait(url.split("/")[2], min_interval)
        try:
            r = self.session.get(url, params=params, timeout=30)
            if r.status_code == 404:
                data = None
            else:
                r.raise_for_status()
                data = r.json()
        except (requests.RequestException, ValueError) as e:
            log.warning("GET %s failed: %s", url, e)
            return None
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        return data

    def download(self, url: str, dest: str, params: Optional[dict] = None, timeout: int = 300) -> bool:
        try:
            with self.session.get(url, params=params, timeout=timeout, stream=True) as r:
                r.raise_for_status()
                os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
                tmp = dest + ".part"
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
                os.replace(tmp, dest)
                return True
        except requests.RequestException as e:
            log.warning("download %s failed: %s", url, e)
            return False


class OfflineNet:
    """Used with --offline: every lookup quietly returns nothing."""

    def get_json(self, *a, **k):
        return None

    def download(self, *a, **k):
        return False
