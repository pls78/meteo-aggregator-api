## ADDED Requirements

### Requirement: Satellite imagery endpoint

The system SHALL expose an HTTP endpoint `GET /imagery` that accepts an optional
`time` parameter (ISO 8601 UTC) and returns ready-to-use WMS parameters for every
configured EUMETSAT EUMETView layer as JSON. The response SHALL contain a
`generated_at` timestamp and a `layers` array, where each entry carries the WMS
URL, layer name, title, snapped `time`, CRS, and image format. No image bytes flow
through the service — the map client fetches tiles directly from EUMETSAT.

#### Scenario: Successful imagery request

- **WHEN** a client requests `GET /imagery?time=2026-06-20T12:00:00Z`
- **THEN** the response is JSON containing `generated_at` and a `layers` array with
  one entry per configured layer, each ready to register with a map library

#### Scenario: Default timestamp

- **WHEN** a client requests `GET /imagery` without a `time`
- **THEN** the system computes the parameters as of now

#### Scenario: Invalid timestamp

- **WHEN** a client requests the endpoint with a non-parseable `time`
- **THEN** the system responds with HTTP 422 and does not return imagery
  parameters

### Requirement: Per-layer time snapping

For each configured layer, the system SHALL snap the requested time down to that
layer's cadence boundary. For a layer whose archive starts after the requested
time, the system SHALL return `time: null` for that layer so the WMS serves the
most recent available image.

#### Scenario: Time snapped to the layer cadence

- **WHEN** imagery is requested for a time that falls between a layer's cadence
  boundaries
- **THEN** that layer's `time` is the most recent cadence boundary at or before the
  requested time

#### Scenario: Request predates a layer's archive

- **WHEN** the requested time is earlier than a layer's archive start
- **THEN** that layer's `time` is `null` while other layers still return their
  snapped times
