## Why

The daily forecast answers "what will the weather be like on Thursday?" but not
"will it rain at 3pm?" — a key practical question for planning activities. Adding
hourly resolution for the near-term (up to 7 days / 168 hours) fills this gap
using the same Open-Meteo providers already in place, with no new upstream
dependencies.

## What Changes

- Add a `GET /hourly` endpoint returning a per-hour consensus forecast for up to
  168 hours, with per-hour confidence derived from inter-model spread.
- Fetch hourly data from the same general providers (ECMWF, GFS, ICON seamless)
  and the local provider (ICON-2i, ~3-day horizon) via Open-Meteo's `hourly=`
  parameter on the same forecast endpoint.
- Introduce a focused set of hourly variables: `temperature_2m`,
  `apparent_temperature`, `precipitation`, `precipitation_probability`,
  `wind_speed_10m`, `wind_direction_10m`, `weather_code`, `cloud_cover`,
  `relative_humidity_2m`, `uv_index`.
- Add new domain models (`HourConsensus`, `AggregatedHourlyForecast`) and a new
  aggregation function parallel to the existing daily one.
- No changes to `GET /forecast` (daily), `GET /search`, or `GET /imagery`.

## Capabilities

### New Capabilities
- `hourly-forecast`: Per-hour consensus from multiple Open-Meteo models with
  lead-time weighting, per-hour confidence from inter-model spread, and a
  per-model breakdown — mirroring the daily forecast structure at hourly
  resolution.

### Modified Capabilities
<!-- None — daily forecast, geocoding, and imagery are untouched. -->

## Impact

- **New code:** `meteo_aggregator/providers/open_meteo_hourly.py` (or reuse
  existing provider with `hourly=` param), `HourConsensus` /
  `AggregatedHourlyForecast` models, `aggregate_hourly` function,
  `get_hourly_forecast` client facade, `GET /hourly` API endpoint. Config gains
  hourly variable list and max horizon.
- **No breaking changes** — purely additive.
- **External services:** Open-Meteo Forecast API (`/v1/forecast`), same endpoint
  and keyless access as the daily providers.
