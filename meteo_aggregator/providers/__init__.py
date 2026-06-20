"""Forecast providers: a general (global models) and a swappable local one."""

from meteo_aggregator.providers.base import ForecastProvider
from meteo_aggregator.providers.open_meteo import OpenMeteoGeneralProvider
from meteo_aggregator.providers.open_meteo_local import OpenMeteoLocalProvider

__all__ = [
    "ForecastProvider",
    "OpenMeteoGeneralProvider",
    "OpenMeteoLocalProvider",
]
