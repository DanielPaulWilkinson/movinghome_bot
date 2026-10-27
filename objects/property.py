from dataclasses import dataclass
from typing import Optional


@dataclass
class Property:
    url: str
    price_text: str = ""
    address: str = ""
    property_type: str = ""
    beds: Optional[int] = None
    bathrooms: Optional[int] = None

    @property
    def price(self) -> Optional[int]:
        from services.parsing import parse_price

        return parse_price(self.price_text)

    @property
    def listing_id(self) -> str:
        from services.parsing import listing_id_from_url

        return listing_id_from_url(self.url)
