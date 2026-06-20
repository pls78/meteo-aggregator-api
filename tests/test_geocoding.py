from __future__ import annotations

import httpx
import respx

from meteo_aggregator import config
from meteo_aggregator.providers.geocoding import search_places


@respx.mock
async def test_search_parses_results():
    payload = {
        "results": [
            {
                "id": 3173435,
                "name": "Milan",
                "latitude": 45.46427,
                "longitude": 9.18951,
                "country": "Italy",
                "country_code": "IT",
                "admin1": "Lombardy",
                "timezone": "Europe/Rome",
                "population": 1236837,
                "elevation": 122.0,
            },
            {
                "id": 5074472,
                "name": "Milan",
                "latitude": 41.43197,
                "longitude": -90.57347,
                "country": "United States",
                "country_code": "US",
                "admin1": "Illinois",
            },
        ]
    }
    respx.get(config.GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))

    async with httpx.AsyncClient() as client:
        places = await search_places(client, "Milan")

    assert len(places) == 2
    first = places[0]
    assert first.name == "Milan"
    assert first.latitude == 45.46427
    assert first.country == "Italy"
    assert first.admin1 == "Lombardy"
    # to_location() bridges into the forecast pipeline.
    loc = first.to_location()
    assert (loc.latitude, loc.longitude, loc.name) == (45.46427, 9.18951, "Milan")


@respx.mock
async def test_search_no_match_returns_empty_list():
    # Open-Meteo omits the "results" key entirely when nothing matches.
    respx.get(config.GEOCODING_URL).mock(
        return_value=httpx.Response(200, json={"generationtime_ms": 0.1})
    )
    async with httpx.AsyncClient() as client:
        places = await search_places(client, "zzzznowhere")
    assert places == []


@respx.mock
async def test_search_skips_rows_missing_coordinates():
    payload = {"results": [{"id": 1, "name": "Nowhere"}]}  # no lat/lon
    respx.get(config.GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
    async with httpx.AsyncClient() as client:
        places = await search_places(client, "Nowhere")
    assert places == []


@respx.mock
async def test_search_caps_count_and_passes_params():
    route = respx.get(config.GEOCODING_URL).mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    async with httpx.AsyncClient() as client:
        await search_places(client, "Milan", count=9999, language="it")

    params = route.calls.last.request.url.params
    assert params["name"] == "Milan"
    assert params["language"] == "it"
    assert params["count"] == str(config.GEOCODING_MAX_COUNT)
