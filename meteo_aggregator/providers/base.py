"""Provider interface shared by the general and specialized-local providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from meteo_aggregator.config import Role
from meteo_aggregator.models import Location, ModelSeries


class ForecastProvider(ABC):
    """A source of model forecasts for a location.

    Implementations expose a stable ``name`` and a ``role`` (``general`` or
    ``local``) and asynchronously fetch one or more :class:`ModelSeries`.
    """

    name: str
    role: Role

    @abstractmethod
    async def fetch(self, location: Location, days: int) -> list[ModelSeries]:
        """Return model series for ``location`` covering up to ``days`` days."""
        raise NotImplementedError
