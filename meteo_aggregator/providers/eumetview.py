"""EUMETView WMS parameter builder.

This provider makes **no HTTP calls**. It computes WMS layer parameters
(endpoint, layer name, snapped TIME, CRS, format) that a map library (Leaflet,
MapLibre) can use to fetch satellite imagery tiles directly from EUMETSAT.

Time snapping rules:
- Regular layers: floor the requested datetime to the nearest cadence boundary
  (e.g. 14:07 on a 15-min layer → 14:00).
- Daily layers (cadence_minutes == 0): snap to midnight UTC of the requested day.
- Publish latency: never request a frame newer than ``now - EUMETVIEW_LATENCY_MINUTES``.
  The freshest cadence boundary is usually not disseminated yet, and requesting
  it makes EUMETSAT's WMS error (500/502/ServiceException). Historical requests
  (already older than that bound) are unaffected.
- Pre-archive requests: return time=None; the WMS will serve the latest available.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta, timezone

from meteo_aggregator import config
from meteo_aggregator.models import SatelliteImagery, WmsLayerParams


def _snap(dt: datetime, cadence_minutes: int) -> str:
    """Floor dt to the nearest cadence boundary and return an ISO 8601 string."""
    if cadence_minutes == 0:
        # Daily product: snap to start of UTC day.
        snapped = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        total_minutes = dt.hour * 60 + dt.minute
        floored_minutes = (total_minutes // cadence_minutes) * cadence_minutes
        snapped = dt.replace(
            hour=floored_minutes // 60,
            minute=floored_minutes % 60,
            second=0,
            microsecond=0,
        )
    return snapped.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_satellite_imagery(at: datetime | None = None) -> SatelliteImagery:
    """Return WMS parameters for all configured EUMETView layers at time ``at``.

    ``at`` should be UTC-aware; if naive it is treated as UTC. Defaults to now.
    """
    if at is None:
        at = datetime.now(timezone.utc)
    elif at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)

    # Never snap to a frame newer than the freshest reliably-published one. This
    # clamps near-real-time (and future) requests to now - latency while leaving
    # historical requests, already older than that bound, unchanged.
    freshest = datetime.now(timezone.utc) - timedelta(
        minutes=config.EUMETVIEW_LATENCY_MINUTES
    )
    effective = min(at, freshest)

    layers: list[WmsLayerParams] = []
    for defn in config.EUMETVIEW_LAYERS:
        archive_from = Date.fromisoformat(defn["archive_from"])
        if effective.date() < archive_from:
            time_str = None
        else:
            time_str = _snap(effective, defn["cadence_minutes"])

        layers.append(
            WmsLayerParams(
                wms_url=config.EUMETVIEW_WMS_URL,
                layer=defn["name"],
                title=defn["title"],
                time=time_str,
                crs=config.EUMETVIEW_CRS,
                format=config.EUMETVIEW_FORMAT,
            )
        )

    return SatelliteImagery(generated_at=at, layers=layers)
