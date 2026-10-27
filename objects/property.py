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
    description: str = ""  # all other listing text from the alert (features, summary)
    reduced: bool = False  # the alert itself said "reduced"
    alert_id: str = ""  # fallback id when the alert has no Rightmove property link

    @property
    def price(self) -> Optional[int]:
        from services.parsing import parse_price

        return parse_price(self.price_text)

    @property
    def listing_id(self) -> str:
        from services.parsing import listing_id_from_url

        if self.alert_id and "/properties/" not in (self.url or ""):
            return self.alert_id
        return listing_id_from_url(self.url)
