"""Decide whether a scraped listing is worth alerting on."""
from typing import List

from objects.criteria import Criteria
from objects.property import Property


def rejection_reasons(p: Property, c: Criteria) -> List[str]:
    """Return why a property fails the criteria (empty list means it passes).

    Unknown values (None) are let through: better a false alert than a missed home.
    """
    reasons = []
    price = p.price
    if price is not None:
        if c.min_price is not None and price < c.min_price:
            reasons.append(f"price £{price:,} below £{c.min_price:,}")
        if c.max_price is not None and price > c.max_price:
            reasons.append(f"price £{price:,} above £{c.max_price:,}")
    if p.beds is not None:
        if c.min_beds is not None and p.beds < c.min_beds:
            reasons.append(f"{p.beds} beds < {c.min_beds}")
        if c.max_beds is not None and p.beds > c.max_beds:
            reasons.append(f"{p.beds} beds > {c.max_beds}")
    if p.bathrooms is not None and c.min_bathrooms is not None:
        if p.bathrooms < c.min_bathrooms:
            reasons.append(f"{p.bathrooms} bathrooms < {c.min_bathrooms}")
    return reasons


def matches(p: Property, c: Criteria) -> bool:
    return not rejection_reasons(p, c)


def is_affordable(p: Property, c: Criteria):
    """True/False against the deposit, or None if we can't tell."""
    limit = c.affordable_max_price
    if limit is None or p.price is None:
        return None
    return p.price <= limit
