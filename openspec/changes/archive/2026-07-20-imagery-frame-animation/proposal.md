## Why

`GET /imagery` returns a single snapped frame per layer, so the map client can
only show a still image. A short ordered run of recent frames lets the client
loop them into a time-lapse animation, making cloud/storm/dust evolution
visible without any new data source — the WMS already serves arbitrary past
frames via its TIME dimension.

## What Changes

- Add an optional `frames` query parameter to `GET /imagery` (integer, default
  `1`). It requests the N most-recent cadence-stepped frames per layer, newest
  first.
- Each layer entry gains a `times` array (N snapped ISO-8601 timestamps, newest
  first) alongside the existing `time`. `time` stays and equals `times[0]` for
  backward compatibility.
- Frame stepping reuses the existing per-layer snapping, cadence, latency, and
  archive rules: frame *k* is `snap(effective - k * cadence)`; stepping stops
  (shorter array) once a frame would predate the layer's `archive_from`.
- Default `frames=1` preserves today's response shape and values (a one-element
  `times` plus the same `time`).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `satellite-imagery`: the imagery endpoint gains a `frames` parameter and a
  per-layer `times` array; the per-layer time-snapping requirement extends to
  emit an ordered run of cadence-stepped frames.

## Impact

- API: `GET /imagery` — new optional `frames` query param; response `layers[]`
  gains a `times` array (additive, non-breaking).
- Code: `meteo_aggregator/providers/eumetview.py` (frame stepping),
  `meteo_aggregator/models.py` (`WmsLayerParams.times`), `api/main.py`
  (parse/validate `frames`).
- Docs: `api/README.md`, `README.md` imagery sections.
- No new dependencies; no change to how tiles are fetched (client-side, direct
  from EUMETSAT).
