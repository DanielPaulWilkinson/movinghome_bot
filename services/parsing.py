"""Pure parsing helpers. No network, no Selenium, so they are easy to test."""
import re
from typing import Optional

_PROPERTY_ID = re.compile(r"/properties/(\d+)")
_NUMBER = re.compile(r"\d[\d,]*")


def parse_price(text: str) -> Optional[int]:
    """'£229,950\\nOffers in Region of' -> 229950. Returns None for 'POA' etc."""
    if not text:
        return None
    match = re.search(r"£\s*(\d[\d,]*)", text) or _NUMBER.search(text)
    if not match:
        return None
    digits = match.group(1) if match.groups() else match.group(0)
    try:
        return int(digits.replace(",", ""))
    except ValueError:
        return None


def parse_int(text) -> Optional[int]:
    """'3' -> 3, '3 bedrooms' -> 3, '' / 'UNKNOWN' / None -> None."""
    if text is None:
        return None
    if isinstance(text, int):
        return text
    match = re.search(r"\d+", str(text))
    return int(match.group(0)) if match else None


def listing_id_from_url(url: str) -> str:
    """Stable key for a listing, ignoring '#/?channel=RES_BUY' and other noise."""
    match = _PROPERTY_ID.search(url or "")
    if match:
        return match.group(1)
    return (url or "").split("#")[0].split("?")[0].rstrip("/")
