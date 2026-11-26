
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
place = dict(day="2026-11-27", tz=3, lat=45.0428, lon=41.9734)


def test_day_screen_before_sunrise():
    rows = client.post("/api/panchang/day", json=place).json()["rows"]
    at = "2026-11-27T03:00:00"
    current = {key: next((i for i in items if i["dt_start"] <= at < i["dt_end"]), None)
               for key, items in rows.items()}
    assert current["vara"]["name"] == "Четверг"
    assert [current[k]["num"] for k in ("tithi", "nakshatra", "karana", "yoga")] == [18, 6, 7, 23]
    assert current["moon"]["dt_start"].startswith("2026-11-26T04:41")
    assert current["moon"]["dt_end"].startswith("2026-11-28T04:52")
    assert current["lagna"]["num"] == 6
    assert current["yama"]["num"] == 6
    assert current["muhurta"]["num"] == 26 and current["hora"]["num"] == 21
    for key in ("light", "vara", "lagna", "tithi", "nakshatra", "karana", "yoga", "muhurta", "hora", "yama"):
        intervals = rows[key]
        assert intervals[0]["dt_start"] <= place["day"] + "T00:00:00"
        assert intervals[-1]["dt_end"] >= "2026-11-28T00:00:00"
        for left, right in zip(intervals, intervals[1:]):
            assert left["dt_end"] == right["dt_start"]


def test_geometric_and_polar_day():
    body = client.post("/api/panchang/day", json=dict(place, position_mode="geometric")).json()
    assert body["position_mode"] == "geometric"
    assert body["rows"]["tithi"][0]["dt_end"] != "2026-11-27T07:19:03"
    polar = client.post("/api/panchang/day", json=dict(place, lat=78, lon=15, tz=1)).json()
    assert polar["warnings"] and polar["rows"]["lagna"] == [] and polar["rows"]["yoga"]
