from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Location:
    name: str
    code: str = ""  # Rightmove locationIdentifier, e.g. "REGION^1234"
    search_url: str = ""  # or paste a full Rightmove search URL instead
    active: bool = True


@dataclass
class Criteria:
    locations: List[Location]
    min_beds: Optional[int] = None
    max_beds: Optional[int] = None
    min_bathrooms: Optional[int] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    property_types: List[str] = field(default_factory=list)
    must_have: List[str] = field(default_factory=list)
    dont_show: List[str] = field(default_factory=list)
    include_sstc: bool = False
    # Affordability check: flag homes whose deposit you can't cover.
    deposit: Optional[int] = None
    min_deposit_pct: float = 5.0

    @property
    def affordable_max_price(self) -> Optional[int]:
        """Highest price the deposit covers at min_deposit_pct (e.g. £9k at 5% = £180k)."""
        if not self.deposit or self.min_deposit_pct <= 0:
            return None
        return int(self.deposit * 100 / self.min_deposit_pct)
