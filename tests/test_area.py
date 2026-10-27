from services import area
from tests.fakes import FakeNet

TIERS = {"1": ["Selby", "Brayton"], "2": ["Thorpe Willoughby", "Barlby", "Osgodby"], "3": ["Riccall", "Carlton"]}
CHURCH = (53.78252, -1.07128)


def test_haversine_church_to_brayton():
    assert 1.5 < area.haversine_km(*CHURCH, 53.7685, -1.0890) < 2.5


def test_church_tier_prefers_parish_then_earliest_place():
    assert area.church_tier("1 Example Avenue, Selby", "Barlby with Osgodby", TIERS) == (2, "Barlby")
    assert area.church_tier("Example Avenue, Barlby, Selby, YO8", "", TIERS) == (2, "Barlby")
    assert area.church_tier("Leeds Road, Selby", "Selby", TIERS) == (1, "Selby")
    assert area.church_tier("Main Street, Riccall, York", "", TIERS) == (3, "Riccall")
    assert area.church_tier("High Street, Snaith, Goole", "Snaith and Cowick", TIERS) == (None, "")


def test_geocode_full_postcode_uses_postcodes_io():
    net = FakeNet({"https://api.postcodes.io/postcodes/YO84HL": {"result": {
        "latitude": 53.78, "longitude": -1.07, "postcode": "YO8 4HL", "eastings": 461300,
        "northings": 432100, "parish": "Selby", "admin_district": "North Yorkshire"}}})
    g = area.geocode("Example Road, Selby, YO8 4HL", net)
    assert g["precision"] == "postcode" and g["parish"] == "Selby" and g["eastings"] == 461300


def test_geocode_falls_back_to_nominatim_then_reverse_postcode():
    net = FakeNet({
        "https://nominatim.openstreetmap.org/search": [{"lat": "53.7700", "lon": "-1.1260"}],
        "https://api.postcodes.io/postcodes": {"result": [{"latitude": 53.771, "longitude": -1.127,
                                                           "postcode": "YO8 9NB", "eastings": 457700,
                                                           "northings": 431400, "parish": "Thorpe Willoughby"}]},
    })
    g = area.geocode("Fox Lane, Thorpe Willoughby, Selby", net, near=CHURCH)
    assert g["precision"] == "street" and g["lat"] == 53.77 and g["parish"] == "Thorpe Willoughby"
    url, params = next(c for c in net.calls if "nominatim" in c[0])
    assert params["countrycodes"] == "gb" and "viewbox" in params


def test_geocode_place_fallback_picks_nearest_same_name():
    carltons = {"result": [
        {"name_1": "Carlton", "latitude": 54.59, "longitude": -1.39, "eastings": 1, "northings": 1},
        {"name_1": "Carlton", "latitude": 53.71, "longitude": -1.02, "eastings": 464000, "northings": 424500},
    ]}
    net = FakeNet({"https://api.postcodes.io/places?q=Carlton": carltons})
    g = area.geocode("Example Lane, Carlton, Goole, DN14", net, near=CHURCH)
    assert g["precision"] == "village/town" and g["lat"] == 53.71


def test_geocode_gives_up_quietly():
    assert area.geocode("Nowhere", FakeNet()) is None
    assert area.geocode("", FakeNet()) is None


def test_crime_and_flood_summaries():
    crimes = [{"category": "anti-social-behaviour", "month": "2026-08"}] * 3 + [{"category": "burglary", "month": "2026-08"}]
    net = FakeNet({
        "https://data.police.uk/api/crimes-street/all-crime": crimes,
        "https://environment.data.gov.uk/flood-monitoring/id/floodAreas": {"items": [{"label": "River Ouse at Selby"}]},
        "https://environment.data.gov.uk/flood-monitoring/id/floods": {"items": [
            {"description": "River Ouse", "severity": "Flood alert", "severityLevel": 3},
            {"description": "Old one", "severity": "Warning no longer in force", "severityLevel": 4}]},
    })
    c = area.crime(53.78, -1.07, net)
    assert c["total"] == 4 and c["top"][0] == {"category": "anti social behaviour", "count": 3}
    f = area.flood(53.78, -1.07, net)
    assert f["areas_within_1km"] == ["River Ouse at Selby"]
    assert f["live_warnings"] == ["River Ouse: Flood alert"]
    assert area.crime(0, 0, FakeNet()) is None and area.flood(0, 0, FakeNet()) is None


def test_nearest_schools():
    schools = [
        {"URN": "1", "name": "Near", "easting": "461300", "northing": "432200", "religious": "Church of England"},
        {"URN": "2", "name": "Mid", "easting": "462300", "northing": "432200", "religious": "Does not apply"},
        {"URN": "3", "name": "Far", "easting": "470000", "northing": "432200", "religious": ""},
    ]
    out = area.nearest_schools(461300, 432100, schools, max_km=3, count=3)
    assert [s["name"] for s in out] == ["Near", "Mid"]
    assert out[0]["religious"] == "Church of England" and out[1]["religious"] == ""
    assert out[0]["link"].endswith("/1")
    assert area.nearest_schools(None, None, schools, 3, 3) == []


def sale(price, pc, street, t, date="2026-05-01", locality="", town="SELBY", cat="A"):
    return {"price_paid": str(price), "postcode": pc, "street": street, "property_type": t, "deed_date": date,
            "locality": locality, "town": town, "transaction_category": cat}


def test_comparables_street_sector_and_village():
    sales = [
        sale(180000, "YO8 4HA", "EXAMPLE ROAD", "S"), sale(200000, "YO8 4HB", "OTHER ROAD", "S", "2026-07-01"),
        sale(300000, "YO8 4HC", "OTHER ROAD", "D"), sale(150000, "YO8 5AA", "FAR ROAD", "S"),
        sale(999999, "YO8 4HD", "EXAMPLE ROAD", "S", cat="B"),
        sale(260000, "YO8 5BB", "VILLAGE LANE", "D", locality="BARLBY"),
    ]
    c = area.comparables("12 Example Road, Selby, YO8 4HL", "YO8 4HL", "semi-detached house", sales)
    assert c["street"]["count"] == 1 and c["street"]["median"] == 180000
    assert c["area"]["label"] == "YO8 4 sector" and c["area"]["count"] == 2 and c["area"]["median"] == 190000
    assert c["area"]["latest"]["date"] == "2026-07-01"
    v = area.comparables("Example Avenue, Barlby, Selby, YO8", "", "detached house", sales)
    assert v["area"]["label"] == "Barlby" and v["area"]["count"] == 1
    assert area.comparables("x", "", "", []) == {"type": "any"}


def test_street_name_and_type_code():
    assert area.street_name("12a Example Road, Selby") == "EXAMPLE ROAD"
    assert area.street_name("Flat 3 4 Park Street, Selby") == "PARK STREET"
    assert area.street_name("Example Road, Selby") == "EXAMPLE ROAD"
    assert [area.type_code(t) for t in ("semi-detached house", "detached house", "end of terrace house", "flat", "bungalow")] \
        == ["S", "D", "T", "F", None]
