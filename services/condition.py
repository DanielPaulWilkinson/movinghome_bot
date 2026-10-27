"""Rough condition and feature flags from listing text. These are guesses from
the agent's wording, not a survey; the report labels them as estimates."""
import re
from typing import Dict, List, Optional

_EPC = re.compile(r"\bEPC(?:\s+rating)?\s*[:\-]?\s*([A-G])\b", re.I)

NEEDS_WORK = [
    "requires modernisation", "in need of modernisation", "needs modernisation", "modernisation required",
    "in need of updating", "requires updating", "scope to improve", "renovation project", "refurbishment project",
    "cash buyers only", "cash buyer", "investment opportunity", "damp", "subsidence", "fire damaged",
    "probate", "doer upper", "in need of some", "tlc", "updating required",
]
GOOD = [
    "recently refurbished", "newly refurbished", "refurbished", "renovated", "modernised throughout",
    "newly fitted", "new kitchen", "new bathroom", "new boiler", "immaculate", "move in ready", "ready to move",
    "turnkey", "high specification", "well presented", "beautifully presented", "new build", "newly built",
]
GARDEN = re.compile(r"\bgardens?\b|\bgarden\b|\blawn", re.I)
NO_GARDEN = re.compile(r"\bno garden\b|\bcommunal garden", re.I)
PARKING = re.compile(r"driveway|drive way|off[- ]road|off[- ]street|garage|car port|carport|allocated parking|parking space|parking for", re.I)
ONSTREET = re.compile(r"on[- ]street parking|permit parking|no parking", re.I)
TENURE = re.compile(r"\b(freehold|leasehold|share of freehold|commonhold)\b", re.I)


def _hits(text: str, words: List[str]) -> List[str]:
    low = text.lower()
    return [w for w in words if re.search(r"\b" + re.escape(w) + r"\b", low)]


def epc_rating(text: str) -> Optional[str]:
    m = _EPC.search(text or "")
    return m.group(1).upper() if m else None


def assess(text: str) -> Dict:
    text = text or ""
    epc = epc_rating(text)
    bad, good = _hits(text, NEEDS_WORK), _hits(text, GOOD)
    score = len(good) - len(bad)
    if epc in ("A", "B", "C"):
        score += 1
    elif epc in ("E", "F", "G"):
        score -= 1
    if not (bad or good) and epc not in ("A", "B", "C", "E", "F", "G"):
        label = "Unknown"
    elif score >= 1:
        label = "Likely good"
    elif score <= -1:
        label = "Likely needs work"
    else:
        label = "Mixed"
    if NO_GARDEN.search(text):
        garden = "no"
    elif GARDEN.search(text):
        garden = "yes"
    else:
        garden = "unknown"
    if PARKING.search(text):
        parking = "yes"
    elif ONSTREET.search(text):
        parking = "on-street"
    else:
        parking = "unknown"
    t = TENURE.search(text)
    return {
        "condition": label,
        "condition_note": "Estimate from the listing wording and EPC, not a survey",
        "condition_signals": bad + good + ([f"EPC {epc}"] if epc else []),
        "epc": epc,
        "garden": garden,
        "parking": parking,
        "tenure": t.group(1).title() if t else "Unknown",
    }
