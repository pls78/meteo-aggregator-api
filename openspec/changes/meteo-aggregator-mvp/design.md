## Context

Greenfield project (only `openspec/` and `.claude/` scaffolding exist). The goal is an accurate local 7-day forecast assembled from multiple weather models. Research established the key facts that drive this design:

- **Open-Meteo** serves many global models (ECMWF, GFS, ICON) through one keyless JSON API, supports requesting multiple models in a single call (`models=`), and offers up to a 16-day horizon plus a separate **Ensemble API** for probabilistic spread.
- **ItaliaMeteo-ARPAE ICON-2i** (~2 km, Italy-wide, ~3-day horizon) is a genuinely distinct high-resolution regional model, also reachable through Open-Meteo (`italia_meteo_arpae_icon_2i`).
- **ARPA Lombardia's** own bulletin is *itself* DWD-ICON sourced from Open-Meteo, web-only with no clean data API — so scraping it would duplicate ICON numerically while adding fragility. ICON-2i is the better "local" signal and covers all of Italy.

The form factor is a reusable library core plus a thin HTTP layer, so the same backend can later serve a web app and an iOS app.

## Goals / Non-Goals

**Goals:**
- Clean separation between a **general** provider and a **swappable specialized-local** provider behind one interface.
- A **lead-time-weighted consensus** per day with a **per-day confidence** signal (level + numeric range).
- Always preserve the **per-model breakdown** with provenance alongside the consensus.
- Relocation (e.g. Lombardy → Toscana) handled by **config**, not code changes.
- Thin, stateless HTTP layer returning the aggregated forecast as JSON.

**Non-Goals:**
- No web or iOS frontend in this change (HTTP/JSON contract only).
- No scraping of ARPA Lombardia / ARPAT bulletins.
- No persistence, caching layer, auth, or rate limiting in the MVP.
- No nowcasting/radar, sub-daily consensus, or alerting.

## Decisions

### 1. Provider abstraction with explicit roles
A `ForecastProvider` ABC exposes `name`, `role` (`general` | `local`), and `async fetch(location, days) -> list[ModelSeries]`. Each `ModelSeries` carries provenance (model name, role, native resolution, max horizon). The client composes one general + one local provider.
- *Why:* The general/local split is the core user requirement and makes the local slot swappable.
- *Alternative considered:* a single multi-model fetch with no role tagging — rejected because lead-time weighting and the swap requirement need the roles to be first-class.

### 2. Both providers are Open-Meteo-backed (for now)
General provider requests global models (`ecmwf_ifs025,gfs_seamless,icon_seamless`); local provider requests `italia_meteo_arpae_icon_2i`. The local model id is **config-selected** (`config.local_provider`).
- *Why:* One keyless API, consistent variable schema, no scraping. ICON-2i covers all of Italy, so a Toscana move is a config change.
- *Alternative considered:* scraping ARPA Lombardia — rejected (no API, duplicates ICON, region-specific scraper per move).

### 3. Lead-time-weighted consensus
Per day/variable, the consensus is a weighted blend using a weight table keyed by lead time (days 1–3 favor the local high-res model; days 4–7 favor ECMWF). When the local model is absent past its ~3-day horizon, weights **renormalize automatically** over the remaining models.
- *Why:* Matches known model skill by lead time; degrades gracefully.
- *Alternative considered:* plain mean — rejected (ignores that skill varies by range and resolution).

### 3a. Non-blendable variables
Timestamps and categorical codes (`sunrise`, `sunset`, `weather_code`) are not numerically averaged; their consensus is the value from the highest-weighted model present that day, with native type preserved. Configured via `config.NON_BLENDABLE_VARIABLES`.
- *Why:* Averaging an ISO timestamp or a WMO weather code is meaningless; the highest-weighted model is the most trustworthy single source for that day.
- *Alternative considered:* mode/most-common code — deferred; the weighted pick is simpler and consistent with the blending philosophy.

### 4. Confidence from disagreement + ensemble spread
Per-day confidence combines (a) inter-model disagreement (spread/stddev across that day's model values) and (b) ensemble spread from the Open-Meteo Ensemble API. Output is both a categorical level (`high`/`medium`/`low`) and a numeric range (e.g. p25–p75).
- *Why:* Directly serves the original need to treat far-out days as probabilistic.
- *Alternative considered:* disagreement only — kept as a fallback when the ensemble call is unavailable, but ensemble adds true probabilistic spread.

### 5. Thin FastAPI layer over a pure library core
All logic lives in `meteo_aggregator/`; `api/` only parses the request, calls `client.get_forecast`, and serializes the pydantic result.
- *Why:* Keeps the core reusable and independently testable; the HTTP layer is replaceable.

## Risks / Trade-offs

- **Open-Meteo dependency / availability** → Treat it as the single upstream; isolate all HTTP in providers so a second backend can be added later without touching aggregation.
- **Ensemble API call adds latency / may fail** → Confidence degrades gracefully to disagreement-only when ensemble data is missing; ensemble fetch is best-effort.
- **Weight table is a heuristic, not validated skill scores** → Keep weights in `config.py` so they can be tuned; document them as provisional.
- **Non-commercial keyless tier limits** → Acceptable for MVP/personal use; document that commercial use needs an API key.
- **ICON-2i ~3-day horizon means days 4–7 lose the local signal** → Expected and handled by weight renormalization; confidence naturally widens at range.

## Migration Plan

Greenfield — no migration. Deploy is `uvicorn api.main:app`. Rollback is removing the change; nothing else depends on it.

## Open Questions

- Exact default weight values per lead-time bucket (provisional; tune after first live comparisons).
- Confidence-level thresholds (what spread maps to high/medium/low) — start with simple percentile cutoffs, revisit.

## Resolved

- **Default variable set** — settled on 16 daily variables (temperature & apparent temperature max/min, precipitation sum/hours/probability max & mean, max wind, mean cloud cover, max relative humidity, max UV index, daylight duration, sunrise, sunset, weather_code). Defined in `config.DAILY_VARIABLES`; `sunrise`/`sunset`/`weather_code` are non-blendable (see Decision 3a).
