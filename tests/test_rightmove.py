import json
from urllib.parse import parse_qs, urlparse

from objects.criteria import Criteria, Location
from services.rightmove_service import build_search_url, parse_search_results, search_location


def crit():
    return Criteria(
        locations=[], min_beds=3, max_beds=4, min_price=100000, max_price=200000,
        property_types=["detached", "terraced"], must_have=["garden"], dont_show=["retirement"],
    )


def test_build_url_from_code():
    url = build_search_url(Location("Selby", code="REGION^1234"), crit())
    q = parse_qs(urlparse(url).query)
    assert q["locationIdentifier"] == ["REGION^1234"]
    assert q["minBedrooms"] == ["3"] and q["maxPrice"] == ["200000"]
    assert q["propertyTypes"] == ["detached,terraced"]
    assert q["sortType"] == ["6"] and q["includeSSTC"] == ["false"]
    assert "index" not in q


def test_build_url_paginates():
    url = build_search_url(Location("Selby", code="REGION^1234"), crit(), page=2)
    assert parse_qs(urlparse(url).query)["index"] == ["48"]


def test_pasted_search_url_wins():
    loc = Location("Selby", code="REGION^1", search_url="https://www.rightmove.co.uk/property-for-sale/find.html?x=1")
    assert build_search_url(loc, crit()) == loc.search_url


def test_unconfigured_location_returns_none():
    assert build_search_url(Location("Selby"), crit()) is None


def _page(properties):
    data = {"props": {"pageProps": {"searchResults": {"properties": properties}}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></html>'


SAMPLE = [
    {
        "id": 111, "bedrooms": 3, "bathrooms": 1, "displayAddress": "Millgate, Selby",
        "propertySubType": "Semi-Detached", "propertyUrl": "/properties/111#/?channel=RES_BUY",
        "price": {"amount": 175000, "displayPrices": [{"displayPrice": "£175,000"}]},
    },
    {"id": 222, "bedrooms": 2, "price": {"amount": 120000}},
    {"id": 111, "bedrooms": 3, "price": {"amount": 175000}},  # duplicate (featured + normal)
]


def test_parse_next_data():
    props = parse_search_results(_page(SAMPLE))
    assert [p.listing_id for p in props] == ["111", "222"]
    first = props[0]
    assert first.price == 175000 and first.beds == 3 and first.bathrooms == 1
    assert first.address == "Millgate, Selby"
    assert first.url == "https://www.rightmove.co.uk/properties/111"
    assert props[1].price_text == "£120,000"


def test_parse_garbage_returns_empty():
    assert parse_search_results("<html>nothing here</html>") == []


def test_search_location_uses_fetcher_and_stops_on_short_page():
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return _page(SAMPLE)

    props = search_location(Location("Selby", code="REGION^1"), crit(), max_pages=3, delay=0, fetcher=fake_fetch)
    assert len(calls) == 1  # fewer than 24 results, so no second page
    assert len(props) == 2
