"""High-level facade orchestrating providers + aggregation."""

from __future__ import annotations

import asyncio
from datetime import datetime

import httpx

from meteo_aggregator import config
from meteo_aggregator.aggregation import aggregate, aggregate_hourly
from meteo_aggregator.models import (
    AggregatedForecast,
    AggregatedHourlyForecast,
    Location,
    Place,
    SatelliteImagery,
)
from meteo_aggregator.providers.ensemble import fetch_ensemble_spread
from meteo_aggregator.providers.eumetview import get_satellite_imagery as _get_satellite_imagery
from meteo_aggregator.providers.geocoding import search_places
from meteo_aggregator.providers.open_meteo import (
    OpenMeteoGeneralHourlyProvider,
    OpenMeteoGeneralProvider,
    OpenMeteoLocalHourlyProvider,
)
from meteo_aggregator.providers.open_meteo_local import OpenMeteoLocalProvider


async def _run(client: httpx.AsyncClient, location: Location, days: int) -> AggregatedForecast:
    general = OpenMeteoGeneralProvider(client)
    local = OpenMeteoLocalProvider(client)

    general_series, local_series, ensemble_spread = await asyncio.gather(
        general.fetch(location, days),
        local.fetch(location, days),
        fetch_ensemble_spread(client, location, days),
    )
    return aggregate(location, general_series + local_series, ensemble_spread)


async def get_forecast(
    location: Location,
    days: int = config.DEFAULT_DAYS,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> AggregatedForecast:
    """Fetch general + local + ensemble data and aggregate into one forecast.

    Pass ``http_client`` to reuse a client (and in tests); otherwise a
    short-lived one is created and closed. The ensemble fetch is best-effort.
    """
    if http_client is not None:
        return await _run(http_client, location, days)
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await _run(client, location, days)


async def search_locations(
    query: str,
    *,
    count: int = config.GEOCODING_DEFAULT_COUNT,
    language: str = config.GEOCODING_LANGUAGE,
    http_client: httpx.AsyncClient | None = None,
) -> list[Place]:
    """Resolve a place-name query into matching places via Open-Meteo geocoding.

    Pass ``http_client`` to reuse a client (and in tests); otherwise a
    short-lived one is created and closed. Returns an empty list on no match.
    """
    if http_client is not None:
        return await search_places(http_client, query, count=count, language=language)
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await search_places(client, query, count=count, language=language)


async def get_hourly_forecast(
    location: Location,
    hours: int = config.DEFAULT_HOURLY_HOURS,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> AggregatedHourlyForecast:
    """Fetch general + local hourly data and aggregate into one hourly forecast."""
    async def _run(client: httpx.AsyncClient) -> AggregatedHourlyForecast:
        general = OpenMeteoGeneralHourlyProvider(client)
        local = OpenMeteoLocalHourlyProvider(client)
        general_series, local_series = await asyncio.gather(
            general.fetch(location, hours),
            local.fetch(location, hours),
        )
        return aggregate_hourly(location, general_series + local_series)

    if http_client is not None:
        return await _run(http_client)
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await _run(client)


def get_satellite_imagery(
    at: datetime | None = None, frames: int = 1
) -> SatelliteImagery:
    """Return WMS parameters for all configured EUMETView layers at time ``at``.

    ``frames`` requests the N most-recent cadence-stepped frames per layer for a
    time-lapse animation (newest first). No network call is made — the map client
    fetches tiles directly from EUMETSAT. See
    :mod:`meteo_aggregator.providers.eumetview` for snapping rules.
    """
    return _get_satellite_imagery(at, frames=frames)
