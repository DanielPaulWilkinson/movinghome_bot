"""Remembers which listings have been alerted, so each one is sent once.

Keyed by Rightmove listing id (not the full URL), and remembers the last
price so a price drop triggers a fresh alert.
"""
import json
import os
import tempfile
from typing import Dict, Optional

from logger.logger import getMyLogger
from objects.property import Property

logger = getMyLogger(__name__)

NEW = "new"
PRICE_DROP = "price_drop"
SEEN = "seen"


class SeenStore:
    def __init__(self, path: str):
        self.path = path
        self._data: Dict[str, Dict] = self._load()

    def _load(self) -> Dict[str, Dict]:
        if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not read %s, starting with an empty list", self.path)
            return {}

    def _save(self):
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        # Write to a temp file then rename, so a crash can't corrupt the file.
        fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self.path)

    def last_price(self, p: Property) -> Optional[int]:
        entry = self._data.get(p.listing_id)
        return entry.get("price") if entry else None

    def check(self, p: Property) -> str:
        """NEW, PRICE_DROP or SEEN. Does not record anything."""
        entry = self._data.get(p.listing_id)
        if entry is None:
            return NEW
        old, new = entry.get("price"), p.price
        if old is not None and new is not None and new < old:
            return PRICE_DROP
        return SEEN

    def record(self, p: Property, save: bool = True, extra: Optional[Dict] = None):
        """Remember a listing. `extra` (e.g. the enriched report row) is kept with it
        so the report can show earlier finds without a separate database."""
        entry = {"url": p.url, "price": p.price}
        if extra is not None:
            entry["extra"] = extra
        self._data[p.listing_id] = entry
        if save:
            self._save()

    def entries(self) -> Dict[str, Dict]:
        return dict(self._data)

    def save(self):
        self._save()

    def __len__(self):
        return len(self._data)
