from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Criteria:
    """What Daniel is looking for, plus the settings the report needs.

    Loaded from data/criteria.json (see config.load_criteria)."""

    min_beds: Optional[int] = None
    max_beds: Optional[int] = None
    min_bathrooms: Optional[int] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    preferred_max_price: Optional[int] = None
    deposit: Optional[int] = None
    min_deposit_pct: float = 5.0
    church: Dict = field(default_factory=lambda: {"name": "St James the Apostle, Selby", "lat": 53.78252, "lng": -1.07128})
    tiers: Dict[str, List[str]] = field(default_factory=dict)
    mortgage_rate_pct: float = 4.5
    mortgage_term_years: int = 30
    comparables_districts: List[str] = field(default_factory=lambda: ["YO8", "YO19", "DN14", "LS25"])
    comparables_months: int = 24
    schools_max_km: float = 3.0
    schools_count: int = 3

    @property
    def affordable_max_price(self) -> Optional[int]:
        """Highest price the deposit covers at min_deposit_pct (e.g. £9k at 5% = £180k)."""
        if not self.deposit or self.min_deposit_pct <= 0:
            return None
        return int(self.deposit * 100 / self.min_deposit_pct)
