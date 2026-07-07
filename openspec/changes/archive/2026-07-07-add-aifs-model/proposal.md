## Why

ECMWF's AIFS — their machine-learning forecast model — is now free real-time
open data, and Open-Meteo already serves it as `ecmwf_aifs025_single`. Adding it
to the general model mix diversifies the consensus: AIFS is a data-driven model
whose error characteristics differ from the physics-based IFS/GFS/ICON, so
blending it in should improve robustness and sharpen the inter-model
disagreement signal that drives confidence. This is a config-only change — the
general provider, parser, and aggregation already support an arbitrary model
list.

## What Changes

- Add `ecmwf_aifs025_single` to `GLOBAL_MODELS`, with a `MODEL_META` entry
  (general, ~0.25° / 25 km, ~15-day horizon).
- Give AIFS a weight in `WEIGHTS_NEAR_TERM` and `WEIGHTS_RANGE`, rebalancing the
  existing global weights (weights renormalize over models present per day and
  per variable, so the exact totals are illustrative).
- No code changes: the general provider fetches `GLOBAL_MODELS` in one call, and
  the daily/hourly parsers already drop absent values so a model self-limits.

## AIFS variable coverage (verified against Open-Meteo)

AIFS provides all configured daily/hourly variables **except**
`precipitation_probability*` and `uv_index*`. Aggregation renormalizes
per-variable over the models that actually supply a value, so AIFS simply does
not contribute to those variables — no skew, no nulls introduced. (IFS already
omits UV as well, so UV coverage is unchanged.)

## Capabilities

### Modified Capabilities
- `weather-providers`: the general provider's global model set now includes the
  ECMWF AIFS machine-learning model alongside the physics-based ECMWF/GFS/ICON
  models.

## Impact

- **Config only:** `meteo_aggregator/config.py` (`GLOBAL_MODELS`, `MODEL_META`,
  the two weight tables). No new modules, dependencies, or external services.
- **Response shape unchanged;** AIFS appears as an extra entry in each day's/hour's
  `breakdown`. Slightly larger single Open-Meteo response (one more model).
- **No breaking changes.**
