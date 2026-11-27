
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


def test_month_summary_uses_sunrise_and_local_day():
    response = client.post("/api/panchang/month", json=dict(place, day="2026-11-01"))
    assert response.status_code == 200
    days = response.json()
    assert len(days) == 30
    assert days[26] == {
        "date": "2026-11-27", "tithi": "Чатуртхи", "nakshatra": "Ардра", "bhadra": True,
    }

    polar = client.post("/api/panchang/month", json=dict(place, lat=78, lon=15, tz=1)).json()
    assert polar[26]["tithi"] is None
    assert polar[26]["nakshatra"] is None


def test_civil_day_tracks_clock_changes():
    from datetime import datetime

    berlin = dict(lat=52.52, lon=13.405, tz=1, use_local_timezone=True)
    for day, hours in [("2026-03-29", 23), ("2026-10-25", 25)]:
        result = client.post("/api/panchang/day", json=dict(berlin, day=day)).json()
        assert result["timezone"] == "Europe/Berlin"
        start, end = (datetime.fromisoformat(result[key]) for key in ("start", "end"))
        assert (end - start).total_seconds() == hours * 3600
        for key in ("vara", "tithi", "nakshatra", "hora"):
            for left, right in zip(result["rows"][key], result["rows"][key][1:]):
                assert left["dt_end"] == right["dt_start"]
        assert result["rows"]["hora"][0]["dt_start"][-6:] != result["rows"]["hora"][-1]["dt_end"][-6:]

    month = client.post("/api/panchang/month", json=dict(berlin, day="2026-10-01")).json()
    assert len(month) == 31
    assert month[24]["nakshatra"]


def test_automatic_stavropol_agrees_with_reference():
    reference = client.post("/api/panchang/day", json=place).json()
    local = client.post("/api/panchang/day", json=dict(place, use_local_timezone=True)).json()
    for key in reference["rows"]:
        assert [row["dt_start"] for row in reference["rows"][key]] == [
            row["dt_start"][:-6] for row in local["rows"][key]
        ]
