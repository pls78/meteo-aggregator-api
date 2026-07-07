"""Tests for the EUMETView WMS parameter builder.

No network calls are made — the provider is pure computation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from meteo_aggregator import config
from meteo_aggregator.providers.eumetview import _snap, get_satellite_imagery

_UTC = timezone.utc


# --- _snap -------------------------------------------------------------------

def test_snap_15min_floors_to_boundary():
    dt = datetime(2026, 6, 20, 14, 7, 30, tzinfo=_UTC)
    assert _snap(dt, 15) == "2026-06-20T14:00:00Z"


def test_snap_15min_already_on_boundary():
    dt = datetime(2026, 6, 20, 14, 15, 0, tzinfo=_UTC)
    assert _snap(dt, 15) == "2026-06-20T14:15:00Z"


def test_snap_10min():
    dt = datetime(2026, 6, 20, 9, 23, 45, tzinfo=_UTC)
    assert _snap(dt, 10) == "2026-06-20T09:20:00Z"


def test_snap_5min():
    dt = datetime(2026, 6, 20, 9, 23, 45, tzinfo=_UTC)
    assert _snap(dt, 5) == "2026-06-20T09:20:00Z"


def test_snap_daily_snaps_to_midnight():
    dt = datetime(2026, 6, 20, 14, 37, 12, tzinfo=_UTC)
    assert _snap(dt, 0) == "2026-06-20T00:00:00Z"


# --- get_satellite_imagery ---------------------------------------------------

def test_returns_all_configured_layers():
    result = get_satellite_imagery(datetime(2026, 6, 20, 12, 0, tzinfo=_UTC))
    assert len(result.layers) == len(config.EUMETVIEW_LAYERS)


def test_all_layers_have_correct_wms_url_crs_format():
    result = get_satellite_imagery(datetime(2026, 6, 20, 12, 0, tzinfo=_UTC))
    for layer in result.layers:
        assert layer.wms_url == config.EUMETVIEW_WMS_URL
        assert layer.crs == config.EUMETVIEW_CRS
        assert layer.format == config.EUMETVIEW_FORMAT


def test_layer_names_match_config():
    result = get_satellite_imagery(datetime(2026, 6, 20, 12, 0, tzinfo=_UTC))
    names = [l.layer for l in result.layers]
    expected = [defn["name"] for defn in config.EUMETVIEW_LAYERS]
    assert names == expected


def test_time_snapped_for_15min_layer():
    at = datetime(2026, 6, 20, 14, 7, tzinfo=_UTC)
    result = get_satellite_imagery(at)
    clm = next(l for l in result.layers if l.layer == "msg_fes:clm")
    assert clm.time == "2026-06-20T14:00:00Z"


def test_time_snapped_for_10min_layer():
    at = datetime(2026, 6, 20, 9, 23, tzinfo=_UTC)
    result = get_satellite_imagery(at)
    mtg = next(l for l in result.layers if l.layer == "mtg_fd:ir105_hrfi")
    assert mtg.time == "2026-06-20T09:20:00Z"


def test_sentinel3_snapped_to_midnight():
    at = datetime(2026, 6, 20, 15, 45, tzinfo=_UTC)
    result = get_satellite_imagery(at)
    s3 = next(
        l for l in result.layers
        if l.layer == "copernicus:daily_sentinel3ab_olci_l1_rgb_fulres"
    )
    assert s3.time == "2026-06-20T00:00:00Z"


def test_pre_archive_time_yields_none():
    # MTG archive starts 2024-09-23; requesting before that → time=None.
    at = datetime(2024, 1, 1, 12, 0, tzinfo=_UTC)
    result = get_satellite_imagery(at)
    mtg = next(l for l in result.layers if l.layer == "mtg_fd:ir105_hrfi")
    assert mtg.time is None


def test_pre_archive_time_does_not_affect_older_layers():
    # msg_fes:clm archive starts 2020-09-01; a 2024-01-01 request is within range.
    at = datetime(2024, 1, 1, 12, 0, tzinfo=_UTC)
    result = get_satellite_imagery(at)
    clm = next(l for l in result.layers if l.layer == "msg_fes:clm")
    assert clm.time is not None


def test_naive_datetime_treated_as_utc():
    naive = datetime(2026, 6, 20, 12, 0)  # no tzinfo
    result = get_satellite_imagery(naive)
    clm = next(l for l in result.layers if l.layer == "msg_fes:clm")
    assert clm.time == "2026-06-20T12:00:00Z"


def test_defaults_to_now_when_no_time():
    result = get_satellite_imagery()
    # All layers with archives before today should have a non-None time.
    clm = next(l for l in result.layers if l.layer == "msg_fes:clm")
    assert clm.time is not None


def _parse(t: str) -> datetime:
    return datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def test_recent_request_clamped_to_publish_latency():
    # The freshest cadence boundary is not disseminated yet; a "now" request must
    # snap to no newer than now - EUMETVIEW_LATENCY_MINUTES (else EUMETSAT errors).
    now = datetime.now(timezone.utc)
    result = get_satellite_imagery(now)
    bound = now - timedelta(minutes=config.EUMETVIEW_LATENCY_MINUTES)
    for layer in result.layers:
        if layer.time is None:
            continue
        assert _parse(layer.time) <= bound


def test_future_request_clamped_to_publish_latency():
    # A future timestamp must not produce a future (unavailable) frame either.
    future = datetime.now(timezone.utc) + timedelta(hours=6)
    result = get_satellite_imagery(future)
    bound = datetime.now(timezone.utc) - timedelta(
        minutes=config.EUMETVIEW_LATENCY_MINUTES
    )
    geo = next(l for l in result.layers if l.layer == "mtg_fd:rgb_geocolour")
    assert _parse(geo.time) <= bound
