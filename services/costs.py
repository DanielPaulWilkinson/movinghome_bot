"""Buying-cost maths. England rates from 1 April 2025. Rates change: check
https://www.gov.uk/stamp-duty-land-tax/residential-property-rates before relying on them."""
from typing import Dict, List, Tuple

STANDARD_BANDS: List[Tuple[float, float]] = [
    (125_000, 0.0), (250_000, 0.02), (925_000, 0.05), (1_500_000, 0.10), (float("inf"), 0.12)]
FTB_BANDS: List[Tuple[float, float]] = [(300_000, 0.0), (500_000, 0.05)]
FTB_MAX_PRICE = 500_000


def _banded(price: float, bands) -> int:
    tax, lower = 0.0, 0.0
    for upper, rate in bands:
        if price > lower:
            tax += (min(price, upper) - lower) * rate
        lower = upper
    return int(round(tax))


def stamp_duty(price: float, first_time_buyer: bool = False) -> int:
    if first_time_buyer and price <= FTB_MAX_PRICE:
        return _banded(price, FTB_BANDS)
    return _banded(price, STANDARD_BANDS)


def monthly_payment(loan: float, rate_pct: float, years: int) -> int:
    n = years * 12
    r = rate_pct / 100 / 12
    if loan <= 0:
        return 0
    if r == 0:
        return int(round(loan / n))
    return int(round(loan * r / (1 - (1 + r) ** -n)))


def costs(price: int, savings: float, rate_pct: float, years: int) -> Dict:
    out = {
        "stamp_duty": stamp_duty(price),
        "stamp_duty_ftb": stamp_duty(price, first_time_buyer=True),
        "savings": savings,
        "rate_pct": rate_pct,
        "term_years": years,
    }
    for pct in (5, 10):
        dep = int(round(price * pct / 100))
        out[f"deposit_{pct}"] = dep
        out[f"monthly_{pct}"] = monthly_payment(price - dep, rate_pct, years)
    out["savings_cover_5pct"] = savings >= out["deposit_5"]
    return out
