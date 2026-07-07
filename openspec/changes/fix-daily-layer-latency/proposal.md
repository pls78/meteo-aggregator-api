## Why

The Sentinel-3 "daily" true-colour layer rendered only some tiles — big swathes
(Europe, Asia, Africa) were blank. It is a polar-orbiter mosaic accumulated over
the UTC day, so "today" is only partially imaged and the product isn't complete or
processed until ~2 days later (yesterday's tiles even return 502). But `/imagery`
snapped it to *today's* midnight via the single global 20-minute latency, which
is correct for near-real-time geostationary layers and wrong for a daily polar
mosaic.

## What Changes

- Support a per-layer `latency_minutes` override in `EUMETVIEW_LAYERS`; the snap
  clamp uses it, falling back to the global `EUMETVIEW_LATENCY_MINUTES`.
- Set the Sentinel-3 daily layer to ~48 h, so it requests the day that ended two
  UTC days ago — complete and processed worldwide.

## Capabilities

### Modified Capabilities
- `satellite-imagery`: per-layer time snapping now honours a per-layer publish
  latency, so daily accumulated products request a complete day rather than
  today's partial mosaic.

## Impact

- **Config + provider:** a per-layer `latency_minutes` key and a small change in
  `eumetview.py` to apply latency per layer. No API/response-shape change.
- **Fixes:** the Sentinel-3 layer now covers the full globe (verified ~500 KB
  Europe tile vs ~116 KB partial before).
- Geostationary layers keep the 20-minute default — unchanged.
