"""Thin FastAPI layer over the meteo_aggregator library core.

No forecasting logic here: parse/validate the request, delegate to the library
client, and serialize the pydantic result.
"""

from __future__ import annotations

from fastapi import FastAPI, Query

from meteo_aggregator import config
from meteo_aggregator.client import get_forecast, search_locations
from meteo_aggregator.models import AggregatedForecast, Location, Place

app = FastAPI(title="Meteo-Aggregator", version="0.1.0")


@app.get("/forecast", response_model=AggregatedForecast)
async def forecast(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: int = Query(config.DEFAULT_DAYS, ge=1, le=config.MAX_HORIZON_DAYS),
) -> AggregatedForecast:
    # Invalid/missing/non-numeric coordinates are rejected by Query validation
    # (HTTP 422) before any provider call is made.
    return await get_forecast(Location(latitude=lat, longitude=lon), days)


@app.get("/search", response_model=list[Place])
async def search(
    name: str = Query(..., min_length=1, description="Place name to search for"),
    count: int = Query(
        config.GEOCODING_DEFAULT_COUNT, ge=1, le=config.GEOCODING_MAX_COUNT
    ),
    language: str = Query(config.GEOCODING_LANGUAGE, min_length=2, max_length=2),
) -> list[Place]:
    # A missing/empty name is rejected by Query validation (HTTP 422) before any
    # geocoding call is made. No matches returns an empty list (200).
    return await search_locations(name, count=count, language=language)
