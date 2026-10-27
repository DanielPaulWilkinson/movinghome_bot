"""One search run: fetch each location, filter, de-duplicate. Shared by /find
and the scheduled alerts so the two can't drift apart (they had in v1)."""
import time
from dataclasses import dataclass, field
from typing import List, Tuple

from config import Settings
from logger.logger import getMyLogger
from objects.criteria import Criteria
from objects.property import Property
from services import rightmove_service
from services.filtering import rejection_reasons
from services.seen_store import NEW, PRICE_DROP, SeenStore

logger = getMyLogger(__name__)


@dataclass
class SearchResult:
    alerts: List[Tuple[Property, str, object]] = field(default_factory=list)
    scanned: int = 0
    errors: List[str] = field(default_factory=list)


def select_alerts(properties: List[Property], c: Criteria, store: SeenStore):
    """Pure-ish core: which properties deserve an alert, and why.

    Returns [(property, status, previous_price)] and records them in the store.
    """
    alerts = []
    for p in properties:
        reasons = rejection_reasons(p, c)
        if reasons:
            logger.debug("Skipping %s: %s", p.url, "; ".join(reasons))
            continue
        status = store.check(p)
        if status in (NEW, PRICE_DROP):
            alerts.append((p, status, store.last_price(p)))
            store.record(p, save=False)
    if alerts:
        store.save()
    return alerts


def run_search(settings: Settings, c: Criteria, store: SeenStore, fetcher=None) -> SearchResult:
    result = SearchResult()
    if not settings.scrape_enabled:
        result.errors.append(
            "Rightmove fetching is switched off (RIGHTMOVE_SCRAPE_ENABLED=false). "
            "See the README before turning it on."
        )
        return result
    fetcher = fetcher or rightmove_service.fetch
    found: List[Property] = []
    active = [loc for loc in c.locations if loc.active]
    for i, loc in enumerate(active):
        if i:
            time.sleep(settings.request_delay_seconds)
        try:
            found.extend(
                rightmove_service.search_location(
                    loc, c, settings.max_pages, settings.request_delay_seconds, fetcher
                )
            )
        except Exception as exc:  # one bad location shouldn't stop the rest
            logger.exception("Search failed for %s", loc.name)
            result.errors.append(f"{loc.name}: {exc}")
    result.scanned = len(found)
    result.alerts = select_alerts(found, c, store)
    return result
