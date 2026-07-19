"""EUMETView WMS parameter builder.

This provider makes **no HTTP calls**. It computes WMS layer parameters
(endpoint, layer name, snapped TIME, CRS, format) that a map library (Leaflet,
MapLibre) can use to fetch satellite imagery tiles directly from EUMETSAT.

Time snapping rules:
- Regular layers: floor the requested datetime to the nearest cadence boundary
  (e.g. 14:07 on a 15-min layer → 14:00).
- Daily layers (cadence_minutes == 0): snap to midnight UTC of the requested day.
- Publish latency: never request a frame newer than ``now - latency``, where
  latency is the layer's ``latency_minutes`` (falling back to
  ``EUMETVIEW_LATENCY_MINUTES``). The freshest boundary is usually not
  disseminated yet, and requesting it makes EUMETSAT's WMS error
  (500/502/ServiceException); daily polar mosaics need a much larger lag because
  "today" is only partially accumulated. Historical requests (already older than
  the bound) are unaffected.
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


def _frame_step(dt: datetime, cadence_minutes: int, k: int) -> datetime:
    """Step ``dt`` back by ``k`` cadence intervals (one UTC day when daily)."""
    if cadence_minutes == 0:
        return dt - timedelta(days=k)
    return dt - timedelta(minutes=cadence_minutes * k)


def get_satellite_imagery(
    at: datetime | None = None, frames: int = 1
) -> SatelliteImagery:
    """Return WMS parameters for all configured EUMETView layers at time ``at``.

    ``at`` should be UTC-aware; if naive it is treated as UTC. Defaults to now.
    ``frames`` requests the N most-recent cadence-stepped frames per layer
    (newest first) for a time-lapse animation; frames stepping before a layer's
    archive are dropped, so a layer may return fewer than ``frames``.
    """
    if at is None:
        at = datetime.now(timezone.utc)
    elif at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    layers: list[WmsLayerParams] = []
    for defn in config.EUMETVIEW_LAYERS:
        # Never snap newer than the freshest reliably-published frame for this
        # layer. Clamps near-real-time (and future) requests to now - latency,
        # per-layer, while leaving older historical requests unchanged.
        latency = defn.get("latency_minutes", config.EUMETVIEW_LATENCY_MINUTES)
        effective = min(at, now - timedelta(minutes=latency))
        cadence = defn["cadence_minutes"]
        archive_from = Date.fromisoformat(defn["archive_from"])

        # Build the frame run newest-first, stopping once a frame would predate
        # the archive. The newest frame predating the archive yields [None].
        times: list[str | None] = []
        for k in range(frames):
            frame_dt = _frame_step(effective, cadence, k)
            if frame_dt.date() < archive_from:
                break
            times.append(_snap(frame_dt, cadence))
        if not times:
            times = [None]

        layers.append(
            WmsLayerParams(
                wms_url=config.EUMETVIEW_WMS_URL,
                layer=defn["name"],
                title=defn["title"],
                time=times[0],
                times=times,
                crs=config.EUMETVIEW_CRS,
                format=config.EUMETVIEW_FORMAT,
            )
        )

    return SatelliteImagery(generated_at=at, layers=layers)
