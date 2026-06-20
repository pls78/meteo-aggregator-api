"""Meteo-Aggregator: accurate local 7-day forecasts from multiple weather models."""

from meteo_aggregator.client import get_forecast, get_satellite_imagery, search_locations
from meteo_aggregator.models import (
    AggregatedForecast,
    Confidence,
    DayConsensus,
    Location,
    ModelContribution,
    ModelSeries,
    Place,
    SatelliteImagery,
    WmsLayerParams,
)

__all__ = [
    "get_forecast",
    "get_satellite_imagery",
    "search_locations",
    "AggregatedForecast",
    "Confidence",
    "DayConsensus",
    "Location",
    "ModelContribution",
    "ModelSeries",
    "Place",
    "SatelliteImagery",
    "WmsLayerParams",
]
