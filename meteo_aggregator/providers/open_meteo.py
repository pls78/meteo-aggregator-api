"""General provider: multiple global models from the Open-Meteo Forecast API.

Also exposes :func:`fetch_open_meteo_daily`, the shared request/parse helper
reused by the local provider (same endpoint, different model list).
"""

from __future__ import annotations

from datetime import date as Date

import httpx

from meteo_aggregator import config
from meteo_aggregator.models import Location, ModelDay, ModelSeries
from meteo_aggregator.providers.base import ForecastProvider


def _parse_daily(data: dict, models: list[str], variables: list[str]) -> list[ModelSeries]:
    """Parse an Open-Meteo daily response into one series per model.

    With multiple models, Open-Meteo suffixes each daily key with the model id
    (e.g. ``temperature_2m_max_ecmwf_ifs_hres_9km``). For a single model the
    bare key may be used, so we try the suffixed key first then fall back.
    Days where a model has no values at all are dropped, which lets a model
    self-limit to its native horizon.
    """
    daily = data.get("daily") or {}
    times = [Date.fromisoformat(t) for t in daily.get("time", [])]

    series: list[ModelSeries] = []
    for model in models:
        meta = config.MODEL_META.get(model, {})
        model_days: list[ModelDay] = []
        for i, day in enumerate(times):
            values: dict[str, float | None] = {}
            has_value = False
            for var in variables:
                col = daily.get(f"{var}_{model}")
                if col is None:
                    col = daily.get(var)  # single-model responses
                val = col[i] if col is not None and i < len(col) else None
                values[var] = val
                if val is not None:
                    has_value = True
            if has_value:
                model_days.append(ModelDay(date=day, values=values))
        series.append(
            ModelSeries(
                name=model,
                role=meta.get("role", "general"),
                resolution_km=meta.get("resolution_km"),
                max_horizon_days=meta.get("max_horizon_days"),
                days=model_days,
            )
        )
    return series


async def fetch_open_meteo_daily(
    client: httpx.AsyncClient,
    location: Location,
    days: int,
    models: list[str],
    variables: list[str],
) -> list[ModelSeries]:
    """Issue a single Open-Meteo daily request for the given models."""
    capped_days = max(1, min(days, config.MAX_HORIZON_DAYS))
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "daily": ",".join(variables),
        "models": ",".join(models),
        "forecast_days": capped_days,
        "timezone": "auto",
    }
    resp = await client.get(config.FORECAST_URL, params=params)
    resp.raise_for_status()
    return _parse_daily(resp.json(), models, variables)


class OpenMeteoGeneralProvider(ForecastProvider):
    """Fetches the configured global models in one Open-Meteo call."""

    role = "general"
    name = "open-meteo-global"

    def __init__(
        self,
        client: httpx.AsyncClient,
        models: list[str] | None = None,
        variables: list[str] | None = None,
    ) -> None:
        self._client = client
        self._models = models or config.GLOBAL_MODELS
        self._variables = variables or config.DAILY_VARIABLES

    async def fetch(self, location: Location, days: int) -> list[ModelSeries]:
        return await fetch_open_meteo_daily(
            self._client, location, days, self._models, self._variables
        )
