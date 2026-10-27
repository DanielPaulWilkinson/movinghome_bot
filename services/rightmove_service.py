"""Rightmove search URL building and result parsing.

IMPORTANT: Rightmove's terms of use prohibit automated access and scraping.
Fetching is therefore OFF by default (RIGHTMOVE_SCRAPE_ENABLED=false) and, when
switched on, is deliberately gentle: robots.txt is checked, one page per
location by default (results are sorted newest first), and a delay between
requests. Parsing is kept separate from fetching so it can be unit tested
without touching the site.
"""
import json
import re
import time
from typing import Iterable, List, Optional
from urllib import robotparser
from urllib.parse import urlencode, urljoin

from logger.logger import getMyLogger
from objects.criteria import Criteria, Location
from objects.property import Property
from services.parsing import parse_int

logger = getMyLogger(__name__)

BASE = "https://www.rightmove.co.uk"
SEARCH_PATH = "/property-for-sale/find.html"
PAGE_SIZE = 24
USER_AGENT = "movinghome_bot/2.0 (personal property alerts)"


class ScrapeError(Exception):
    pass


# ---------------------------------------------------------------- URLs


def build_search_url(location: Location, c: Criteria, page: int = 0) -> Optional[str]:
    """Return the search URL for a location, or None if it isn't configured."""
    if location.search_url:
        url = location.search_url
        if page:
            url += ("&" if "?" in url else "?") + f"index={page * PAGE_SIZE}"
        return url
    if not location.code:
        return None
    params = {"searchType": "SALE", "locationIdentifier": location.code, "sortType": 6}
    for key, value in (
        ("minBedrooms", c.min_beds),
        ("maxBedrooms", c.max_beds),
        ("minPrice", c.min_price),
        ("maxPrice", c.max_price),
    ):
        if value is not None:
            params[key] = value
    if c.property_types:
        params["propertyTypes"] = ",".join(c.property_types)
    if c.must_have:
        params["mustHave"] = ",".join(c.must_have)
    if c.dont_show:
        params["dontShow"] = ",".join(c.dont_show)
    params["includeSSTC"] = str(c.include_sstc).lower()
    if page:
        params["index"] = page * PAGE_SIZE
    return f"{BASE}{SEARCH_PATH}?{urlencode(params)}"


# ---------------------------------------------------------------- parsing


def _find_property_lists(node) -> Iterable[list]:
    """Walk embedded JSON and yield any list that looks like search results."""
    if isinstance(node, dict):
        for key, value in node.items():
            if (
                key == "properties"
                and isinstance(value, list)
                and value
                and isinstance(value[0], dict)
                and "id" in value[0]
            ):
                yield value
            else:
                yield from _find_property_lists(value)
    elif isinstance(node, list):
        for item in node:
            yield from _find_property_lists(item)


def _embedded_json(html: str) -> List[dict]:
    blobs = []
    m = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S
    )
    if m:
        blobs.append(m.group(1))
    m = re.search(r"window\.jsonModel\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if m:
        blobs.append(m.group(1))
    out = []
    for blob in blobs:
        try:
            out.append(json.loads(blob))
        except json.JSONDecodeError:
            logger.warning("Found embedded JSON but could not decode it")
    return out


def _to_property(raw: dict) -> Optional[Property]:
    pid = raw.get("id")
    if not pid:
        return None
    url = raw.get("propertyUrl") or f"/properties/{pid}"
    price = raw.get("price") or {}
    price_text = ""
    if isinstance(price, dict):
        disp = price.get("displayPrices") or []
        if disp and isinstance(disp[0], dict):
            price_text = disp[0].get("displayPrice", "")
        if not price_text and price.get("amount") is not None:
            price_text = f"£{int(price['amount']):,}"
    elif price:
        price_text = str(price)
    return Property(
        url=urljoin(BASE, url.split("#")[0]),
        price_text=price_text,
        address=raw.get("displayAddress", "") or "",
        property_type=raw.get("propertySubType", "") or "",
        beds=parse_int(raw.get("bedrooms")),
        bathrooms=parse_int(raw.get("bathrooms")),
    )


def parse_search_results(html: str) -> List[Property]:
    """Parse a Rightmove search results page into Property objects."""
    results, seen = [], set()
    for data in _embedded_json(html):
        for plist in _find_property_lists(data):
            for raw in plist:
                p = _to_property(raw)
                if p and p.listing_id not in seen:
                    seen.add(p.listing_id)
                    results.append(p)
    return results


# ---------------------------------------------------------------- fetching


_robots = None


def _allowed_by_robots(url: str) -> bool:
    global _robots
    if _robots is None:
        _robots = robotparser.RobotFileParser(urljoin(BASE, "/robots.txt"))
        try:
            _robots.read()
        except OSError:
            logger.warning("Could not read robots.txt; refusing to fetch")
            _robots = None
            return False
    return _robots.can_fetch(USER_AGENT, url)


def fetch(url: str, timeout: int = 20) -> str:
    import requests  # imported lazily so tests don't need it

    if not _allowed_by_robots(url):
        raise ScrapeError(f"robots.txt disallows {url}")
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    if resp.status_code != 200:
        raise ScrapeError(f"HTTP {resp.status_code} from Rightmove")
    return resp.text


def search_location(
    location: Location, c: Criteria, max_pages: int = 1, delay: float = 10.0, fetcher=fetch
) -> List[Property]:
    results: List[Property] = []
    for page in range(max_pages):
        url = build_search_url(location, c, page)
        if url is None:
            logger.warning(
                "Location %s has no 'code' or 'search_url' in criteria.json; skipping",
                location.name,
            )
            return results
        if page:
            time.sleep(delay)
        logger.info("Fetching %s page %d", location.name, page + 1)
        found = parse_search_results(fetcher(url))
        if not found:
            if page == 0:
                logger.warning(
                    "No listings parsed for %s. Either there are none, or Rightmove's "
                    "page structure has changed and the parser needs updating.",
                    location.name,
                )
            break
        results.extend(found)
        if len(found) < PAGE_SIZE:
            break
    return results
