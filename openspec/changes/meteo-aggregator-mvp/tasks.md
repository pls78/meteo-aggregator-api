## 1. Project setup

- [x] 1.1 Create `pyproject.toml` with runtime deps (`httpx`, `pydantic`, `fastapi`, `uvicorn`) and dev deps (`pytest`, `pytest-asyncio`, `respx`)
- [x] 1.2 Create the `meteo_aggregator/` package and `api/` package layout with `__init__.py` files
- [x] 1.3 Add `config.py` with settings: global model list, local model id (default `italia_meteo_arpae_icon_2i`), default variable set, default `days`/max horizon, and the lead-time weight table

## 2. Domain models

- [x] 2.1 Define pydantic models in `models.py`: `Location`, `Variable`, `ModelSeries` (with provenance: model name, role, resolution, horizon), `Confidence` (level + range), `DayConsensus`, `AggregatedForecast`

## 3. Providers

- [x] 3.1 Implement `providers/base.py`: `ForecastProvider` ABC (`name`, `role`, async `fetch(location, days) -> list[ModelSeries]`)
- [x] 3.2 Implement `providers/open_meteo.py` (general): single Open-Meteo call requesting the configured global models with daily variables; cap days at the supported maximum
- [x] 3.3 Implement `providers/open_meteo_local.py` (local): fetch the config-selected model; return only the days the model provides
- [x] 3.4 Implement `providers/ensemble.py`: fetch ensemble spread from the Open-Meteo Ensemble API; return best-effort, degrade gracefully on failure

## 4. Aggregation

- [x] 4.1 Align all `ModelSeries` onto a per-day grid
- [x] 4.2 Compute lead-time-weighted consensus per day/variable using the weight table, with automatic renormalization over present models
- [x] 4.3 Compute per-day confidence (level + numeric range) from inter-model disagreement and, when present, ensemble spread; fall back to disagreement-only
- [x] 4.4 Assemble `AggregatedForecast` preserving the per-model breakdown with provenance for every day

## 5. Client facade

- [x] 5.1 Implement `client.py` `get_forecast(location, days)` orchestrating general + local + ensemble fetches and aggregation

## 6. HTTP layer

- [x] 6.1 Implement `api/main.py` FastAPI app with `GET /forecast?lat&lon&days` delegating to `client.get_forecast`
- [x] 6.2 Validate/parse query params (numeric `lat`/`lon`, optional `days` defaulting to 7); return client error on invalid coordinates without calling providers

## 7. Tests

- [x] 7.1 Add Open-Meteo response fixtures and `respx`-mocked unit tests for each provider (parsing + day-count behavior)
- [x] 7.2 Unit-test aggregation: near-term local favoring, ECMWF favoring at range, weight renormalization when local is absent, confidence mapping (incl. no-ensemble fallback)
- [x] 7.3 Test the API endpoint with a mocked client (success, default days, invalid coordinates)
- [x] 7.4 Add a network-gated/skippable live integration test for the user's Lombardy coords

## 8. Docs

- [x] 8.1 Write `README.md`: overview, running the API, and the local-provider swap instructions (Lombardy → Toscana via config)
