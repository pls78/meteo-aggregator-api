## Context

The daily forecast pipeline (`providers/open_meteo.py`, `aggregation.py`,
`client.py`) fetches `daily=` variables from Open-Meteo, blends them with
lead-time weights, and computes per-day confidence. Open-Meteo's same
`/v1/forecast` endpoint supports a `hourly=` parameter with the same multi-model
suffix scheme, so hourly data is additive on the same upstream without new
external dependencies.

The existing `_parse_daily` / `fetch_open_meteo_daily` helpers and `aggregate`
function are the patterns to mirror, not to extend — changing them risks breaking
the daily pipeline.

## Goals / Non-Goals

**Goals:**
- `GET /hourly?lat&lon&hours` returning per-hour consensus, confidence, and
  per-model breakdown up to 168 hours (7 days).
- Same provider set as daily: ECMWF, GFS, ICON seamless (general) + ICON-2i
  (local, ~72h horizon).
- Per-hour confidence from inter-model spread on `temperature_2m`.
- `weather_code` and `wind_direction_10m` non-blendable (take highest-weight
  model's value).
- All new code; no changes to the daily pipeline.

**Non-Goals:**
- Ensemble spread for hourly confidence (inter-model disagreement suffices for
  MVP; ensemble hourly can be added later).
- Sub-hourly resolution.
- Hourly variables beyond the selected 10-variable set.
- Merging daily and hourly into one endpoint.

## Decisions

### 1. Parallel provider + aggregation, not extensions of the daily ones

New `fetch_open_meteo_hourly` helper and `OpenMeteoGeneralHourlyProvider` /
`OpenMeteoLocalHourlyProvider` classes, parallel to the daily equivalents.
New `aggregate_hourly` function and `HourConsensus` / `AggregatedHourlyForecast`
models.

- *Why:* Keeps the daily pipeline untouched (no regression risk). The code
  duplication is modest and the two pipelines differ enough (datetime vs date,
  different variables, different default horizons) that shared base classes would
  obscure more than they reveal.
- *Alternative considered:* Generalising existing providers to support both
  `daily=` and `hourly=` — rejected because it would require touching and
  re-testing the daily path.

### 2. Hourly variable set (10 variables)

`temperature_2m`, `apparent_temperature`, `precipitation`, `precipitation_probability`,
`wind_speed_10m`, `wind_direction_10m`, `weather_code`, `cloud_cover`,
`relative_humidity_2m`, `uv_index`.

Non-blendable: `weather_code` (categorical WMO code), `wind_direction_10m`
(averaging angular values is geometrically wrong — 0° and 350° would average to
175° instead of 355°). Both take the highest-weighted model's value.

- *Why:* A focused set covering temperature, precipitation, wind, sky, and UV —
  sufficient for "will it rain at 3pm?" without overloading the response.

### 3. Lead-time weighting reuses the daily weight table, converted to hours

Near-term boundary: `NEAR_TERM_DAYS * 24` hours (currently 3 × 24 = 72h). Hours
< 72 use `WEIGHTS_NEAR_TERM`; hours ≥ 72 use `WEIGHTS_RANGE`. The same
`weight_for(model, lead_day)` function is reused by converting `lead_hour //
24` to `lead_day`.

- *Why:* Consistent skill assumptions across daily and hourly. One weight table
  to maintain.

### 4. Max hourly horizon: 168 hours (7 days)

ECMWF supports 240h, GFS 384h, but hourly granularity past day 7 is not
meaningfully more useful than the daily forecast. Config: `MAX_HOURLY_HOURS =
168`, default `DEFAULT_HOURLY_HOURS = 48`.

### 5. Confidence from inter-model disagreement only (no ensemble)

Same logic as the daily fallback: spread = standard deviation of
`temperature_2m` across models for that hour; thresholds are the same
`CONFIDENCE_HIGH_MAX` / `CONFIDENCE_MEDIUM_MAX`. Ensemble hourly can be added
later without interface changes.

- *Why:* Ensemble adds a network call and latency; inter-model spread already
  gives a meaningful confidence signal for near-term hours.

## Risks / Trade-offs

- **Response size** — 168 hours × per-model breakdown is much larger than 7 days
  of daily data. Default to 48h to keep responses small; document that large
  `hours` values produce large payloads.
- **ICON-2i hourly horizon** — ICON-2i self-limits to ~72h just like in the
  daily pipeline (days with all-None values are dropped). Weights renormalize
  automatically past that horizon.
- **Timestamp alignment** — Open-Meteo returns hourly timestamps in the
  location's local timezone (`timezone=auto`). The parser must normalise to UTC
  or preserve the offset consistently.
- **Weight table reuse** — if the daily weight table is ever tuned, hourly
  weights change automatically. This is a feature, not a bug, but worth noting.
