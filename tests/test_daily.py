import json
import os
import re

import daily
from config import load_criteria
from services.seen_store import SeenStore
from tests.fakes import FakeNet

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")


def html():
    with open(os.path.join(FIX, "rightmove_alert.html"), encoding="utf-8") as f:
        return f.read()


def criteria():
    return load_criteria(os.path.join(ROOT, "data", "criteria.json"))


def fake_net():
    return FakeNet({
        "https://api.postcodes.io/postcodes/YO84HL": {"result": {
            "latitude": 53.7830, "longitude": -1.0700, "postcode": "YO8 4HL", "eastings": 461380,
            "northings": 432200, "parish": "Selby"}},
        "https://api.postcodes.io/places?q=Barlby": {"result": [
            {"name_1": "Barlby", "latitude": 53.8005, "longitude": -1.0395, "eastings": 463358, "northings": 434200}]},
        "https://api.postcodes.io/places?q=Riccall": {"result": [
            {"name_1": "Riccall", "latitude": 53.8335, "longitude": -1.0598, "eastings": 461971, "northings": 437900}]},
        "https://data.police.uk/api/crimes-street/all-crime": [{"category": "burglary", "month": "2026-08"}],
        "https://environment.data.gov.uk/flood-monitoring/id/floodAreas": {"items": []},
        "https://environment.data.gov.uk/flood-monitoring/id/floods": {"items": []},
    })


def test_run_end_to_end_then_price_drop(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    ctx = {"schools": [{"URN": "9", "name": "Selby Abbey CE Primary", "easting": "461300", "northing": "432150",
                        "religious": "Church of England"}], "sales": []}
    res = daily.run([html()], criteria(), store, str(tmp_path / "out"), fake_net(), date="2026-10-27", ctx=ctx)

    rows = {r["id"]: r for r in res["rows"]}
    assert sorted(rows) == ["900000001", "900000002", "900000003"]  # 2-bed and £265k filtered out
    assert {r["id"] for r in res["rejected"]} == {"900000004", "900000005"}
    assert all(r["status"] == "new" for r in rows.values())

    selby = rows["900000001"]
    assert selby["tier"] == 1 and selby["church_km"] < 1 and selby["precision"] == "postcode"
    assert selby["garden"] == "yes" and selby["parking"] == "yes" and selby["epc"] == "C"
    assert selby["costs"]["stamp_duty_ftb"] == 0 and selby["schools"][0]["name"].startswith("Selby Abbey")
    assert selby["crime"]["total"] == 1
    assert rows["900000002"]["tier"] == 2 and rows["900000002"]["condition"] == "Likely needs work"
    assert rows["900000003"]["tier"] == 3 and rows["900000003"]["tenure"] == "Leasehold"

    out = tmp_path / "out" / "2026-10-27"
    page = (out / "report.html").read_text()
    assert "leaflet" in page and "St James the Apostle" in page
    data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S)
                      .group(1).replace("<\\/", "</"))
    assert len(data["rows"]) == 3
    brief = json.loads((out / "brief.json").read_text())
    assert brief["new"] == 3 and brief["filtered_out"] == 2
    md = (out / "brief.md").read_text()
    assert "House brief, 2026-10-27" in md and "Riccall" in md and "estimate" in md

    # Next day: same email again plus a price drop on one listing.
    store2 = SeenStore(str(tmp_path / "seen.json"))
    cheaper = html().replace("£205,000", "£195,000")
    net2 = FakeNet()  # unchanged listings must not be looked up again
    res2 = daily.run([cheaper], criteria(), store2, str(tmp_path / "out"), net2, date="2026-10-28", ctx=ctx)
    rows2 = {r["id"]: r for r in res2["rows"]}
    assert rows2["900000001"]["status"] == "reduced" and rows2["900000001"]["reduced_from"] == 205000
    assert rows2["900000002"]["status"] == "earlier" and rows2["900000002"]["tier"] == 2
    assert json.loads((tmp_path / "out" / "2026-10-28" / "brief.json").read_text())["reduced"] == 1


def test_earlier_finds_shown_from_seen_store_until_they_age_out(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    ctx = {"schools": [], "sales": []}
    daily.run([html()], criteria(), store, str(tmp_path / "out"), fake_net(), date="2026-10-01", ctx=ctx)
    res = daily.run([], criteria(), store, str(tmp_path / "out"), FakeNet(), date="2026-10-20", ctx=ctx)
    assert len(res["rows"]) == 3 and all(r["status"] == "earlier" for r in res["rows"])
    assert "Nothing new or reduced" in open(res["paths"]["brief_md"]).read()
    res = daily.run([], criteria(), store, str(tmp_path / "out"), FakeNet(), date="2026-12-01", ctx=ctx)
    assert res["rows"] == []


def test_html_escapes_script_breakout(tmp_path):
    evil = html().replace("Example Road, Selby, YO8 4HL", "</script><script>alert(1)</script>, Selby, YO8 4HL")
    res = daily.run([evil], criteria(), SeenStore(str(tmp_path / "s.json")), str(tmp_path), FakeNet(),
                    date="2026-10-27", ctx={})
    page = open(res["paths"]["report"]).read()
    assert "</script><script>alert(1)" not in page


def test_cli_offline(tmp_path, capsys):
    rc = daily.main(["--input", FIX, "--out", str(tmp_path / "r"), "--seen", str(tmp_path / "seen.json"),
                     "--offline", "--date", "2026-10-27",
                     "--criteria", os.path.join(ROOT, "data", "criteria.json")])
    assert rc == 0
    printed = capsys.readouterr().out
    assert "4 new" in printed and os.path.exists(tmp_path / "r" / "2026-10-27" / "report.html")
    assert daily.main(["--input", str(tmp_path / "missing"), "--offline"]) == 2
