## 1. Config

- [x] 1.1 Add `HOURLY_VARIABLES`, `DEFAULT_HOURLY_HOURS`, `MAX_HOURLY_HOURS` to
  `config.py`; add `wind_direction_10m` and `weather_code` to
  `NON_BLENDABLE_VARIABLES`

## 2. Domain models

- [x] 2.1 Add `ModelHour` (`date: datetime`, `values: DailyValues`) to `models.py`
- [x] 2.2 Add `HourSeries` (like `ModelSeries` but with `hours: list[ModelHour]`)
- [x] 2.3 Add `HourContribution` (like `ModelContribution`, for per-model breakdown)
- [x] 2.4 Add `HourConsensus` (`date: datetime`, `lead_hour: int`, `values`,
  `confidence`, `breakdown: list[HourContribution]`)
- [x] 2.5 Add `AggregatedHourlyForecast` (`location`, `generated_at`,
  `hours: list[HourConsensus]`)

## 3. Providers

- [x] 3.1 Add `_parse_hourly` and `fetch_open_meteo_hourly` to
  `providers/open_meteo.py`, mirroring `_parse_daily` / `fetch_open_meteo_daily`
  but using the `hourly` response key and `datetime.fromisoformat` for timestamps
- [x] 3.2 Add `OpenMeteoGeneralHourlyProvider` (general models, `hourly=` param)
- [x] 3.3 Add `OpenMeteoLocalHourlyProvider` (ICON-2i, self-limits to ~72h by
  dropping all-None hours)

## 4. Aggregation

- [x] 4.1 Add `aggregate_hourly(location, series, ensemble_spread={}) ->
  AggregatedHourlyForecast` to `aggregation.py`; reuse `weight_for(model,
  lead_hour // 24)` for weights; handle non-blendable variables; compute
  confidence from inter-model spread on `temperature_2m`

## 5. Client facade

- [x] 5.1 Add `get_hourly_forecast(location, hours, *, http_client)` to
  `client.py` orchestrating general + local hourly fetches and `aggregate_hourly`
- [x] 5.2 Export `get_hourly_forecast`, `HourConsensus`, `AggregatedHourlyForecast`
  from `__init__.py`

## 6. HTTP layer

- [x] 6.1 Add `GET /hourly?lat&lon&hours` to `api/main.py` mirroring the
  `/forecast` endpoint; default `hours=DEFAULT_HOURLY_HOURS`, max
  `MAX_HOURLY_HOURS`; reject invalid coordinates (HTTP 422) before any provider
  call

## 7. Tests

- [x] 7.1 Provider tests: `respx`-mock `_parse_hourly` for multi-model suffix
  parsing and all-None hour dropping (mirroring existing provider tests)
- [x] 7.2 Aggregation tests: near-term local favoring, weight renormalization past
  ICON-2i horizon, non-blendable variable handling (`weather_code`,
  `wind_direction_10m`), confidence mapping
- [x] 7.3 API tests: success shape, default hours, invalid coordinates (monkeypatch
  `get_hourly_forecast`)
- [x] 7.4 Network-gated live integration test for Lombardy coords

## 8. Docs

- [x] 8.1 Document `GET /hourly` in `api/README.md` (params, `HourConsensus`
  fields, variable list, example)
- [x] 8.2 Add a short "Hourly forecast" section to the root `README.md`
