## 1. Config

- [x] 1.1 Add `ecmwf_aifs025_single` to `GLOBAL_MODELS` in
  `meteo_aggregator/config.py`
- [x] 1.2 Add its `MODEL_META` entry (role `general`, `resolution_km` 25.0,
  `max_horizon_days` 15)
- [x] 1.3 Add AIFS weights to `WEIGHTS_NEAR_TERM` and `WEIGHTS_RANGE`, rebalancing
  the existing global weights

## 2. Verify

- [x] 2.1 `pytest` passes offline (59 passed). Weight-dependent aggregation/hourly
  tests updated to derive expected blends from `config.weight_for` rather than
  hardcoded constants; fixed `test_long_range_favors_ecmwf`, which never actually
  exercised the range bucket (a single-day series lands at `lead_day 0`).
- [x] 2.2 Live check: AIFS appears in the `breakdown` and contributes to blended
  variables; `precipitation_probability` and `uv_index` remain sourced from other
  models; AIFS persists across the horizon.

## 3. Docs

- [x] 3.1 Note ECMWF AIFS in the general-provider model list in the root
  `README.md`
