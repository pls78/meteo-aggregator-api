"""Live integration test against the real Open-Meteo API.

Skipped unless METEO_LIVE=1 so the suite stays offline by default.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from meteo_aggregator import get_forecast, get_hourly_forecast, get_satellite_imagery, search_locations
from meteo_aggregator.models import Location

pytestmark = pytest.mark.live

LOMBARDY = Location(latitude=45.5, longitude=9.5, name="rural Lombardy")


@pytest.mark.skipif(os.environ.get("METEO_LIVE") != "1", reason="set METEO_LIVE=1 to run")
async def test_live_seven_day_forecast():
    forecast = await get_forecast(LOMBARDY, days=7)

    assert len(forecast.days) == 7
    for day in forecast.days:
        assert day.values.get("temperature_2m_max") is not None
        assert day.breakdown, "each day should carry a per-model breakdown"
        assert day.confidence.level in {"high", "medium", "low"}

    # Non-blendable variables keep their native types end-to-end.
    day0 = forecast.days[0]
    assert isinstance(day0.values.get("sunrise"), str)
    assert day0.values.get("weather_code") is not None

    # Local high-res model should contribute to the near term, not day 7.
    day1_models = {c.model for c in forecast.days[0].breakdown}
    assert "italia_meteo_arpae_icon_2i" in day1_models


@pytest.mark.skipif(os.environ.get("METEO_LIVE") != "1", reason="set METEO_LIVE=1 to run")
async def test_live_hourly_forecast():
    forecast = await get_hourly_forecast(LOMBARDY, hours=48)

    assert len(forecast.hours) == 48
    for hour in forecast.hours:
        assert hour.values.get("temperature_2m") is not None
        assert hour.breakdown, "each hour should carry a per-model breakdown"
        assert hour.confidence.level in {"high", "medium", "low"}

    # Non-blendable variables keep their native types end-to-end.
    h0 = forecast.hours[0]
    assert h0.values.get("weather_code") is not None
    assert isinstance(h0.values.get("wind_direction_10m"), (int, float))

    # Local high-res model should contribute to the near-term hours.
    near_term_models = {c.model for c in forecast.hours[0].breakdown}
    assert "italia_meteo_arpae_icon_2i" in near_term_models


@pytest.mark.skipif(os.environ.get("METEO_LIVE") != "1", reason="set METEO_LIVE=1 to run")
async def test_live_geocoding_search():
    # "Milano" matches several places worldwide; the Italian one is named "Milan"
    # in English, so assert it appears among results rather than ranking first.
    places = await search_locations("Milano", count=10, language="it")

    assert places, "expected at least one match for Milano"
    # Milan, Italy is around 45.5 N, 9.2 E.
    milan_it = next(
        (p for p in places if 44.5 < p.latitude < 46.5 and 8.0 < p.longitude < 10.5),
        None,
    )
    assert milan_it is not None, f"Milan, Italy not in results: {[p.name for p in places]}"
    assert milan_it.country_code == "IT"
    # A result is directly usable by the forecast pipeline.
    assert milan_it.to_location().latitude == milan_it.latitude


@pytest.mark.skipif(os.environ.get("METEO_LIVE") != "1", reason="set METEO_LIVE=1 to run")
async def test_live_satellite_imagery_wms_reachable():

    # Request imagery from 3 hours ago so data is indexed (near-real-time
    # products have processing latency of a few minutes to ~1 hour).
    at = datetime.now(timezone.utc) - timedelta(hours=3)
    imagery = get_satellite_imagery(at)
    assert imagery.layers, "expected at least one configured layer"

    # Verify each layer returns an actual image (not a WMS ServiceException).
    # Lombardy bbox in EPSG:3857.
    bbox = "896122,5621521,1113194,5800000"
    async with httpx.AsyncClient(timeout=20.0) as http:
        for layer in imagery.layers:
            if layer.time is None:
                continue  # layer archive starts after the requested time; skip
            params = {
                "service": "WMS",
                "version": "1.3.0",
                "request": "GetMap",
                "layers": layer.layer,
                "crs": layer.crs,
                "bbox": bbox,
                "width": "256",
                "height": "256",
                "format": layer.format,
                "time": layer.time,
            }
            resp = await http.get(layer.wms_url, params=params)
            assert resp.status_code == 200, (
                f"{layer.layer} returned HTTP {resp.status_code}"
            )
            content_type = resp.headers.get("content-type", "")
            assert "image" in content_type, (
                f"{layer.layer} returned {content_type!r} instead of an image — "
                f"body: {resp.text[:300]}"
            )
