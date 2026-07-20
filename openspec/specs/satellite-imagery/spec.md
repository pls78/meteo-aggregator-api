# satellite-imagery Specification

## Purpose
TBD - created by archiving change add-eumetview-imagery. Update Purpose after archive.
## Requirements
### Requirement: Satellite imagery endpoint

The system SHALL expose an HTTP endpoint `GET /imagery` that accepts an optional
`time` parameter (ISO 8601 UTC) and an optional `frames` parameter (integer,
default 1) and returns ready-to-use WMS parameters for every configured EUMETSAT
EUMETView layer as JSON. The response SHALL contain a `generated_at` timestamp
and a `layers` array, where each entry carries the WMS URL, layer name, title,
CRS, image format, a `times` array of snapped frame timestamps (newest first),
and a `time` field equal to the newest frame (`times[0]`) for backward
compatibility. `frames` requests the N most-recent frames per layer so a map
client can loop them into a time-lapse animation. No image bytes flow through
the service — the map client fetches tiles directly from EUMETSAT.

#### Scenario: Successful imagery request

- **WHEN** a client requests `GET /imagery?time=2026-06-20T12:00:00Z`
- **THEN** the response is JSON containing `generated_at` and a `layers` array
  with one entry per configured layer, each carrying `time` and a `times` array
  and ready to register with a map library

#### Scenario: Default timestamp

- **WHEN** a client requests `GET /imagery` without a `time`
- **THEN** the system computes the parameters as of now

#### Scenario: Default single frame

- **WHEN** a client requests `GET /imagery` without a `frames` parameter
- **THEN** each layer's `times` array has a single element equal to `time`,
  preserving the pre-animation response shape and values

#### Scenario: Multiple frames requested

- **WHEN** a client requests `GET /imagery?frames=5`
- **THEN** each layer's `times` array holds up to 5 snapped timestamps ordered
  newest first, and `time` equals the first (newest) element

#### Scenario: Invalid timestamp

- **WHEN** a client requests the endpoint with a non-parseable `time`
- **THEN** the system responds with HTTP 422 and does not return imagery
  parameters

#### Scenario: Invalid frame count

- **WHEN** a client requests the endpoint with a `frames` value that is not a
  positive integer within the allowed bound
- **THEN** the system responds with HTTP 422 and does not return imagery
  parameters

### Requirement: Per-layer time snapping

For each configured layer, the system SHALL snap the requested time down to that
layer's cadence boundary. To account for dissemination latency, the system SHALL
NOT return a time newer than `now - latency`, where `latency` is the layer's
configured `latency_minutes` (falling back to `EUMETVIEW_LATENCY_MINUTES`): a
requested time at or beyond that bound (including "now" and future times) is
clamped to it before snapping, while requests already older than the bound are
unaffected. Daily/low-cadence products that accumulate over the day SHALL use a
larger latency so a complete, processed day is requested rather than today's
partial mosaic. For a layer whose archive starts after the (clamped) requested
time, the system SHALL return `time: null` so the WMS serves the most recent
available image.

When `frames` is greater than 1, the system SHALL emit an ordered run of
cadence-stepped frames per layer, newest first, where frame `k` (0-indexed) is
the snapped time of `effective - k * cadence`. The system SHALL stop emitting
frames for a layer once a frame would predate that layer's archive start, so a
layer near its archive boundary MAY return fewer than `frames` timestamps. For a
layer whose newest frame already predates its archive, `times` SHALL be a single
`[null]` and `time` SHALL be `null`.

#### Scenario: Time snapped to the layer cadence

- **WHEN** imagery is requested for a time that falls between a layer's cadence
  boundaries (and older than the latency bound)
- **THEN** that layer's `time` is the most recent cadence boundary at or before the
  requested time

#### Scenario: Near-real-time request avoids the un-published frame

- **WHEN** imagery is requested for now (or a future time)
- **THEN** each layer's `time` is no newer than `now - latency` for that layer,
  snapped to the layer cadence, so the WMS can serve the frame

#### Scenario: Frames stepped by the layer cadence

- **WHEN** imagery is requested with `frames=N` for a regular layer
- **THEN** the layer's `times` are N timestamps each one cadence interval older
  than the previous, ordered newest first, all no newer than `now - latency`

#### Scenario: Frame run truncated at the archive start

- **WHEN** a `frames=N` request would step a layer back before its archive start
- **THEN** that layer's `times` contains only the frames at or after the archive
  start, with no `null` entries mixed in

#### Scenario: Request predates a layer's archive

- **WHEN** the requested time is earlier than a layer's archive start
- **THEN** that layer's `time` is `null`, `times` is `[null]`, while other layers
  still return their snapped times

### Requirement: Curated, visually rich layer catalog

The configured EUMETView layer catalog SHALL favour visually informative
products — including RGB composite imagery (e.g. Geo Colour, Dust, Cloud Phase,
Airmass, Convection) — and SHALL avoid near-duplicate layers that convey the same
information, retaining the most informative of any such group. All layers SHALL
remain keyless EUMETView WMS layers whose tiles are fetched directly by the map
client.

#### Scenario: Catalog includes RGB composite imagery

- **WHEN** the imagery endpoint returns the configured layers
- **THEN** the set includes RGB composite products, not only single-channel or
  derived-index layers

#### Scenario: No redundant near-duplicate layers

- **WHEN** two candidate layers would convey essentially the same product (e.g.
  the same channel at different scan cadences, or two equivalent convective
  instability indices)
- **THEN** only the most informative one is retained in the catalog

