"""Specialized-local provider: the config-selected high-res regional model.

Defaults to ItaliaMeteo-ARPAE ICON-2i. Swap ``config.LOCAL_MODEL`` (or pass
``model=``) to relocate to a different high-res model — no code change needed.
The model self-limits to its native horizon because days with no values are
dropped during parsing.
"""

from __future__ import annotations

import httpx

from meteo_aggregator import config
from meteo_aggregator.models import Location, ModelSeries
from meteo_aggregator.providers.base import ForecastProvider
from meteo_aggregator.providers.open_meteo import fetch_open_meteo_daily


class OpenMeteoLocalProvider(ForecastProvider):
    role = "local"
    name = "open-meteo-local"

    def __init__(
        self,
        client: httpx.AsyncClient,
        model: str | None = None,
        variables: list[str] | None = None,
    ) -> None:
        self._client = client
        self._model = model or config.LOCAL_MODEL
        self._variables = variables or config.DAILY_VARIABLES

    async def fetch(self, location: Location, days: int) -> list[ModelSeries]:
        return await fetch_open_meteo_daily(
            self._client, location, days, [self._model], self._variables
        )
