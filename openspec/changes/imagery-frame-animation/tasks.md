## 1. Model

- [x] 1.1 Add `times: list[Optional[str]]` to `WmsLayerParams` in
  `meteo_aggregator/models.py`, newest first; update the docstring to note
  `time == times[0]` and the `[null]` pre-archive case.

## 2. Provider

- [x] 2.1 Add a `frames: int = 1` parameter to `get_satellite_imagery` in
  `providers/eumetview.py`.
- [x] 2.2 For each layer, build the ordered `times` run: for `k` in `0..frames-1`
  snap `effective - k * cadence` (one UTC day step when `cadence_minutes == 0`),
  newest first; stop when a frame would predate `archive_from`.
- [x] 2.3 Set `time = times[0]`; when the newest frame predates the archive emit
  `times = [None]` and `time = None`.
- [x] 2.4 Add a `MAX_IMAGERY_FRAMES` (e.g. 24) constant to `config.py`.

## 3. API

- [x] 3.1 Add a `frames` query param to `GET /imagery` in `api/main.py` using
  `Query(default=1, ge=1, le=config.MAX_IMAGERY_FRAMES)` so bad values return 422.
- [x] 3.2 Pass `frames` through to `get_satellite_imagery`.

## 4. Tests

- [x] 4.1 `frames` default → each layer's `times` has one element equal to `time`
  (response unchanged from before).
- [x] 4.2 `frames=N` on a regular layer → N timestamps, each one cadence older,
  newest first, all within the latency bound.
- [x] 4.3 Frame run truncates at `archive_from` (fewer than N, no `null` mixed in).
- [x] 4.4 Pre-archive request → `times == [None]` and `time is None`.
- [x] 4.5 API: `?frames=5` returns arrays of expected length; `frames=0`,
  negative, and over-cap return 422.

## 5. Docs

- [x] 5.1 Update `api/README.md` imagery section: document `frames`, the `times`
  array, and newest-first ordering.
- [x] 5.2 Update `README.md` imagery blurb to mention the animation/frames option.
