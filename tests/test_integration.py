"""Live integration test against the real Open-Meteo API.

Skipped unless METEO_LIVE=1 so the suite stays offline by default.
"""

from __future__ import annotations

import os

import pytest

from meteo_aggregator import get_forecast, search_locations
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
