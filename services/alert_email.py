"""Turn Rightmove alert emails into Property objects.

Input is a directory of saved emails, so this module never talks to Gmail:
  *.eml   raw RFC 822 messages (the HTML part is used, plain text as fallback)
  *.json  {"subject": ..., "date": ..., "html": "..."} (or "text"), or a list of those
  *.html  just the email body

Rightmove changes its email templates now and then, so the parser leans on a few
stable signals rather than exact markup:
  * every listing links to rightmove.co.uk/properties/<id>, sometimes wrapped in a
    click-tracking redirect (we URL-decode hrefs to find it);
  * every listing has exactly one "£123,456" price;
  * "N bedroom <type>" describes the home.
If no property links are found at all, listings are split on prices instead and
given a stable id made from the address, so de-duplication still works.
"""
import email
import email.policy
import glob
import hashlib
import json
import os
import re
from html import unescape
from html.parser import HTMLParser
from typing import Iterable, List, Optional, Tuple
from urllib.parse import unquote

from objects.property import Property
from services.parsing import parse_int

BASE = "https://www.rightmove.co.uk/properties/"
_PROP_ID = re.compile(r"rightmove\.co\.uk(?:/|%2F)+properties(?:/|%2F)+(\d{6,})", re.I)
_PRICE = re.compile(r"£\s?\d[\d,]{2,}")
_BEDS = re.compile(r"(\d+)\s*(?:bed(?:room)?s?)\b\s*([A-Za-z \-]*?)(?:\s+for sale|$|,)", re.I)
_POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b|\b[A-Z]{1,2}\d[A-Z\d]?\b")
_FOOTER = re.compile(
    r"unsubscribe|manage (your )?alerts|you are receiving|privacy policy|"
    r"edit (this|your) (alert|search)|view all (results|properties)|rightmove plc",
    re.I,
)
_NOISE = re.compile(
    r"^(view (property|details)|see more|more details|save|new|added (today|yesterday)|"
    r"just added|reduced( today| yesterday)?|price reduced|featured property|property image|new property)$",
    re.I,
)
_SKIP_TAGS = {"style", "script", "head", "title"}
_BLOCK_TAGS = {"p", "div", "td", "tr", "li", "br", "h1", "h2", "h3", "h4", "table", "span"}


class _Tokens(HTMLParser):
    """Collects (text, href) pairs; href is the enclosing link, if any."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens: List[Tuple[str, Optional[str]]] = []
        self._href: List[Optional[str]] = []
        self._skip = 0
        self._buf = ""

    def _flush(self):
        text = re.sub(r"\s+", " ", self._buf).strip()
        if text:
            self.tokens.append((text, self._href[-1] if self._href else None))
        self._buf = ""

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        if tag in _BLOCK_TAGS or tag == "a":
            self._flush()
        if tag == "a":
            self._href.append(dict(attrs).get("href"))
        elif tag == "img":
            # Listing images usually sit inside the property link: record the link.
            alt = dict(attrs).get("alt") or ""
            self.tokens.append((alt.strip(), self._href[-1] if self._href else None))

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        if tag in _BLOCK_TAGS or tag == "a":
            self._flush()
        if tag == "a" and self._href:
            self._href.pop()

    def handle_data(self, data):
        if not self._skip:
            self._buf += data

    def close(self):
        super().close()
        self._flush()


def property_id_from_href(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    for candidate in (href, unquote(href), unquote(unquote(href))):
        m = _PROP_ID.search(candidate)
        if m:
            return m.group(1)
    return None


def _tokens(html: str) -> List[Tuple[str, Optional[str]]]:
    p = _Tokens()
    p.feed(html)
    p.close()
    return p.tokens


def _blocks_by_link(tokens) -> List[Tuple[str, List[str]]]:
    blocks, current_id, texts = [], None, []
    for text, href in tokens:
        if _FOOTER.search(text):
            break
        pid = property_id_from_href(href)
        if pid and pid != current_id and pid not in [b[0] for b in blocks]:
            if current_id:
                blocks.append((current_id, texts))
            current_id, texts = pid, []
        if current_id and text:
            texts.append(text)
    if current_id:
        blocks.append((current_id, texts))
    return blocks


def _blocks_by_price(tokens) -> List[Tuple[Optional[str], List[str]]]:
    """Fallback: a listing starts at each price. Text just before a price that
    looks like a heading ("3 bedroom house") is pulled into that listing."""
    blocks: List[List[str]] = []
    pending: List[str] = []
    for text, _ in tokens:
        if _FOOTER.search(text):
            break
        if not text:
            continue
        if _PRICE.search(text):
            blocks.append(pending + [text])
            pending = []
        elif blocks and not (_BEDS.search(text) and any(_BEDS.search(t) for t in blocks[-1])):
            blocks[-1].append(text)
        else:
            pending.append(text)
    return [(None, b) for b in blocks]


def _address(texts: List[str]) -> str:
    for t in texts:
        if _PRICE.search(t) or _BEDS.search(t) or _NOISE.match(t) or len(t) > 120:
            continue
        if "," in t or _POSTCODE.search(t):
            return t
    return ""


def _parse_block(pid: Optional[str], texts: List[str]) -> Optional[Property]:
    reduced = any(re.search(r"\breduced\b|price (drop|change)", t, re.I) for t in texts)
    texts = [t for t in texts if t and not _NOISE.match(t)] or texts
    joined = " | ".join(texts)
    price = _PRICE.search(joined)
    if not price:
        return None
    beds = ptype = None
    m = _BEDS.search(joined)
    if m:
        beds = parse_int(m.group(1))
        ptype = (m.group(2) or "").strip().rstrip("|").strip() or None
    address = _address(texts)
    alert_id = ""
    if not pid:
        key = re.sub(r"\W+", "", address.lower()) + f"|{beds}"
        alert_id = "alert-" + hashlib.sha1(key.encode()).hexdigest()[:12]
    rest = [t for t in texts if t != address and not _PRICE.fullmatch(t.strip())]
    return Property(
        url=f"{BASE}{pid}" if pid else "",
        price_text=price.group(0),
        address=address,
        property_type=ptype or "",
        beds=beds,
        description=" | ".join(rest),
        reduced=reduced,
        alert_id=alert_id,
    )


def parse_alert_html(html: str) -> List[Property]:
    tokens = _tokens(html)
    blocks = _blocks_by_link(tokens) or _blocks_by_price(tokens)
    out, seen = [], set()
    for pid, texts in blocks:
        p = _parse_block(pid, texts)
        if p and p.listing_id not in seen:
            seen.add(p.listing_id)
            out.append(p)
    return out


def _text_to_html(text: str) -> str:
    """Plain-text alerts: keep URLs as links so property ids are found."""
    from html import escape

    lines = []
    for line in text.splitlines():
        line = line.strip()
        url = re.search(r"https?://\S+", line)
        if url:
            lines.append(f'<p><a href="{escape(url.group(0))}">{escape(line)}</a></p>')
        elif line:
            lines.append(f"<p>{escape(line)}</p>")
    return "\n".join(lines)


def _bodies_from_eml(raw: bytes) -> List[str]:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    html = msg.get_body(preferencelist=("html",))
    if html is not None:
        return [html.get_content()]
    text = msg.get_body(preferencelist=("plain",))
    return [_text_to_html(text.get_content())] if text is not None else []


def _bodies_from_json(data) -> List[str]:
    items = data if isinstance(data, list) else [data]
    bodies = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("html"):
            bodies.append(item["html"])
        elif item.get("text") or item.get("body"):
            bodies.append(_text_to_html(item.get("text") or item.get("body")))
    return bodies


def read_alert_bodies(path: str) -> Iterable[Tuple[str, str]]:
    """Yield (filename, html) for every saved email in a file or directory."""
    files = [path] if os.path.isfile(path) else sorted(
        f for ext in ("eml", "json", "html", "htm") for f in glob.glob(os.path.join(path, f"*.{ext}"))
    )
    for f in files:
        with open(f, "rb") as fh:
            raw = fh.read()
        if f.endswith(".eml"):
            bodies = _bodies_from_eml(raw)
        elif f.endswith(".json"):
            bodies = _bodies_from_json(json.loads(raw.decode("utf-8")))
        else:
            bodies = [raw.decode("utf-8", "replace")]
        for b in bodies:
            yield f, unescape(b) if "&lt;a" in b else b


def read_alerts(path: str) -> List[Property]:
    found, seen = [], set()
    for _, html in read_alert_bodies(path):
        for p in parse_alert_html(html):
            if p.listing_id not in seen:
                seen.add(p.listing_id)
                found.append(p)
    return found
