"""Search preferences and report settings, from data/criteria.json. No secrets
are needed: every data source used here is free and keyless."""
import json

from objects.criteria import Criteria


def _opt_int(value):
    return None if value in (None, "") else int(value)


def criteria_from_dict(d: dict) -> Criteria:
    mortgage = d.get("mortgage", {})
    comps = d.get("comparables", {})
    schools = d.get("schools", {})
    c = Criteria(
        min_beds=_opt_int(d.get("min_beds")),
        max_beds=_opt_int(d.get("max_beds")),
        min_bathrooms=_opt_int(d.get("min_bathrooms")),
        min_price=_opt_int(d.get("min_price")),
        max_price=_opt_int(d.get("max_price")),
        preferred_max_price=_opt_int(d.get("preferred_max_price")),
        deposit=_opt_int(d.get("deposit")),
        min_deposit_pct=float(d.get("min_deposit_pct", 5)),
        tiers={str(k): list(v) for k, v in d.get("tiers", {}).items()},
        mortgage_rate_pct=float(mortgage.get("rate_pct", 4.5)),
        mortgage_term_years=int(mortgage.get("term_years", 30)),
        comparables_districts=list(comps.get("postcode_districts", ["YO8", "YO19", "DN14", "LS25"])),
        comparables_months=int(comps.get("months", 24)),
        schools_max_km=float(schools.get("max_km", 3)),
        schools_count=int(schools.get("count", 3)),
    )
    if "church" in d:
        c.church = d["church"]
    return c


def load_criteria(path: str) -> Criteria:
    with open(path, "r", encoding="utf-8") as f:
        return criteria_from_dict(json.load(f))
