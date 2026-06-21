"""Tests for the hourly forecast pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import api.main as api_main
from api.main import app
from meteo_aggregator import config
from meteo_aggregator.aggregation import aggregate_hourly
from meteo_aggregator.models import AggregatedHourlyForecast, HourSeries, Location
from meteo_aggregator.providers.open_meteo import (
    OpenMeteoGeneralHourlyProvider,
    OpenMeteoLocalHourlyProvider,
    _parse_hourly,
)

client = TestClient(app)
MILAN = Location(latitude=45.46, longitude=9.19)
_UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_hourly_response(times: list[str], model_values: dict[str, dict[str, list]]) -> dict:
    hourly: dict = {"time": list(times)}
    for model, variables in model_values.items():
        for var, col in variables.items():
            hourly[f"{var}_{model}"] = col
    return {"hourly": hourly}


# ---------------------------------------------------------------------------
# Provider — parsing
# ---------------------------------------------------------------------------

@respx.mock
async def test_general_hourly_provider_parses_multiple_models():
    times = [
        "2026-06-21T00:00", "2026-06-21T01:00", "2026-06-21T02:00"
    ]
    payload = build_hourly_response(
        times,
        {
            "ecmwf_ifs025": {
                "temperature_2m": [18.0, 17.5, 17.0],
                "precipitation": [0.0, 0.1, 0.0],
            },
            "gfs_seamless": {
                "temperature_2m": [19.0, 18.0, 17.5],
                "precipitation": [0.0, 0.0, 0.2],
            },
        },
    )
    respx.get(config.FORECAST_URL).mock(return_value=httpx.Response(200, json=payload))

    async with httpx.AsyncClient() as c:
        provider = OpenMeteoGeneralHourlyProvider(
            c,
            models=["ecmwf_ifs025", "gfs_seamless"],
            variables=["temperature_2m", "precipitation"],
        )
        series = await provider.fetch(MILAN, 3)

    assert {s.name for s in series} == {"ecmwf_ifs025", "gfs_seamless"}
    ecmwf = next(s for s in series if s.name == "ecmwf_ifs025")
    assert len(ecmwf.hours) == 3
    assert ecmwf.hours[0].values["temperature_2m"] == 18.0


@respx.mock
async def test_local_hourly_provider_drops_all_none_hours():
    times = ["2026-06-21T00:00", "2026-06-21T01:00", "2026-06-21T02:00"]
    payload = build_hourly_response(
        times,
        {
            "italia_meteo_arpae_icon_2i": {
                "temperature_2m": [20.0, 19.0, None],
                "precipitation": [0.0, 0.0, None],
            }
        },
    )
    respx.get(config.FORECAST_URL).mock(return_value=httpx.Response(200, json=payload))

    async with httpx.AsyncClient() as c:
        series = await OpenMeteoLocalHourlyProvider(
            c, variables=["temperature_2m", "precipitation"]
        ).fetch(MILAN, 3)

    assert len(series) == 1
    assert len(series[0].hours) == 2  # third hour all-None → dropped


@respx.mock
async def test_hourly_provider_caps_hours_at_max():
    route = respx.get(config.FORECAST_URL).mock(
        return_value=httpx.Response(200, json={"hourly": {"time": []}})
    )
    async with httpx.AsyncClient() as c:
        await OpenMeteoGeneralHourlyProvider(c).fetch(MILAN, 9999)

    assert route.calls.last.request.url.params["forecast_hours"] == str(config.MAX_HOURLY_HOURS)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _make_series(name: str, role: str, hours: list[tuple[str, dict]]) -> HourSeries:
    from meteo_aggregator.models import ModelHour
    return HourSeries(
        name=name,
        role=role,
        hours=[
            ModelHour(date=datetime.fromisoformat(ts), values=vals)
            for ts, vals in hours
        ],
    )


def test_aggregate_hourly_returns_all_hours():
    ts = ["2026-06-21T00:00+00:00", "2026-06-21T01:00+00:00"]
    s1 = _make_series("ecmwf_ifs025", "general", [(t, {"temperature_2m": 18.0}) for t in ts])
    s2 = _make_series("gfs_seamless", "general", [(t, {"temperature_2m": 20.0}) for t in ts])
    result = aggregate_hourly(MILAN, [s1, s2], variables=["temperature_2m"])
    assert len(result.hours) == 2


def test_aggregate_hourly_blends_temperature():
    ts = "2026-06-21T00:00+00:00"
    # ecmwf weight (near-term, lead_day 0): 0.25; gfs: 0.10 → weighted mean ~18.4
    s1 = _make_series("ecmwf_ifs025", "general", [(ts, {"temperature_2m": 18.0})])
    s2 = _make_series("gfs_seamless", "general", [(ts, {"temperature_2m": 20.0})])
    result = aggregate_hourly(MILAN, [s1, s2], variables=["temperature_2m"])
    val = result.hours[0].values["temperature_2m"]
    assert val is not None
    assert 18.0 <= val <= 20.0


def test_aggregate_hourly_local_favoured_near_term():
    ts = "2026-06-21T06:00+00:00"
    # lead_hour=6 → lead_day=0 → near-term → ICON-2i weight 0.50 > ECMWF 0.25
    icon2i = _make_series("italia_meteo_arpae_icon_2i", "local", [(ts, {"temperature_2m": 22.0})])
    ecmwf = _make_series("ecmwf_ifs025", "general", [(ts, {"temperature_2m": 18.0})])
    result = aggregate_hourly(MILAN, [icon2i, ecmwf], variables=["temperature_2m"])
    # Weighted: (0.50*22 + 0.25*18) / 0.75 = 20.67
    val = result.hours[0].values["temperature_2m"]
    assert val == pytest.approx(20.666, rel=1e-3)


def test_aggregate_hourly_weight_renormalizes_without_local():
    # lead_hour=96 → lead_day=4 → range bucket (no ICON-2i weight)
    ts = "2026-06-25T00:00+00:00"
    ecmwf = _make_series("ecmwf_ifs025", "general", [(ts, {"temperature_2m": 18.0})])
    gfs = _make_series("gfs_seamless", "general", [(ts, {"temperature_2m": 20.0})])
    result = aggregate_hourly(MILAN, [ecmwf, gfs], variables=["temperature_2m"])
    val = result.hours[0].values["temperature_2m"]
    assert val is not None  # still produces a consensus


def test_aggregate_hourly_non_blendable_weather_code():
    ts = "2026-06-21T00:00+00:00"
    # ECMWF has higher weight near-term; its weather_code should win
    ecmwf = _make_series("ecmwf_ifs025", "general", [(ts, {"weather_code": 61})])
    gfs = _make_series("gfs_seamless", "general", [(ts, {"weather_code": 80})])
    result = aggregate_hourly(MILAN, [ecmwf, gfs], variables=["weather_code"])
    assert result.hours[0].values["weather_code"] == 61


def test_aggregate_hourly_non_blendable_wind_direction():
    ts = "2026-06-21T00:00+00:00"
    # Averaging 350° and 10° arithmetically gives 180° — wrong. Should pick
    # the highest-weighted model instead.
    ecmwf = _make_series("ecmwf_ifs025", "general", [(ts, {"wind_direction_10m": 350})])
    gfs = _make_series("gfs_seamless", "general", [(ts, {"wind_direction_10m": 10})])
    result = aggregate_hourly(MILAN, [ecmwf, gfs], variables=["wind_direction_10m"])
    # Should be 350 (ECMWF), not 180
    assert result.hours[0].values["wind_direction_10m"] == 350
    assert result.hours[0].values["wind_direction_10m"] != 180


def test_aggregate_hourly_confidence_level_present():
    ts = "2026-06-21T00:00+00:00"
    s1 = _make_series("ecmwf_ifs025", "general", [(ts, {"temperature_2m": 18.0})])
    s2 = _make_series("gfs_seamless", "general", [(ts, {"temperature_2m": 18.1})])
    result = aggregate_hourly(MILAN, [s1, s2], variables=["temperature_2m"])
    assert result.hours[0].confidence.level in {"high", "medium", "low"}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def _fake_hourly(location: Location) -> AggregatedHourlyForecast:
    from datetime import datetime, timezone
    return AggregatedHourlyForecast(
        location=location,
        generated_at=datetime.now(timezone.utc),
        hours=[],
    )


def test_hourly_success(monkeypatch):
    async def fake(location, hours, **kwargs):
        return _fake_hourly(location)

    monkeypatch.setattr(api_main, "get_hourly_forecast", fake)
    resp = client.get("/hourly", params={"lat": 45.5, "lon": 9.5, "hours": 24})
    assert resp.status_code == 200
    body = resp.json()
    assert body["location"]["latitude"] == 45.5
    assert "hours" in body


def test_hourly_defaults_to_48_hours(monkeypatch):
    captured = {}

    async def fake(location, hours, **kwargs):
        captured["hours"] = hours
        return _fake_hourly(location)

    monkeypatch.setattr(api_main, "get_hourly_forecast", fake)
    client.get("/hourly", params={"lat": 45.5, "lon": 9.5})
    assert captured["hours"] == config.DEFAULT_HOURLY_HOURS


def test_hourly_rejects_invalid_coordinates(monkeypatch):
    called = {"hit": False}

    async def fake(location, hours, **kwargs):
        called["hit"] = True
        return _fake_hourly(location)

    monkeypatch.setattr(api_main, "get_hourly_forecast", fake)
    resp = client.get("/hourly", params={"lat": "bad", "lon": 9.5})
    assert resp.status_code == 422
    assert called["hit"] is False
