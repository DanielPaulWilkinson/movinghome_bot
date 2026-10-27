from html import escape
from typing import Optional
from urllib.parse import quote_plus

from objects.criteria import Criteria
from objects.property import Property
from services.filtering import is_affordable
from services.seen_store import PRICE_DROP


def _areas(c: Criteria) -> str:
    names = [loc.name for loc in c.locations if loc.active]
    return ", ".join(names) or "no areas yet (edit data/criteria.json)"


def start_message(first_name: str, c: Criteria) -> str:
    return (
        f"<b>Hi {escape(first_name)}</b> 👋\n"
        "I'm here to help you move home.\n\n"
        f"I'm currently watching: {escape(_areas(c))}.\n"
        "Try /find for a search now, or /start_alerts for regular updates.\n"
        "/help explains each command."
    )


def help_message(interval_minutes: int) -> str:
    return (
        "<b>Commands</b> 🤖\n\n"
        "▪️ /find - search now and show anything new 🔍\n"
        f"▪️ /start_alerts - check every {interval_minutes} minutes ⏰\n"
        "▪️ /stop_alerts - stop the regular checks\n"
        "▪️ /criteria - show what I'm searching for"
    )


def criteria_message(c: Criteria) -> str:
    def rng(lo, hi, fmt="{}"):
        lo_s = fmt.format(lo) if lo is not None else "any"
        hi_s = fmt.format(hi) if hi is not None else "any"
        return f"{lo_s} to {hi_s}"

    lines = [
        "<b>Current search</b>",
        f"Areas: {escape(_areas(c))}",
        f"Price: {rng(c.min_price, c.max_price, '£{:,}')}",
        f"Beds: {rng(c.min_beds, c.max_beds)}",
        f"Min bathrooms: {c.min_bathrooms if c.min_bathrooms is not None else 'any'}",
    ]
    if c.affordable_max_price:
        lines.append(
            f"Deposit £{c.deposit:,} at {c.min_deposit_pct:g}% covers up to "
            f"£{c.affordable_max_price:,}"
        )
    return "\n".join(lines)


def property_message(p: Property, c: Criteria, status: str = "new", previous_price: Optional[int] = None) -> str:
    price = f"£{p.price:,}" if p.price is not None else (p.price_text or "Unknown")
    header = "🏠 <b>New listing</b>"
    if status == PRICE_DROP and previous_price and p.price is not None:
        header = f"📉 <b>Price drop</b> (was £{previous_price:,}, down £{previous_price - p.price:,})"
    lines = [header, f"<b>Price</b>: {escape(price)}"]
    affordable = is_affordable(p, c)
    if affordable is False:
        lines.append(
            f"⚠️ Above the £{c.affordable_max_price:,} your £{c.deposit:,} deposit covers at "
            f"{c.min_deposit_pct:g}%"
        )
    if p.address:
        maps = "https://www.google.co.uk/maps/search/" + quote_plus(p.address)
        lines.append(f"<b>Address</b>: <a href=\"{maps}\">{escape(p.address)}</a>")
    if p.property_type:
        lines.append(f"<b>Type</b>: {escape(p.property_type)}")
    if p.beds is not None:
        lines.append(f"<b>Beds</b>: {p.beds}")
    if p.bathrooms is not None:
        lines.append(f"<b>Bathrooms</b>: {p.bathrooms}")
    lines.append(f"<a href=\"{escape(p.url)}\">View on Rightmove</a>")
    return "\n".join(lines)
