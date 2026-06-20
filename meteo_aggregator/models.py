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
