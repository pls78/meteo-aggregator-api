"""Location search over the Open-Meteo Geocoding API.

Resolves a place-name query into a ranked list of :class:`Place` objects. Unlike
the forecast providers this is a standalone fetch (no model/series machinery):
one keyless GET, parse ``results``, done.
"""

from __future__ import annotations

import httpx

from meteo_aggregator import config
from meteo_aggregator.models import Place

# Open-Meteo geocoding fields that map straight onto Place.
_PLACE_FIELDS = (
    "id",
    "name",
    "latitude",
    "longitude",
    "country",
    "country_code",
    "admin1",
    "timezone",
    "population",
    "elevation",
)


def _parse_results(data: dict) -> list[Place]:
    """Parse an Open-Meteo geocoding response into Place objects.

    Open-Meteo omits the ``results`` key entirely when there is no match, so we
    default to an empty list. Rows missing a name or coordinates are skipped
    rather than raising.
    """
    places: list[Place] = []
    for row in data.get("results") or []:
        if row.get("name") is None or row.get("latitude") is None or row.get("longitude") is None:
            continue
        places.append(Place(**{k: row.get(k) for k in _PLACE_FIELDS}))
    return places


async def search_places(
    client: httpx.AsyncClient,
    query: str,
    *,
    count: int = config.GEOCODING_DEFAULT_COUNT,
    language: str = config.GEOCODING_LANGUAGE,
) -> list[Place]:
    """Search the Open-Meteo Geocoding API for places matching ``query``."""
    params = {
        "name": query,
        "count": max(1, min(count, config.GEOCODING_MAX_COUNT)),
        "language": language,
        "format": "json",
    }
    resp = await client.get(config.GEOCODING_URL, params=params)
    resp.raise_for_status()
    return _parse_results(resp.json())
