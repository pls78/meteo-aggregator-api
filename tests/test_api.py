from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from api.main import app
from meteo_aggregator import config
from meteo_aggregator.models import (
    AggregatedForecast,
    Confidence,
    DayConsensus,
    Location,
    Place,
)

client = TestClient(app)


def _fake_forecast(location: Location) -> AggregatedForecast:
    return AggregatedForecast(
        location=location,
        generated_at=datetime.now(timezone.utc),
        days=[
            DayConsensus(
                date=date(2026, 6, 16),
                lead_day=0,
                values={
                    "temperature_2m_max": 24.0,
                    "weather_code": 61,
                    "sunrise": "2026-06-16T05:30",
                },
                confidence=Confidence(level="high", low=23.0, high=25.0, spread=1.0),
                breakdown=[],
            )
        ],
    )


def test_forecast_success(monkeypatch):
    async def fake_get_forecast(location, days, **kwargs):
        return _fake_forecast(location)

    monkeypatch.setattr(api_main, "get_forecast", fake_get_forecast)

    resp = client.get("/forecast", params={"lat": 45.5, "lon": 9.5, "days": 7})
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"]["latitude"] == 45.5
    assert len(body["days"]) == 1
    day = body["days"][0]
    assert day["values"]["temperature_2m_max"] == 24.0
    # Non-blendable variables round-trip with their native types.
    assert day["values"]["weather_code"] == 61
    assert day["values"]["sunrise"] == "2026-06-16T05:30"
    assert day["confidence"]["level"] == "high"
    assert "breakdown" in day


def test_forecast_defaults_to_seven_days(monkeypatch):
    captured = {}

    async def fake_get_forecast(location, days, **kwargs):
        captured["days"] = days
        return _fake_forecast(location)

    monkeypatch.setattr(api_main, "get_forecast", fake_get_forecast)

    resp = client.get("/forecast", params={"lat": 45.5, "lon": 9.5})
    assert resp.status_code == 200
    assert captured["days"] == 7


def test_forecast_rejects_invalid_coordinates(monkeypatch):
    called = {"hit": False}

    async def fake_get_forecast(location, days, **kwargs):
        called["hit"] = True
        return _fake_forecast(location)

    monkeypatch.setattr(api_main, "get_forecast", fake_get_forecast)

    resp = client.get("/forecast", params={"lat": "not-a-number", "lon": 9.5})
    assert resp.status_code == 422
    assert called["hit"] is False


def test_search_success(monkeypatch):
    async def fake_search_locations(query, **kwargs):
        return [
            Place(id=1, name="Milan", latitude=45.46, longitude=9.19, country="Italy"),
        ]

    monkeypatch.setattr(api_main, "search_locations", fake_search_locations)

    resp = client.get("/search", params={"name": "Milan"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Milan"
    assert body[0]["latitude"] == 45.46
    assert body[0]["country"] == "Italy"


def test_search_no_match_returns_empty_list(monkeypatch):
    async def fake_search_locations(query, **kwargs):
        return []

    monkeypatch.setattr(api_main, "search_locations", fake_search_locations)

    resp = client.get("/search", params={"name": "zzzznowhere"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_rejects_empty_name(monkeypatch):
    called = {"hit": False}

    async def fake_search_locations(query, **kwargs):
        called["hit"] = True
        return []

    monkeypatch.setattr(api_main, "search_locations", fake_search_locations)

    resp = client.get("/search", params={"name": ""})
    assert resp.status_code == 422
    assert called["hit"] is False


def test_imagery_returns_all_layers():
    resp = client.get("/imagery")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["layers"]) == len(config.EUMETVIEW_LAYERS)
    layer = body["layers"][0]
    assert layer["wms_url"] == config.EUMETVIEW_WMS_URL
    assert layer["crs"] == config.EUMETVIEW_CRS
    assert layer["format"] == config.EUMETVIEW_FORMAT


def test_imagery_time_param_is_forwarded():
    resp = client.get("/imagery", params={"time": "2026-06-20T14:07:00Z"})
    assert resp.status_code == 200
    body = resp.json()
    # msg_fes:clm is a 15-min layer; 14:07 should snap to 14:00.
    clm = next(l for l in body["layers"] if l["layer"] == "msg_fes:clm")
    assert clm["time"] == "2026-06-20T14:00:00Z"


def test_imagery_rejects_invalid_time():
    resp = client.get("/imagery", params={"time": "not-a-datetime"})
    assert resp.status_code == 422


def test_imagery_pre_archive_time_yields_null_for_mtg():
    # MTG starts Sep 2024; a 2023 time should give time=null for MTG layers.
    resp = client.get("/imagery", params={"time": "2023-06-01T12:00:00Z"})
    assert resp.status_code == 200
    body = resp.json()
    mtg = next(l for l in body["layers"] if l["layer"] == "mtg_fd:ir105_hrfi")
    assert mtg["time"] is None


def test_imagery_default_single_frame():
    resp = client.get("/imagery")
    assert resp.status_code == 200
    for layer in resp.json()["layers"]:
        assert layer["times"] == [layer["time"]]


def test_imagery_frames_returns_arrays():
    resp = client.get(
        "/imagery", params={"time": "2026-06-20T14:07:00Z", "frames": 5}
    )
    assert resp.status_code == 200
    clm = next(l for l in resp.json()["layers"] if l["layer"] == "msg_fes:clm")
    assert len(clm["times"]) == 5
    assert clm["time"] == clm["times"][0]


@pytest.mark.parametrize("frames", [0, -1, config.MAX_IMAGERY_FRAMES + 1])
def test_imagery_rejects_out_of_range_frames(frames):
    resp = client.get("/imagery", params={"frames": frames})
    assert resp.status_code == 422
