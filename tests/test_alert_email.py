import json
import os

from services.alert_email import parse_alert_html, property_id_from_href, read_alert_bodies, read_alerts

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture_html():
    with open(os.path.join(FIX, "rightmove_alert.html"), encoding="utf-8") as f:
        return f.read()


def by_id(listings):
    return {p.listing_id: p for p in listings}


def test_parses_every_listing_and_ignores_footer():
    found = by_id(parse_alert_html(fixture_html()))
    assert sorted(found) == ["900000001", "900000002", "900000003", "900000004", "900000005"]


def test_fields_from_tracking_wrapped_listing():
    p = by_id(parse_alert_html(fixture_html()))["900000001"]
    assert p.url == "https://www.rightmove.co.uk/properties/900000001"
    assert p.price == 205000
    assert p.beds == 3
    assert p.property_type == "semi-detached house"
    assert p.address == "Example Road, Selby, YO8 4HL"
    assert "driveway" in p.description and "EPC Rating: C" in p.description
    assert not p.reduced


def test_reduced_flag_and_other_listings():
    found = by_id(parse_alert_html(fixture_html()))
    assert found["900000003"].reduced
    assert found["900000003"].price == 199950
    assert found["900000002"].address == "Example Avenue, Barlby, Selby, YO8"
    assert found["900000004"].beds == 2


def test_property_id_from_encoded_hrefs():
    assert property_id_from_href("https://www.rightmove.co.uk/properties/123456789#/") == "123456789"
    assert property_id_from_href("https://t.example/?u=https%3A%2F%2Fwww.rightmove.co.uk%2Fproperties%2F123456789") == "123456789"
    assert property_id_from_href("https://t.example/?u=https%253A%252F%252Fwww.rightmove.co.uk%252Fproperties%252F123456789") == "123456789"
    assert property_id_from_href("https://www.rightmove.co.uk/alerts/edit") is None
    assert property_id_from_href(None) is None


def test_reads_eml_html_part():
    bodies = list(read_alert_bodies(os.path.join(FIX, "rightmove_alert.eml")))
    assert len(bodies) == 1
    assert len(parse_alert_html(bodies[0][1])) == 5


def test_price_fallback_when_no_property_links():
    (p,) = read_alerts(os.path.join(FIX, "rightmove_alert_text.json"))
    assert p.price == 180000 and p.beds == 3 and p.property_type == "bungalow"
    assert p.address.startswith("Example Lane, Thorpe Willoughby")
    assert p.listing_id.startswith("alert-")
    # The fallback id is stable, so the seen store can still de-duplicate it.
    (again,) = read_alerts(os.path.join(FIX, "rightmove_alert_text.json"))
    assert again.listing_id == p.listing_id


def test_directory_read_deduplicates_across_files():
    ids = [p.listing_id for p in read_alerts(FIX)]
    assert len(ids) == len(set(ids)) == 6


def test_json_list_and_unknown_template(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps([{"html": fixture_html()}, {"subject": "no body"}]))
    assert len(read_alerts(str(tmp_path))) == 5
    assert parse_alert_html("<html><body><p>Nothing to see</p></body></html>") == []
