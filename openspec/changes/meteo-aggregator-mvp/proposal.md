## Why

No single weather source is best across all lead times: high-resolution regional models win the near term (days 1–3), ECMWF wins at range, and days 5–7 are inherently probabilistic. To get a trustworthy **local 7-day forecast**, we need to aggregate multiple models and expose not just a number but how much to trust each day. This change establishes the MVP that does exactly that for a configurable location.

## What Changes

- Introduce a Python **library core** that fetches, aggregates, and scores multi-model weather forecasts, plus a **thin FastAPI HTTP layer** over it (so a future web app and iOS app can both consume the same JSON).
- Fetch **general** forecasts from Open-Meteo global models (ECMWF, GFS, ICON) in a single keyless call, up to a 16-day horizon.
- Fetch a **specialized-local** forecast from ItaliaMeteo-ARPAE **ICON-2i** (~2 km, Italy-wide, ~3-day horizon) via Open-Meteo, behind a **swappable provider slot selected by config** (relocation = config change, no code change).
- Aggregate into a **lead-time-weighted consensus** (local high-res favored days 1–3, ECMWF at range) with a **per-day confidence** (level + numeric range) derived from inter-model disagreement and Open-Meteo Ensemble spread.
- Always return the **full per-model breakdown** alongside the consensus headline, so simple clients use the headline and a future compare view can drill into raw series.
- Expose `GET /forecast?lat&lon&days` returning the aggregated forecast as JSON.

## Capabilities

### New Capabilities
- `weather-providers`: Provider abstraction with a clean general/specialized-local split and the Open-Meteo-backed implementations (global models, ICON-2i local, ensemble spread). The local slot is config-selected and swappable.
- `forecast-aggregation`: Combine provider outputs into a lead-time-weighted per-day consensus, compute per-day confidence (level + range), and preserve the per-model breakdown with provenance.
- `forecast-api`: Thin FastAPI HTTP layer exposing the aggregated forecast over JSON.

### Modified Capabilities
<!-- None — greenfield project, no existing specs. -->

## Impact

- **New code:** `meteo_aggregator/` library package (`models`, `config`, `providers/`, `aggregation`, `client`) and an `api/` FastAPI app. Greenfield — no existing code affected.
- **Dependencies (added):** `httpx`, `pydantic`, `fastapi`, `uvicorn`; dev: `pytest`, `pytest-asyncio`, `respx`.
- **External services:** Open-Meteo Forecast API and Ensemble API (no API key for non-commercial use).
- **No breaking changes** (nothing exists yet).
