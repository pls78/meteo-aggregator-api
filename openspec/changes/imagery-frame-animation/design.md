## Context

`providers/eumetview.py` computes one snapped WMS TIME per layer, honouring
per-layer cadence, `latency_minutes`, and `archive_from`. The map client fetches
tiles directly from EUMETSAT's WMS, which serves any past frame via its TIME
dimension. Adding an animation means producing several past TIME values per
layer — pure computation, no new HTTP calls, no new data source.

## Goals / Non-Goals

**Goals:**
- Return an ordered run of recent frames per layer (newest first) so the client
  can loop a time-lapse.
- Reuse the existing snapping/latency/archive logic exactly — a single-frame
  response stays identical to today's.
- Keep it backward compatible and additive (`time` retained; `times` added).

**Non-Goals:**
- No client/UI work here (loop playback, preloading, timestamp overlay).
- No server-side tile proxying or caching — tiles still fetched client-side.
- No new frame-selection semantics beyond fixed cadence stepping (no gap filling
  across missing frames; the client tolerates an occasional WMS miss).

## Decisions

- **Compute frames by stepping `effective` back by `k * cadence`, then snap.**
  Snapping each stepped instant (rather than snapping once and subtracting) keeps
  all frames on exact cadence boundaries and reuses `_snap` unchanged. For daily
  layers (`cadence_minutes == 0`) the step is one UTC day.
  - *Alternative:* snap once, then subtract raw cadence — rejected; drifts off
    boundary for daily/irregular cases and duplicates `_snap`'s day logic.

- **Newest-first ordering; `time == times[0]`.** Matches how an animation is
  built (start at the freshest frame) and lets old clients keep reading `time`.

- **Truncate at `archive_from`, don't pad with nulls.** Frames stepping before a
  layer's archive are dropped, yielding a shorter `times`. A layer whose newest
  frame already predates its archive returns `times == [null]` and `time == null`
  — the existing pre-archive behaviour, expressed as a one-element array.

- **`frames` is a bounded positive integer, parsed in `api/main.py`.** Default 1;
  reject non-positive or over-limit with 422 (FastAPI `Query(ge=1, le=MAX)`).
  A cap (e.g. 24) bounds response size and discourages abusive archive walks.

- **Signature:** `get_satellite_imagery(at=None, frames=1)`. `frames=1` produces
  a one-element `times` and the same `time` as before, so existing tests and
  callers are unaffected.

## Risks / Trade-offs

- **Frame count vs. availability** → higher `frames` walks further into the
  archive where a frame may occasionally be missing on the WMS. Mitigation: keep
  the default at 1, document the cap, and let the client skip a failed tile.
- **Response size grows ~linearly with `frames`** → bounded by the `MAX` cap; the
  payload is still just timestamps, not image bytes.
- **Daily-layer animations span many days** → currently no daily layer is
  configured (Sentinel-3 removed), so the day-step path is exercised only by unit
  tests; behaviour is defined but not user-visible today.

## Migration Plan

Additive and backward compatible — deploy the API, then the client can adopt
`frames` when ready. Rollback is a straight revert; no data migration.
