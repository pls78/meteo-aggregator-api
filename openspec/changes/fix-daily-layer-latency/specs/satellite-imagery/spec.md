## MODIFIED Requirements

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

#### Scenario: Time snapped to the layer cadence

- **WHEN** imagery is requested for a time that falls between a layer's cadence
  boundaries (and older than the latency bound)
- **THEN** that layer's `time` is the most recent cadence boundary at or before the
  requested time

#### Scenario: Near-real-time request avoids the un-published frame

- **WHEN** imagery is requested for now (or a future time)
- **THEN** each layer's `time` is no newer than `now - latency` for that layer,
  snapped to the layer cadence, so the WMS can serve the frame

#### Scenario: Daily accumulated product requests a complete day

- **WHEN** a daily layer with a multi-day `latency_minutes` is requested for now
- **THEN** its `time` is a past UTC midnight old enough that the day's mosaic is
  complete worldwide, not today's partially-accumulated day

#### Scenario: Request predates a layer's archive

- **WHEN** the requested time is earlier than a layer's archive start
- **THEN** that layer's `time` is `null` while other layers still return their
  snapped times
