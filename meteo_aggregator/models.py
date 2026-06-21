"""Pydantic domain models for the aggregated forecast.

Provenance travels with the data: every model series and per-day contribution
records which model (and role) it came from.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["general", "local"]
ConfidenceLevel = Literal["high", "medium", "low"]

# A day's variable readings: variable name -> value (None when unavailable).
# Most variables are numeric; a few are non-numeric (e.g. sunrise/sunset strings,
# weather_code categorical), so values may be float, int, or str.
DailyValue = Optional[float | int | str]
DailyValues = dict[str, DailyValue]


class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    name: Optional[str] = None


class Place(BaseModel):
    """A geocoded place: a name-search result the client can forecast on.

    Carries enough provenance (country/region/timezone/population) to
    disambiguate same-named places. ``to_location()`` bridges into the forecast
    pipeline.
    """

    id: Optional[int] = None
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    country: Optional[str] = None
    country_code: Optional[str] = None
    admin1: Optional[str] = None
    timezone: Optional[str] = None
    population: Optional[int] = None
    elevation: Optional[float] = None

    def to_location(self) -> "Location":
        return Location(latitude=self.latitude, longitude=self.longitude, name=self.name)


class WmsLayerParams(BaseModel):
    """WMS parameters for one satellite layer, ready for a map library.

    Pass ``wms_url`` as the endpoint and the remaining fields as layer options
    to Leaflet ``L.tileLayer.wms()``, MapLibre, or equivalent. The service never
    proxies image bytes — the map client fetches tiles directly from EUMETSAT.
    ``time`` is pre-snapped to the layer's cadence boundary; ``None`` means the
    requested time predates the layer's archive (the WMS will serve the latest
    available image).
    """

    wms_url: str
    layer: str
    title: str
    time: Optional[str] = None  # ISO 8601 UTC, e.g. "2026-06-20T14:00:00Z"
    crs: str
    format: str


class SatelliteImagery(BaseModel):
    """WMS parameters for all configured EUMETView layers at a given moment."""

    generated_at: datetime
    layers: list[WmsLayerParams]


class ModelDay(BaseModel):
    date: Date
    values: DailyValues


class ModelSeries(BaseModel):
    """One model's forecast, tagged with provenance."""

    name: str
    role: Role
    resolution_km: Optional[float] = None
    max_horizon_days: Optional[int] = None
    days: list[ModelDay]


class Confidence(BaseModel):
    level: ConfidenceLevel
    # Numeric range for the confidence variable (consensus +/- spread).
    low: Optional[float] = None
    high: Optional[float] = None
    spread: Optional[float] = None


class ModelContribution(BaseModel):
    """A single model's values for one day, kept for the per-model breakdown."""

    model: str
    role: Role
    values: DailyValues


class DayConsensus(BaseModel):
    date: Date
    lead_day: int
    values: DailyValues
    confidence: Confidence
    breakdown: list[ModelContribution]


class AggregatedForecast(BaseModel):
    location: Location
    generated_at: datetime
    days: list[DayConsensus]


# ---------------------------------------------------------------------------
# Hourly forecast models
# ---------------------------------------------------------------------------

class ModelHour(BaseModel):
    date: datetime
    values: DailyValues


class HourSeries(BaseModel):
    """One model's hourly forecast, tagged with provenance."""

    name: str
    role: Role
    resolution_km: Optional[float] = None
    max_horizon_days: Optional[int] = None
    hours: list[ModelHour]


class HourContribution(BaseModel):
    """A single model's values for one hour, kept for the per-model breakdown."""

    model: str
    role: Role
    values: DailyValues


class HourConsensus(BaseModel):
    date: datetime
    lead_hour: int
    values: DailyValues
    confidence: Confidence
    breakdown: list[HourContribution]


class AggregatedHourlyForecast(BaseModel):
    location: Location
    generated_at: datetime
    hours: list[HourConsensus]
