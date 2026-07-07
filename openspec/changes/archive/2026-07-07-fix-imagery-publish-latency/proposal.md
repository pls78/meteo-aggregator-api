## Why

`/imagery` snapped the requested time to the most recent cadence boundary, but
EUMETSAT hasn't disseminated that frame yet (observed MTG/MSG latency ~10-16 min).
Requesting the un-published frame makes EUMETSAT's WMS fail — and it fails
*differently per layer*: some return HTTP 502, others a 200 ServiceException. The
new MTG RGB layers surfaced it loudly (502 → visibly broken tiles), but the bug
was pre-existing and also hit older layers (e.g. `mtg_fd:ir105_hrfi`) whenever the
current boundary wasn't published.

## What Changes

- Never snap to a frame newer than `now - EUMETVIEW_LATENCY_MINUTES` (default 20).
  Near-real-time and future requests clamp to the freshest reliably-published
  frame; historical requests (already older than that bound) are unchanged.
- Add `EUMETVIEW_LATENCY_MINUTES` to config.

## Capabilities

### Modified Capabilities
- `satellite-imagery`: per-layer time snapping now accounts for dissemination
  latency so returned times point at frames the WMS can actually serve.

## Impact

- **Code:** `meteo_aggregator/providers/eumetview.py` (clamp before snapping) and
  a config constant. No API/response-shape change; imagery is just ~20-30 min old
  instead of pointing at an unpublished frame.
- **Fixes:** intermittent 500/502/ServiceException on satellite overlays.
- Verified: all 10 layers return `200 image/png` at their clamped times.
