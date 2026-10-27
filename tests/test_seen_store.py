from objects.property import Property
from services.seen_store import NEW, PRICE_DROP, SEEN, SeenStore


def p(price, url="https://www.rightmove.co.uk/properties/42#/?channel=RES_BUY"):
    return Property(url=url, price_text=price)


def test_new_then_seen_and_persists(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(str(path))
    assert store.check(p("£150,000")) == NEW
    store.record(p("£150,000"))
    assert store.check(p("£150,000")) == SEEN
    # Same listing with a different URL fragment is still the same listing
    assert store.check(p("£150,000", "https://www.rightmove.co.uk/properties/42")) == SEEN
    assert SeenStore(str(path)).check(p("£150,000")) == SEEN


def test_price_drop_detected_but_rise_is_not(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    store.record(p("£150,000"))
    assert store.check(p("£140,000")) == PRICE_DROP
    assert store.check(p("£160,000")) == SEEN


def test_corrupt_file_starts_empty(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("{not json")
    assert len(SeenStore(str(path))) == 0
