## Why

The forecast payload tells you *what the numbers say* — but a satellite image
tells you *what is actually happening right now*. Showing a live cloud/IR layer
alongside the consensus forecast turns a numerical service into something a user
can sanity-check at a glance ("the model says sunny but I can see a cloud band
moving in"). EUMETSAT's EUMETView exposes public, keyless WMS layers that can
serve exactly this role without any API key or authentication.

## What Changes

- Add an **EUMETView imagery** capability: a thin provider that, given an
  optional timestamp, computes the correct WMS parameters for each configured
  satellite layer and returns them ready for a map library (Leaflet, MapLibre) to
  consume.
- Expose `GET /imagery?time=<ISO>` returning the WMS parameters for all layers
  as JSON. The client (web app or iOS map) registers each layer with its map
  library; no image bytes flow through this service.
- No changes to the forecast or geocoding pipelines.

## Capabilities

### New Capabilities
- `satellite-imagery`: Resolve a timestamp into ready-to-use WMS parameters for
  each configured EUMETSAT EUMETView layer (MTG IR, MTG lightning, MSG cloud
  mask, MSG fog, MSG instability indices, Sentinel-3 RGB). Time is snapped to
  each layer's cadence boundary; layers whose archive starts after the requested
  time return `time: null` (WMS will serve the most recent available).

### Modified Capabilities
<!-- None — the forecast and geocoding capabilities are untouched. -->

## Impact

- **New code:** `meteo_aggregator/providers/eumetview.py` (pure computation, no
  HTTP), `WmsLayerParams` and `SatelliteImagery` models, `get_satellite_imagery`
  client facade, `GET /imagery` API endpoint. Config gains the WMS URL, format,
  CRS, and layer catalog.
- **External services:** EUMETView WMS (`view.eumetsat.int`). Keyless for
  non-commercial use. No HTTP calls from this service — the map client fetches
  tiles directly from EUMETSAT.
- **No breaking changes** — purely additive.
