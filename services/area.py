"""Location and area facts for a listing, all from free keyless public sources.

  postcodes.io      geocoding (falls back to Nominatim, max 1 request/second)
  data.police.uk    street-level crime within 1 mile, latest published month
  EA flood-monitoring  flood alert/warning areas nearby and any live warnings
  GIAS (DfE)        open primary schools, downloaded once a month
  HM Land Registry  price-paid sales, downloaded once a month

Every lookup is best-effort: on failure the field is left empty and the report
still renders.
"""
import csv
import datetime as dt
import math
import os
import re
import statistics
from typing import Dict, List, Optional, Tuple

from logger.logger import getMyLogger

log = getMyLogger(__name__)

FULL_POSTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b", re.I)
OUTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)(?:\s+\d)?\s*$", re.I)
FLOOD_RISK_LINK = "https://check-long-term-flood-risk.service.gov.uk/postcode"
COUNCIL_TAX_LINK = "https://www.tax.service.gov.uk/check-council-tax-band/search"
CACHE_DAYS = 30


# ---------- distance ----------

def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---------- geocoding ----------

def _from_postcodes_io(r: Dict, precision: str) -> Dict:
    return {
        "lat": r.get("latitude"), "lng": r.get("longitude"),
        "postcode": r.get("postcode") or r.get("outcode") or "",
        "eastings": r.get("eastings"), "northings": r.get("northings"),
        "parish": r.get("parish") or "", "district": r.get("admin_district") or "",
        "lsoa": r.get("lsoa") or "", "precision": precision,
    }


def _first(data) -> Optional[Dict]:
    res = (data or {}).get("result") if isinstance(data, dict) else None
    if isinstance(res, list):
        return res[0] if res else None
    return res


def reverse_postcode(lat: float, lng: float, net) -> Optional[Dict]:
    r = _first(net.get_json("https://api.postcodes.io/postcodes",
                            {"lon": lng, "lat": lat, "limit": 1, "radius": 2000}))
    return _from_postcodes_io(r, "street") if r else None


def _place(name: str, net, near: Optional[Tuple[float, float]], max_km: float = 30) -> Optional[Dict]:
    data = net.get_json("https://api.postcodes.io/places", {"q": name, "limit": 10})
    hits = [r for r in ((data or {}).get("result") or []) if (r.get("name_1") or "").lower() == name.lower()]
    if near:
        hits = [r for r in hits if haversine_km(r["latitude"], r["longitude"], *near) <= max_km]
        hits.sort(key=lambda r: haversine_km(r["latitude"], r["longitude"], *near))
    return hits[0] if hits else None


def geocode(address: str, net, contact: str = "", near: Optional[Tuple[float, float]] = None) -> Optional[Dict]:
    """Best location we can get for an alert address, with a `precision` label:
    postcode > street (Nominatim) > village/town (postcodes.io places) > outcode.
    `near` (lat, lng) biases the search and rules out same-named places far away."""
    if not address:
        return None
    m = FULL_POSTCODE.search(address)
    if m:
        r = _first(net.get_json(f"https://api.postcodes.io/postcodes/{m.group(1)}{m.group(2)}"))
        if r:
            return _from_postcodes_io(r, "postcode")

    params = {"q": address, "format": "jsonv2", "countrycodes": "gb", "limit": 1}
    if near:
        lat, lng = near
        params["viewbox"] = f"{lng - 0.3},{lat + 0.2},{lng + 0.3},{lat - 0.2}"
    if contact:
        params["email"] = contact
    hits = net.get_json("https://nominatim.openstreetmap.org/search", params, min_interval=1.1)
    if hits:
        lat, lng = float(hits[0]["lat"]), float(hits[0]["lon"])
        if not near or haversine_km(lat, lng, *near) <= 30:
            found = reverse_postcode(lat, lng, net) or {"postcode": "", "eastings": None, "northings": None,
                                                         "parish": "", "district": "", "lsoa": ""}
            found.update({"lat": lat, "lng": lng, "precision": "street"})
            return found

    parts = [p.strip() for p in address.split(",") if p.strip()]
    for name in parts[1:]:
        if OUTCODE.fullmatch(name) or FULL_POSTCODE.search(name):
            continue
        r = _place(name, net, near)
        if r:
            lat, lng = r["latitude"], r["longitude"]
            found = reverse_postcode(lat, lng, net) or {"postcode": "", "parish": "", "district": "", "lsoa": ""}
            found.update({"lat": lat, "lng": lng, "eastings": r.get("eastings"), "northings": r.get("northings"),
                          "postcode": "", "precision": "village/town"})
            return found

    m = OUTCODE.search(address.strip())
    if m:
        r = _first(net.get_json(f"https://api.postcodes.io/outcodes/{m.group(1).upper()}"))
        if r:
            out = _from_postcodes_io(r, "outcode")
            out["parish"] = ""
            return out
    return None


# ---------- church tier ----------

def _contains(haystack: str, name: str) -> int:
    m = re.search(r"\b" + re.escape(name) + r"\b", haystack or "", re.I)
    return m.start() if m else -1


def church_tier(address: str, parish: str, tiers: Dict[str, List[str]]) -> Tuple[Optional[int], str]:
    """Tier from the civil parish if known, else the place named earliest in the
    address ("Example Avenue, Barlby, Selby" is Barlby, not Selby)."""
    names = [(int(t), n) for t, ns in tiers.items() for n in ns]
    for tier, name in sorted(names):
        if parish and _contains(parish, name) >= 0:
            return tier, name
    best = None
    for tier, name in names:
        pos = _contains(address, name)
        if pos >= 0 and (best is None or pos < best[0]):
            best = (pos, tier, name)
    return (best[1], best[2]) if best else (None, "")


# ---------- crime and flood ----------

def crime(lat: float, lng: float, net) -> Optional[Dict]:
    data = net.get_json("https://data.police.uk/api/crimes-street/all-crime", {"lat": lat, "lng": lng})
    if not isinstance(data, list):
        return None
    counts: Dict[str, int] = {}
    for c in data:
        counts[c.get("category", "other")] = counts.get(c.get("category", "other"), 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
    return {"total": len(data), "month": data[0].get("month") if data else "",
            "top": [{"category": k.replace("-", " "), "count": v} for k, v in top]}


def flood(lat: float, lng: float, net) -> Optional[Dict]:
    areas = net.get_json("https://environment.data.gov.uk/flood-monitoring/id/floodAreas",
                         {"lat": lat, "long": lng, "dist": 1})
    if areas is None:
        return None
    live = net.get_json("https://environment.data.gov.uk/flood-monitoring/id/floods",
                        {"lat": lat, "long": lng, "dist": 3}, cache=False) or {}
    labels = sorted({a.get("label", "") for a in areas.get("items", []) if a.get("label")})
    active = [w for w in live.get("items", []) if w.get("severityLevel") in (1, 2, 3)]
    return {"areas_within_1km": labels,
            "live_warnings": [f"{w.get('description', '')}: {w.get('severity', '')}" for w in active]}


# ---------- monthly cached datasets ----------

def _fresh(path: str, days: int = CACHE_DAYS) -> bool:
    return os.path.exists(path) and (dt.datetime.now().timestamp() - os.path.getmtime(path)) < days * 86400


SCHOOL_FIELDS = ["URN", "name", "type", "religious", "postcode", "easting", "northing"]
PRIMARY_PHASES = {"Primary", "All-through", "Middle deemed primary"}


def ensure_schools(net, cache_dir: str, centre_e: float, centre_n: float, radius_km: float = 25,
                   today: Optional[dt.date] = None) -> List[Dict]:
    """Open primary schools within radius_km of the church, from the monthly GIAS
    extract (about 60MB, kept only as a small filtered CSV)."""
    path = os.path.join(cache_dir, "schools.csv")
    if not _fresh(path):
        today = today or dt.date.today()
        raw = os.path.join(cache_dir, "gias_raw.csv")
        for back in range(8):
            d = (today - dt.timedelta(days=back)).strftime("%Y%m%d")
            url = f"https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/edubasealldata{d}.csv"
            if net.download(url, raw):
                break
        if os.path.exists(raw):
            rows = []
            with open(raw, encoding="cp1252", newline="") as f:
                for r in csv.DictReader(f):
                    if r.get("EstablishmentStatus (name)") != "Open":
                        continue
                    if r.get("PhaseOfEducation (name)") not in PRIMARY_PHASES:
                        continue
                    try:
                        e, n = float(r["Easting"]), float(r["Northing"])
                    except (KeyError, ValueError):
                        continue
                    if math.hypot(e - centre_e, n - centre_n) <= radius_km * 1000:
                        rows.append({"URN": r["URN"], "name": r["EstablishmentName"],
                                     "type": r.get("TypeOfEstablishment (name)", ""),
                                     "religious": r.get("ReligiousCharacter (name)", ""),
                                     "postcode": r.get("Postcode", ""), "easting": e, "northing": n})
            os.makedirs(cache_dir, exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, SCHOOL_FIELDS)
                w.writeheader()
                w.writerows(rows)
            os.remove(raw)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def nearest_schools(e, n, schools: List[Dict], max_km: float, count: int) -> List[Dict]:
    if e is None or n is None:
        return []
    out = []
    for s in schools:
        km = math.hypot(float(s["easting"]) - e, float(s["northing"]) - n) / 1000
        if km <= max_km:
            religious = s.get("religious", "")
            out.append({"name": s["name"], "km": round(km, 2), "type": s.get("type", ""),
                        "religious": "" if religious in ("", "None", "Does not apply") else religious,
                        "link": f"https://reports.ofsted.gov.uk/provider/21/{s['URN']}",
                        "gias": f"https://get-information-schools.service.gov.uk/Establishments/Establishment/Details/{s['URN']}"})
    return sorted(out, key=lambda s: s["km"])[:count]


def ensure_price_paid(net, cache_dir: str, districts: List[str], months: int,
                      today: Optional[dt.date] = None) -> List[Dict]:
    path = os.path.join(cache_dir, "price_paid.csv")
    if not _fresh(path):
        today = today or dt.date.today()
        since = (today - dt.timedelta(days=int(months * 30.44))).isoformat()
        rows, header = [], None
        for d in districts:
            part = os.path.join(cache_dir, f"ppd_{d}.csv")
            ok = net.download("https://landregistry.data.gov.uk/app/ppd/ppd_data.csv", part, params={
                "header": "true", "limit": "all", "min_date": since, "postcode": d})
            if not ok:
                continue
            with open(part, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                header = reader.fieldnames
                rows.extend(reader)
            os.remove(part)
        if header:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, header)
                w.writeheader()
                w.writerows(rows)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---------- comparables ----------

def type_code(property_type: str) -> Optional[str]:
    t = (property_type or "").lower()
    if "semi" in t:
        return "S"
    if "detached" in t:
        return "D"
    if "terrace" in t or "town house" in t or "townhouse" in t:
        return "T"
    if any(k in t for k in ("flat", "apartment", "maisonette")):
        return "F"
    return None  # bungalows, cottages etc. can be any built form


def street_name(address: str) -> str:
    """'12a Example Road, Selby' -> 'EXAMPLE ROAD'."""
    first = (address or "").split(",")[0]
    first = re.sub(r"^\s*(flat|apartment)\s+\S+\s+", "", first, flags=re.I)
    first = re.sub(r"^\s*\d+[a-z]?(?:-\d+[a-z]?)?\s+", "", first, flags=re.I)
    return first.strip().upper()


def _sector(postcode: str) -> str:
    parts = (postcode or "").upper().split()
    return f"{parts[0]} {parts[1][0]}" if len(parts) == 2 and parts[1] else ""


def _summary(rows: List[Dict]) -> Optional[Dict]:
    prices = [int(r["price_paid"]) for r in rows if r.get("price_paid", "").isdigit()]
    if not prices:
        return None
    latest = max(rows, key=lambda r: r.get("deed_date", ""))
    return {"count": len(prices), "median": int(statistics.median(prices)),
            "latest": {"price": int(latest["price_paid"]), "date": latest.get("deed_date", "")}}


def comparables(address: str, postcode: str, property_type: str, sales: List[Dict]) -> Dict:
    """Same street first; then same postcode sector (or village) and built form.
    Only standard sales (category A) are used."""
    sales = [s for s in sales if s.get("transaction_category", "A") == "A"]
    code = type_code(property_type)
    out: Dict = {"type": code or "any"}
    street = street_name(address)
    if street:
        same = [s for s in sales if s.get("street", "").upper() == street]
        if same:
            out["street"] = dict(_summary(same), label=street.title())
    m = FULL_POSTCODE.search(postcode or "") or FULL_POSTCODE.search(address or "")
    if m:
        sector = f"{m.group(1).upper()} {m.group(2)[0]}"
        pool = [s for s in sales if _sector(s.get("postcode", "")) == sector]
        label = f"{sector} sector"
    else:
        parts = [p.strip().upper() for p in (address or "").split(",")[1:]]
        place = next((p for p in parts if any(s.get("locality", "") == p or s.get("town", "") == p for s in sales)), "")
        pool = [s for s in sales if place and (s.get("locality") == place or (s.get("town") == place and not s.get("locality")))]
        label = place.title()
    if code:
        pool = [s for s in pool if s.get("property_type") == code]
    summ = _summary(pool)
    if summ:
        out["area"] = dict(summ, label=label)
    return out
