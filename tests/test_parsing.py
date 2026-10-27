import pytest

from services.parsing import listing_id_from_url, parse_int, parse_price


@pytest.mark.parametrize(
    "text,expected",
    [
        ("£229,950\nOffers in Region of", 229950),
        ("£150,000", 150000),
        ("Guide Price £1,250,000", 1250000),
        ("POA", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text,expected", [("3", 3), ("3 bedrooms", 3), (2, 2), ("UNKNOWN", None), ("", None), (None, None)])
def test_parse_int(text, expected):
    assert parse_int(text) == expected


def test_listing_id_ignores_fragment_and_query():
    a = "https://www.rightmove.co.uk/properties/138021353#/?channel=RES_BUY"
    b = "https://www.rightmove.co.uk/properties/138021353?foo=bar"
    assert listing_id_from_url(a) == listing_id_from_url(b) == "138021353"
