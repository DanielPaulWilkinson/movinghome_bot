from config import Settings, criteria_from_dict, load_criteria
from objects.criteria import Criteria, Location
from objects.property import Property
from services.search_service import run_search, select_alerts
from services.seen_store import NEW, PRICE_DROP, SeenStore
from services.telegram_message_service import property_message
from tests.test_rightmove import SAMPLE, _page


def crit():
    return Criteria(locations=[Location("Selby", code="REGION^1")], min_beds=3, max_price=200000, deposit=9000)


def test_select_alerts_filters_and_dedupes(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    good = Property(url="https://www.rightmove.co.uk/properties/1", price_text="£150,000", beds=3)
    small = Property(url="https://www.rightmove.co.uk/properties/2", price_text="£150,000", beds=2)
    first = select_alerts([good, small], crit(), store)
    assert [(p.listing_id, s) for p, s, _ in first] == [("1", NEW)]
    assert select_alerts([good], crit(), store) == []
    cheaper = Property(url=good.url, price_text="£140,000", beds=3)
    (p, status, prev), = select_alerts([cheaper], crit(), store)
    assert status == PRICE_DROP and prev == 150000


def test_run_search_disabled_does_not_fetch(tmp_path):
    def boom(url):
        raise AssertionError("should not fetch")

    s = Settings(token="x", scrape_enabled=False)
    res = run_search(s, crit(), SeenStore(str(tmp_path / "s.json")), fetcher=boom)
    assert res.alerts == [] and res.errors


def test_run_search_end_to_end_with_fake_fetcher(tmp_path):
    s = Settings(token="x", scrape_enabled=True, request_delay_seconds=0)
    res = run_search(s, crit(), SeenStore(str(tmp_path / "s.json")), fetcher=lambda url: _page(SAMPLE))
    assert res.scanned == 2
    assert [p.listing_id for p, _, _ in res.alerts] == ["111"]  # 222 has 2 beds


def test_run_search_survives_a_failing_location(tmp_path):
    def broken(url):
        raise RuntimeError("HTTP 403")

    s = Settings(token="x", scrape_enabled=True, request_delay_seconds=0)
    res = run_search(s, crit(), SeenStore(str(tmp_path / "s.json")), fetcher=broken)
    assert res.alerts == [] and "403" in res.errors[0]


def test_property_message_escapes_and_flags_affordability():
    p = Property(url="https://www.rightmove.co.uk/properties/9", price_text="£190,000", address="<b>Main St</b>", beds=3)
    text = property_message(p, crit())
    assert "&lt;b&gt;Main St&lt;/b&gt;" in text
    assert "£180,000" in text  # deposit warning
    assert "View on Rightmove" in text


def test_price_drop_message():
    p = Property(url="https://www.rightmove.co.uk/properties/9", price_text="£170,000")
    assert "down £5,000" in property_message(p, crit(), PRICE_DROP, 175000)


def test_shipped_criteria_file_loads():
    c = load_criteria("data/criteria.json")
    assert c.affordable_max_price == 180000
    assert c.locations and c.locations[0].name == "Selby"


def test_criteria_defaults():
    c = criteria_from_dict({"locations": [{"name": "A"}]})
    assert c.locations[0].active and c.min_beds is None
