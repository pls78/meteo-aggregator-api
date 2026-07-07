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

# Dissemination lag: the most recent cadence boundary is often not published yet,
# so requesting it makes EUMETSAT's WMS error (500/502/ServiceException). Never
# request a frame newer than now - this many minutes; observed MTG/MSG latency is
# ~10-16 min, so 20 gives a safe margin while keeping imagery near-real-time.
EUMETVIEW_LATENCY_MINUTES: int = 20

# Layer catalog. Each entry:
#   name            — WMS layer name (workspace:layer)
#   title           — human-readable label
#   cadence_minutes — archive time step; 0 = daily (snap to start of day)
#   archive_from    — earliest date available; requests before this get time=None
# Catalog favours visually rich RGB composites and avoids near-duplicate
# products (e.g. the same IR channel at two scan cadences, or two equivalent
# instability indices) — the more informative one of any such pair is kept.
EUMETVIEW_LAYERS: list[dict] = [
    {
        "name": "mtg_fd:rgb_geocolour",
        "title": "Geo Colour RGB (day + night) – MTG",
        "cadence_minutes": 10,
        "archive_from": "2024-09-23",
    },
    {
        "name": "mtg_fd:ir105_hrfi",
        "title": "IR 10.5 µm – MTG (cloud imagery)",
        "cadence_minutes": 10,
        "archive_from": "2024-09-23",
    },
    {
        "name": "mtg_fd:rgb_cloudphase",
        "title": "Cloud Phase RGB – MTG",
        "cadence_minutes": 10,
        "archive_from": "2024-09-23",
    },
    {
        "name": "mtg_fd:rgb_dust",
        "title": "Dust RGB (Saharan dust) – MTG",
        "cadence_minutes": 10,
        "archive_from": "2024-10-22",
    },
    {
        "name": "msg_fes:rgb_airmass",
        "title": "Airmass RGB – MSG 0°",
        "cadence_minutes": 15,
        "archive_from": "2020-09-01",
    },
    {
        "name": "msg_fes:rgb_convection",
        "title": "Convection RGB (storm potential) – MSG 0°",
        "cadence_minutes": 15,
        "archive_from": "2020-09-01",
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
        "name": "msg_rss:ir039_nrt",
        "title": "IR 3.9 µm Rapid Scan (fog/low cloud, 5-min) – MSG",
        "cadence_minutes": 5,
        "archive_from": "2020-02-12",
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
# ecmwf_aifs025_single is ECMWF's data-driven (machine-learning) model; it is
# blended alongside the physics-based models for diversity. It does not supply
# precipitation_probability or uv_index — aggregation renormalizes per variable,
# so it simply drops out of those.
GLOBAL_MODELS: list[str] = [
    "ecmwf_ifs025",
    "ecmwf_aifs025_single",
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
    "ecmwf_aifs025_single": {"role": "general", "resolution_km": 25.0, "max_horizon_days": 15},
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
    {"sunrise", "sunset", "weather_code", "wind_direction_10m"}
)

# Representative variable used to derive the per-day confidence (in °C).
CONFIDENCE_VARIABLE: str = "temperature_2m_max"

# --- Horizon --------------------------------------------------------------
DEFAULT_DAYS: int = 7
MAX_HORIZON_DAYS: int = 16

# --- Hourly horizon -------------------------------------------------------
DEFAULT_HOURLY_HOURS: int = 48
MAX_HOURLY_HOURS: int = 168  # 7 days; hourly past that adds little over daily

# Hourly variables requested from Open-Meteo.
HOURLY_VARIABLES: list[str] = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "precipitation_probability",
    "wind_speed_10m",
    "wind_direction_10m",
    "weather_code",
    "cloud_cover",
    "relative_humidity_2m",
    "uv_index",
]

# Representative variable for per-hour confidence (same as daily).
HOURLY_CONFIDENCE_VARIABLE: str = "temperature_2m"

# --- Lead-time weighting --------------------------------------------------
# Days 1..NEAR_TERM_DAYS favour the high-res local model; later days favour
# ECMWF. Weights are renormalized at aggregation over the models actually
# present for a given day, so absent models simply drop out.
NEAR_TERM_DAYS: int = 3

# Weights need not sum to 1: aggregation renormalizes over the models actually
# present for a given day and variable.
WEIGHTS_NEAR_TERM: dict[str, float] = {
    "italia_meteo_arpae_icon_2i": 0.50,
    "ecmwf_ifs025": 0.18,
    "ecmwf_aifs025_single": 0.12,
    "icon_seamless": 0.12,
    "gfs_seamless": 0.08,
}

WEIGHTS_RANGE: dict[str, float] = {
    "ecmwf_ifs025": 0.35,
    "ecmwf_aifs025_single": 0.30,
    "icon_seamless": 0.20,
    "gfs_seamless": 0.15,
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
