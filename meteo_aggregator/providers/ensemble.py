"""Ensemble spread from the Open-Meteo Ensemble API, for confidence scoring.

Best-effort: any failure (network, schema, no members) returns an empty mapping
so the forecast still succeeds — aggregation then falls back to inter-model
disagreement alone.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date as Date
from datetime import datetime

import httpx

from meteo_aggregator import config
from meteo_aggregator.models import Location


async def fetch_ensemble_spread(
    client: httpx.AsyncClient,
    location: Location,
    days: int,
    model: str | None = None,
) -> dict[Date, float]:
    """Per-day temperature spread (°C) across ensemble members.

    For each member we take the mean hourly temperature per day, then report
    the standard deviation across members for that day.
    """
    model = model or config.ENSEMBLE_MODEL
    capped_days = max(1, min(days, config.MAX_HORIZON_DAYS))
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "hourly": "temperature_2m",
        "models": model,
        "forecast_days": capped_days,
        "timezone": "auto",
    }
    try:
        resp = await client.get(config.ENSEMBLE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return _spread_from_hourly(data)
    except Exception:
        return {}


def _spread_from_hourly(data: dict) -> dict[Date, float]:
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return {}

    member_keys = [k for k in hourly if k.startswith("temperature_2m")]
    if len(member_keys) < 2:
        return {}

    dates = [datetime.fromisoformat(t).date() for t in times]

    # Per member: daily mean temperature.
    per_member_daily: list[dict[Date, float]] = []
    for key in member_keys:
        col = hourly.get(key) or []
        buckets: dict[Date, list[float]] = defaultdict(list)
        for d, v in zip(dates, col):
            if v is not None:
                buckets[d].append(v)
        per_member_daily.append({d: statistics.fmean(vs) for d, vs in buckets.items() if vs})

    # Per day: stddev across members.
    spread: dict[Date, float] = {}
    for d in sorted({d for m in per_member_daily for d in m}):
        vals = [m[d] for m in per_member_daily if d in m]
        if len(vals) >= 2:
            spread[d] = statistics.pstdev(vals)
    return spread
