## Why

The only entry point today, `GET /forecast`, requires raw `lat`/`lon`. Humans
(and the future web/iOS clients the README anticipates) think in place names, not
coordinates. We need a way to resolve a **place name → coordinates** so a client
can search for a location and then request its forecast. Open-Meteo offers a
keyless Geocoding API that fits the existing provider model exactly, so this is a
low-risk addition that touches none of the forecasting pipeline.

## What Changes

- Add a **location-search** capability: a thin provider over the Open-Meteo
  Geocoding API that takes a query string and returns matching places (name,
  coordinates, country/region, timezone, population).
- Expose `GET /search?name&count&language` returning the matching places as JSON,
  so a client searches by name and then feeds a result's coordinates into
  `GET /forecast`.
- No changes to providers, aggregation, or the forecast endpoint.

## Capabilities

### New Capabilities
- `location-search`: Resolve a place-name query into a ranked list of places
  (coordinates + provenance) via the Open-Meteo Geocoding API, exposed over a
  thin HTTP endpoint. Degrades to an empty list when there is no match.

### Modified Capabilities
<!-- None — the forecast capabilities are untouched. -->

## Impact

- **New code:** `meteo_aggregator/providers/geocoding.py`, a `Place` model in
  `models.py`, a `search_locations` client facade, and a `GET /search` endpoint
  in `api/main.py`. Config gains the geocoding endpoint + defaults.
- **External services:** Open-Meteo Geocoding API
  (`https://geocoding-api.open-meteo.com/v1/search`), keyless for non-commercial
  use.
- **No breaking changes** — purely additive.
