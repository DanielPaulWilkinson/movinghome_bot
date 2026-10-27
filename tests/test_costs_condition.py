from services.condition import assess, epc_rating
from services.costs import costs, monthly_payment, stamp_duty


def test_stamp_duty_standard_bands():
    assert stamp_duty(120_000) == 0
    assert stamp_duty(205_000) == 1_600
    assert stamp_duty(300_000) == 5_000


def test_stamp_duty_first_time_buyer():
    assert stamp_duty(205_000, first_time_buyer=True) == 0
    assert stamp_duty(400_000, first_time_buyer=True) == 5_000
    # Over £500k there is no relief.
    assert stamp_duty(510_000, first_time_buyer=True) == stamp_duty(510_000) == 15_500


def test_monthly_payment():
    assert monthly_payment(120_000, 0, 10) == 1_000
    assert 985 <= monthly_payment(194_750, 4.5, 30) <= 990
    assert monthly_payment(0, 4.5, 30) == 0


def test_costs_summary():
    c = costs(205_000, 9_000, 4.5, 30)
    assert c["deposit_5"] == 10_250 and c["deposit_10"] == 20_500
    assert c["savings_cover_5pct"] is False
    assert costs(180_000, 9_000, 4.5, 30)["savings_cover_5pct"] is True


def test_condition_and_flags():
    good = assess("Recently refurbished, south-facing garden, driveway. EPC Rating: C. Freehold")
    assert (good["condition"], good["garden"], good["parking"], good["tenure"], good["epc"]) == \
        ("Likely good", "yes", "yes", "Freehold", "C")
    bad = assess("Requires modernisation throughout. Cash buyers only. EPC rating E")
    assert bad["condition"] == "Likely needs work"
    assert assess("3 bedroom house")["condition"] == "Unknown"
    street = assess("Leasehold. On-street parking only. Communal gardens")
    assert (street["parking"], street["garden"], street["tenure"]) == ("on-street", "no", "Leasehold")
    assert "not a survey" in good["condition_note"]


def test_epc_rating():
    assert epc_rating("EPC: B") == "B"
    assert epc_rating("EPC Rating - d") == "D"
    assert epc_rating("no rating here") is None
