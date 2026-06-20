"""Configuration for providers, variables, and aggregation weighting.

Everything tunable lives here so behaviour (model choice, the local-provider
swap, weighting, confidence thresholds) can change without touching logic.
"""

from __future__ import annotations

from typing import Literal

Role = Literal["general", "local"]

# --- Open-Meteo endpoints -------------------------------------------------
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# --- Geocoding ------------------------------------------------------------
# Place-name search defaults for the Open-Meteo Geocoding API.
GEOCODING_DEFAULT_COUNT: int = 10
GEOCODING_MAX_COUNT: int = 100
GEOCODING_LANGUAGE: str = "en"

# --- EUMETView satellite imagery ------------------------------------------
EUMETVIEW_WMS_URL: str = "https://view.eumetsat.int/geoserver/wms"
EUMETVIEW_CRS: str = "EPSG:3857"
EUMETVIEW_FORMAT: str = "image/png"

# Layer catalog. Each entry:
#   name            — WMS layer name (workspace:layer)
#   title           — human-readable label
#   cadence_minutes — archive time step; 0 = daily (snap to start of day)
#   archive_from    — earliest date available; requests before this get time=None
EUMETVIEW_LAYERS: list[dict] = [
    {
        "name": "mtg_fd:ir105_hrfi",
        "title": "IR 10.5 µm – MTG (cloud imagery)",
        "cadence_minutes": 10,
        "archive_from": "2024-09-23",
    },
    {
        "name": "mtg_fd:li_afa",
        "title": "Lightning Flash Area – MTG",
        "cadence_minutes": 5,
        "archive_from": "2025-05-30",
    },
    {
        "name": "msg_fes:clm",
        "title": "Cloud Mask – MSG 0°",
        "cadence_minutes": 15,
        "archive_from": "2020-09-01",
    },
    {
        "name": "msg_fes:ir039",
        "title": "IR 3.9 µm (fog/low cloud) – MSG 0°",
        "cadence_minutes": 15,
        "archive_from": "2020-09-01",
    },
    {
        "name": "msg_rss:ir039_nrt",
        "title": "IR 3.9 µm Rapid Scan (fog/low cloud, 5-min) – MSG",
        "cadence_minutes": 5,
        "archive_from": "2020-02-12",
    },
    {
        "name": "msg_fes:gii_kindex",
        "title": "K-Index (convective instability) – MSG 0°",
        "cadence_minutes": 15,
        "archive_from": "2021-06-06",
    },
    {
        "name": "msg_fes:gii_liftedindex",
        "title": "Lifted Index (convective instability) – MSG 0°",
        "cadence_minutes": 15,
        "archive_from": "2021-06-06",
    },
    {
        "name": "copernicus:daily_sentinel3ab_olci_l1_rgb_fulres",
        "title": "True-colour RGB Daily – Sentinel-3",
        "cadence_minutes": 0,
        "archive_from": "2020-02-17",
    },
]

# --- Models ---------------------------------------------------------------
# General provider: global models requested together in one call.
GLOBAL_MODELS: list[str] = [
    "ecmwf_ifs025",
    "gfs_seamless",
    "icon_seamless",
]

# Specialized-local provider: swap this id to relocate (e.g. another country's
# high-res model). ICON-2i covers all of Italy, so Lombardy -> Toscana needs
# no change here.
LOCAL_MODEL: str = "italia_meteo_arpae_icon_2i"

# Ensemble model used to estimate probabilistic spread for confidence.
ENSEMBLE_MODEL: str = "icon_seamless"

# Per-model metadata, carried as provenance on every series.
MODEL_META: dict[str, dict] = {
    "ecmwf_ifs025": {"role": "general", "resolution_km": 25.0, "max_horizon_days": 15},
    "gfs_seamless": {"role": "general", "resolution_km": 11.0, "max_horizon_days": 16},
    "icon_seamless": {"role": "general", "resolution_km": 11.0, "max_horizon_days": 7},
    "italia_meteo_arpae_icon_2i": {"role": "local", "resolution_km": 2.0, "max_horizon_days": 3},
}

# --- Variables ------------------------------------------------------------
# Daily aggregates requested from Open-Meteo. Configurable.
DAILY_VARIABLES: list[str] = [
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_hours",
    "precipitation_probability_max",
    "precipitation_probability_mean",
    "wind_speed_10m_max",
    "cloud_cover_mean",
    "relative_humidity_2m_max",
    "uv_index_max",
    "daylight_duration",
    "sunrise",
    "sunset",
    "weather_code",
]

# Variables that must NOT be numerically blended. Their consensus is taken from
# the highest-weighted model present (averaging strings/categories is meaningless):
#   - sunrise/sunset are ISO timestamps (strings)
#   - weather_code is a categorical WMO code
NON_BLENDABLE_VARIABLES: frozenset[str] = frozenset(
    {"sunrise", "sunset", "weather_code"}
)

# Representative variable used to derive the per-day confidence (in °C).
CONFIDENCE_VARIABLE: str = "temperature_2m_max"

# --- Horizon --------------------------------------------------------------
DEFAULT_DAYS: int = 7
MAX_HORIZON_DAYS: int = 16

# --- Lead-time weighting --------------------------------------------------
# Days 1..NEAR_TERM_DAYS favour the high-res local model; later days favour
# ECMWF. Weights are renormalized at aggregation over the models actually
# present for a given day, so absent models simply drop out.
NEAR_TERM_DAYS: int = 3

WEIGHTS_NEAR_TERM: dict[str, float] = {
    "italia_meteo_arpae_icon_2i": 0.50,
    "ecmwf_ifs025": 0.25,
    "icon_seamless": 0.15,
    "gfs_seamless": 0.10,
}

WEIGHTS_RANGE: dict[str, float] = {
    "ecmwf_ifs025": 0.50,
    "icon_seamless": 0.25,
    "gfs_seamless": 0.25,
}


def weight_for(model: str, lead_day: int) -> float:
    """Configured weight for a model at a given lead day (0-indexed).

    Returns 0.0 for models with no configured weight in the relevant bucket;
    aggregation renormalizes over the non-zero weights actually present.
    """
    if lead_day < NEAR_TERM_DAYS:
        return WEIGHTS_NEAR_TERM.get(model, 0.0)
    return WEIGHTS_RANGE.get(model, 0.0)


# --- Confidence thresholds (spread in °C of the confidence variable) ------
CONFIDENCE_HIGH_MAX: float = 1.5
CONFIDENCE_MEDIUM_MAX: float = 3.5
