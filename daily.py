"""Daily house report from saved Rightmove alert emails.

    python daily.py --input inbox/ --out reports/

Reads every .eml/.json/.html in --input (this script never logs in to Gmail;
whoever runs it saves the alert emails there first). Keeps 3-5 bed homes up to
the max price, compares them with data/seen.json to mark new or reduced ones,
adds area facts, then writes reports/<date>/report.html, brief.md and brief.json.
Use --offline to skip all network lookups.
"""
import argparse
import datetime as dt
import os
import sys
from typing import Dict, Iterable, List, Optional

from config import load_criteria
from logger.logger import getMyLogger
from objects.criteria import Criteria
from objects.property import Property
from services import area
from services.alert_email import parse_alert_html, read_alert_bodies
from services.condition import assess
from services.costs import costs
from services.filtering import rejection_reasons
from services.net import Net, OfflineNet
from services.report import write_outputs
from services.seen_store import NEW, PRICE_DROP, SeenStore

log = getMyLogger("daily")


def enrich(p: Property, c: Criteria, net, ctx: Dict) -> Dict:
    text = " | ".join(x for x in (p.property_type, p.address, p.description) if x)
    facts = assess(text)
    geo = area.geocode(p.address, net, ctx.get("contact", ""), near=(c.church["lat"], c.church["lng"])) or {}
    lat, lng = geo.get("lat"), geo.get("lng")
    tier, place = area.church_tier(p.address, geo.get("parish", ""), c.tiers)
    row = {
        "id": p.listing_id, "url": p.url, "address": p.address, "price": p.price, "price_text": p.price_text,
        "beds": p.beds, "type": p.property_type or "unknown", "description": p.description,
        "lat": lat, "lng": lng, "postcode": geo.get("postcode", ""), "parish": geo.get("parish", ""),
        "precision": geo.get("precision", "not found"),
        "tier": tier, "tier_place": place,
        "church_km": round(area.haversine_km(lat, lng, c.church["lat"], c.church["lng"]), 1) if lat is not None else None,
        "crime": area.crime(lat, lng, net) if lat is not None else None,
        "flood": area.flood(lat, lng, net) if lat is not None else None,
        "schools": area.nearest_schools(geo.get("eastings"), geo.get("northings"), ctx.get("schools", []),
                                        c.schools_max_km, c.schools_count),
        "comparables": area.comparables(p.address, geo.get("postcode", ""), p.property_type, ctx.get("sales", [])),
        "costs": costs(p.price or 0, c.deposit or 0, c.mortgage_rate_pct, c.mortgage_term_years) if p.price else None,
        "council_tax_link": area.COUNCIL_TAX_LINK, "flood_link": area.FLOOD_RISK_LINK,
        "alert_said_reduced": p.reduced,
    }
    row.update(facts)
    return row


def load_context(c: Criteria, net, cache_dir: str, contact: str = "") -> Dict:
    ctx = {"contact": contact, "schools": [], "sales": []}
    centre = area.reverse_postcode(c.church["lat"], c.church["lng"], net)
    if centre and centre.get("eastings"):
        ctx["schools"] = area.ensure_schools(net, cache_dir, centre["eastings"], centre["northings"])
    ctx["sales"] = area.ensure_price_paid(net, cache_dir, c.comparables_districts, c.comparables_months)
    return ctx


def run(alert_bodies: Iterable[str], criteria: Criteria, store: SeenStore, out_dir: str, net,
        date: Optional[str] = None, ctx: Optional[Dict] = None, earlier_days: int = 30) -> Dict:
    """The testable core. `alert_bodies` is any iterable of alert email HTML, so a
    caller can inject emails from anywhere (a folder, an API, a test)."""
    date = date or dt.date.today().isoformat()
    ctx = ctx if ctx is not None else {}
    emails, listings, seen_ids = 0, [], set()
    for body in alert_bodies:
        emails += 1
        for p in parse_alert_html(body):
            if p.listing_id not in seen_ids:
                seen_ids.add(p.listing_id)
                listings.append(p)

    rows, rejected = [], []
    for p in listings:
        reasons = rejection_reasons(p, criteria)
        if reasons:
            rejected.append({"id": p.listing_id, "address": p.address, "price": p.price, "reasons": reasons})
            continue
        state = store.check(p)
        old = store.entries().get(p.listing_id, {})
        if state in (NEW, PRICE_DROP):
            row = enrich(p, criteria, net, ctx)
            row["status"] = "new" if state == NEW else "reduced"
            row["reduced_from"] = store.last_price(p) if state == PRICE_DROP else None
            row["first_seen"] = (old.get("extra") or {}).get("first_seen", date)
            row["last_update"] = date
            store.record(p, save=False, extra=row)
        else:
            row = dict(old.get("extra") or enrich(p, criteria, net, ctx))
            row["status"] = "earlier"
        rows.append(row)

    # Earlier finds still worth seeing (from the seen store, no extra database).
    shown = {r["id"] for r in rows}
    cutoff = (dt.date.fromisoformat(date) - dt.timedelta(days=earlier_days)).isoformat()
    for lid, entry in store.entries().items():
        extra = entry.get("extra")
        if lid in shown or not extra or extra.get("last_update", "") < cutoff:
            continue
        r = dict(extra)
        r["status"] = "earlier"
        rows.append(r)
    store.save()

    meta = {"date": date, "emails": emails, "parsed": len(listings)}
    paths = write_outputs(os.path.join(out_dir, date), rows, rejected, meta, criteria)
    return {"paths": paths, "rows": rows, "rejected": rejected, "meta": meta}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="inbox", help="folder (or file) of saved alert emails: .eml, .json, .html")
    ap.add_argument("--out", default="reports", help="output folder; files go in <out>/<date>/")
    ap.add_argument("--criteria", default="data/criteria.json")
    ap.add_argument("--seen", default="data/seen.json")
    ap.add_argument("--cache", default="data/cache", help="cached lookups and monthly datasets")
    ap.add_argument("--date", help="report date (YYYY-MM-DD), default today")
    ap.add_argument("--offline", action="store_true", help="no network lookups (area facts left blank)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.input):
        log.error("Input %s not found. Save the Rightmove alert emails there first.", args.input)
        return 2
    criteria = load_criteria(args.criteria)
    contact = os.environ.get("NOMINATIM_CONTACT", "")
    if args.offline:
        net, ctx = OfflineNet(), {}
    else:
        net = Net(cache_dir=args.cache, contact=contact)
        ctx = load_context(criteria, net, args.cache, contact)
    bodies = [b for _, b in read_alert_bodies(args.input)]
    result = run(bodies, criteria, SeenStore(args.seen), args.out, net, date=args.date, ctx=ctx)
    for name, path in result["paths"].items():
        print(f"{name}: {path}")
    print(f"{sum(r['status'] == 'new' for r in result['rows'])} new, "
          f"{sum(r['status'] == 'reduced' for r in result['rows'])} reduced, "
          f"{len(result['rejected'])} outside criteria")
    return 0


if __name__ == "__main__":
    sys.exit(main())
