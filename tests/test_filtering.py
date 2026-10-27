from objects.criteria import Criteria
from objects.property import Property
from services.filtering import is_affordable, matches, rejection_reasons


def crit(**kw):
    base = dict(locations=[], min_beds=3, max_beds=4, min_bathrooms=1, min_price=100000, max_price=200000)
    base.update(kw)
    return Criteria(**base)


def prop(price="£150,000", beds=3, baths=1):
    return Property(url="https://www.rightmove.co.uk/properties/1", price_text=price, beds=beds, bathrooms=baths)


def test_matching_property_passes():
    assert matches(prop(), crit())


def test_too_expensive_rejected():
    assert "above" in rejection_reasons(prop("£250,000"), crit())[0]


def test_too_few_beds_rejected():
    assert not matches(prop(beds=2), crit())


def test_too_many_beds_rejected():
    assert not matches(prop(beds=5), crit())


def test_unknown_values_are_let_through():
    assert matches(prop(price="POA", beds=None, baths=None), crit())


def test_affordability_from_deposit():
    c = crit(deposit=9000, min_deposit_pct=5)
    assert c.affordable_max_price == 180000
    assert is_affordable(prop("£175,000"), c) is True
    assert is_affordable(prop("£190,000"), c) is False
    assert is_affordable(prop("POA"), c) is None
    assert is_affordable(prop(), crit()) is None  # no deposit set
