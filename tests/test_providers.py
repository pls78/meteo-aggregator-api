from __future__ import annotations

import httpx
import pytest
import respx

from meteo_aggregator import config
from meteo_aggregator.models import Location
from meteo_aggregator.providers.ensemble import _spread_from_hourly, fetch_ensemble_spread
from meteo_aggregator.providers.open_meteo import OpenMeteoGeneralProvider
from meteo_aggregator.providers.open_meteo_local import OpenMeteoLocalProvider
from helpers import build_daily_response

MILAN = Location(latitude=45.46, longitude=9.19)


@respx.mock
async def test_general_provider_parses_multiple_models():
    times = ["2026-06-16", "2026-06-17", "2026-06-18"]
    payload = build_daily_response(
        times,
        {
            "ecmwf_ifs025": {
                "temperature_2m_max": [24.0, 25.0, 26.0],
                "temperature_2m_min": [14.0, 15.0, 16.0],
            },
            "gfs_seamless": {
                "temperature_2m_max": [27.0, 26.0, 25.0],
                "temperature_2m_min": [16.0, 16.0, 15.0],
            },
        },
    )
    respx.get(config.FORECAST_URL).mock(return_value=httpx.Response(200, json=payload))

    async with httpx.AsyncClient() as client:
        provider = OpenMeteoGeneralProvider(
            client,
            models=["ecmwf_ifs025", "gfs_seamless"],
            variables=["temperature_2m_max", "temperature_2m_min"],
        )
        series = await provider.fetch(MILAN, 3)

    assert {s.name for s in series} == {"ecmwf_ifs025", "gfs_seamless"}
    ecmwf = next(s for s in series if s.name == "ecmwf_ifs025")
    assert ecmwf.role == "general"
    assert ecmwf.resolution_km == 25.0
    assert len(ecmwf.days) == 3
    assert ecmwf.days[0].values["temperature_2m_max"] == 24.0


@respx.mock
async def test_provider_parses_string_and_categorical_variables():
    payload = build_daily_response(
        ["2026-06-16"],
        {
            "ecmwf_ifs025": {
                "weather_code": [61],
                "sunrise": ["2026-06-16T05:30"],
            }
        },
    )
    respx.get(config.FORECAST_URL).mock(return_value=httpx.Response(200, json=payload))

    async with httpx.AsyncClient() as client:
        series = await OpenMeteoGeneralProvider(
            client, models=["ecmwf_ifs025"], variables=["weather_code", "sunrise"]
        ).fetch(MILAN, 1)

    values = series[0].days[0].values
    assert values["weather_code"] == 61
    assert values["sunrise"] == "2026-06-16T05:30"


@respx.mock
async def test_general_provider_caps_days_at_max_horizon():
    route = respx.get(config.FORECAST_URL).mock(
        return_value=httpx.Response(200, json=build_daily_response([], {}))
    )
    async with httpx.AsyncClient() as client:
        await OpenMeteoGeneralProvider(client).fetch(MILAN, 30)

    assert route.calls.last.request.url.params["forecast_days"] == str(config.MAX_HORIZON_DAYS)


@respx.mock
async def test_local_provider_self_limits_to_native_horizon():
    times = ["2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19"]
    payload = build_daily_response(
        times,
        {
            "italia_meteo_arpae_icon_2i": {
                "temperature_2m_max": [23.0, 24.0, 25.0, None],
                "temperature_2m_min": [13.0, 14.0, 15.0, None],
            }
        },
    )
    respx.get(config.FORECAST_URL).mock(return_value=httpx.Response(200, json=payload))

    async with httpx.AsyncClient() as client:
        provider = OpenMeteoLocalProvider(
            client, variables=["temperature_2m_max", "temperature_2m_min"]
        )
        series = await provider.fetch(MILAN, 7)

    assert len(series) == 1
    local = series[0]
    assert local.role == "local"
    # 4th day is all-None -> dropped.
    assert len(local.days) == 3


@respx.mock
async def test_local_provider_uses_configured_model():
    route = respx.get(config.FORECAST_URL).mock(
        return_value=httpx.Response(200, json=build_daily_response([], {}))
    )
    async with httpx.AsyncClient() as client:
        await OpenMeteoLocalProvider(client, model="some_other_model").fetch(MILAN, 3)

    assert route.calls.last.request.url.params["models"] == "some_other_model"


def test_ensemble_spread_from_hourly():
    # Two members, one day, 2 hourly steps each.
    data = {
        "hourly": {
            "time": ["2026-06-16T00:00", "2026-06-16T01:00"],
            "temperature_2m_member01": [10.0, 12.0],  # daily mean 11
            "temperature_2m_member02": [14.0, 16.0],  # daily mean 15
        }
    }
    spread = _spread_from_hourly(data)
    from datetime import date

    assert date(2026, 6, 16) in spread
    # pstdev of [11, 15] = 2.0
    assert spread[date(2026, 6, 16)] == pytest.approx(2.0)


@respx.mock
async def test_ensemble_fetch_degrades_gracefully_on_error():
    respx.get(config.ENSEMBLE_URL).mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as client:
        spread = await fetch_ensemble_spread(client, MILAN, 7)
    assert spread == {}
