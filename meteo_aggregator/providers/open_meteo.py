"""General provider: multiple global models from the Open-Meteo Forecast API.

Also exposes :func:`fetch_open_meteo_daily`, the shared request/parse helper
reused by the local provider (same endpoint, different model list).
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime

import httpx

from meteo_aggregator import config
from meteo_aggregator.models import Location, ModelDay, ModelHour, ModelSeries, HourSeries
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


def _parse_hourly(data: dict, models: list[str], variables: list[str]) -> list[HourSeries]:
    """Parse an Open-Meteo hourly response into one series per model.

    Same suffix scheme as daily: multi-model responses suffix each key with the
    model id; single-model responses may use the bare key. Hours where a model
    has no values at all are dropped so a model self-limits to its horizon.
    """
    hourly = data.get("hourly") or {}
    times = [datetime.fromisoformat(t) for t in hourly.get("time", [])]

    series: list[HourSeries] = []
    for model in models:
        meta = config.MODEL_META.get(model, {})
        model_hours: list[ModelHour] = []
        for i, ts in enumerate(times):
            values: dict[str, float | None] = {}
            has_value = False
            for var in variables:
                col = hourly.get(f"{var}_{model}")
                if col is None:
                    col = hourly.get(var)
                val = col[i] if col is not None and i < len(col) else None
                values[var] = val
                if val is not None:
                    has_value = True
            if has_value:
                model_hours.append(ModelHour(date=ts, values=values))
        series.append(
            HourSeries(
                name=model,
                role=meta.get("role", "general"),
                resolution_km=meta.get("resolution_km"),
                max_horizon_days=meta.get("max_horizon_days"),
                hours=model_hours,
            )
        )
    return series


async def fetch_open_meteo_hourly(
    client: httpx.AsyncClient,
    location: Location,
    hours: int,
    models: list[str],
    variables: list[str],
) -> list[HourSeries]:
    """Issue a single Open-Meteo hourly request for the given models."""
    capped = max(1, min(hours, config.MAX_HOURLY_HOURS))
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "hourly": ",".join(variables),
        "models": ",".join(models),
        "forecast_hours": capped,
        # Local timezone, matching the daily forecast, so an hour's date groups under the
        # same calendar day as /forecast. forecast_hours still anchors hours[0] to "now".
        "timezone": "auto",
    }
    resp = await client.get(config.FORECAST_URL, params=params)
    resp.raise_for_status()
    return _parse_hourly(resp.json(), models, variables)


class OpenMeteoGeneralHourlyProvider:
    """Fetches the configured global models in one Open-Meteo hourly call."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        models: list[str] | None = None,
        variables: list[str] | None = None,
    ) -> None:
        self._client = client
        self._models = models or config.GLOBAL_MODELS
        self._variables = variables or config.HOURLY_VARIABLES

    async def fetch(self, location: Location, hours: int) -> list[HourSeries]:
        return await fetch_open_meteo_hourly(
            self._client, location, hours, self._models, self._variables
        )


class OpenMeteoLocalHourlyProvider:
    """Fetches the config-selected local model hourly. Self-limits to ~72 h."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        model: str | None = None,
        variables: list[str] | None = None,
    ) -> None:
        self._client = client
        self._model = model or config.LOCAL_MODEL
        self._variables = variables or config.HOURLY_VARIABLES

    async def fetch(self, location: Location, hours: int) -> list[HourSeries]:
        return await fetch_open_meteo_hourly(
            self._client, location, hours, [self._model], self._variables
        )


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
