## Purpose

Provide a per-hour aggregated forecast — consensus values, confidence, and the
per-model breakdown — over a requested horizon, complementing the daily
`GET /forecast` capability for clients that need hourly resolution.

## Requirements

### Requirement: Hourly forecast endpoint

The system SHALL expose an HTTP endpoint `GET /hourly` that accepts `lat`, `lon`,
and an optional `hours` parameter, and returns a per-hour aggregated forecast as
JSON for up to 168 hours.

#### Scenario: Successful hourly forecast request

- **WHEN** a client requests `GET /hourly?lat=45.5&lon=9.5&hours=48`
- **THEN** the response is JSON containing, for each hour, the consensus values,
  the confidence level and range, and the per-model breakdown

#### Scenario: Default hour count

- **WHEN** a client requests `GET /hourly?lat=45.5&lon=9.5` without `hours`
- **THEN** the system returns the default 48-hour forecast

#### Scenario: Invalid coordinates

- **WHEN** a client requests the endpoint with missing or non-numeric `lat`/`lon`
- **THEN** the system responds with a client error and does not call upstream
  providers

### Requirement: Per-hour lead-time-weighted consensus

The system SHALL compute a weighted consensus for each hour and each variable,
using the same lead-time weight table as the daily forecast. Hours within the
near-term window (lead hours < `NEAR_TERM_DAYS × 24`) SHALL favour the local
high-res model; later hours SHALL favour ECMWF. Weights SHALL renormalize
automatically over the models present for a given hour.

#### Scenario: Local model favoured in near-term hours

- **WHEN** ICON-2i data is available for hour 12
- **THEN** ICON-2i carries the highest weight in the consensus for that hour

#### Scenario: Local model absent beyond its horizon

- **WHEN** the local model has no data for hour 96 (beyond ~72h)
- **THEN** the weights renormalize over the general models and the consensus is
  still returned

### Requirement: Non-blendable hourly variables

`weather_code` and `wind_direction_10m` SHALL NOT be numerically averaged.
Their consensus SHALL be the value from the highest-weighted model present for
that hour, preserving native type.

#### Scenario: Wind direction consensus

- **WHEN** models report wind directions of 10°, 350°, and 5° for an hour
- **THEN** the consensus is the value from the highest-weighted model, not the
  arithmetic mean (which would be meaningless for angular values)

### Requirement: Per-hour confidence

The system SHALL compute a per-hour confidence (`level` + numeric `low`/`high`/
`spread`) from the inter-model disagreement on `temperature_2m`, using the same
thresholds as the daily confidence.

#### Scenario: High confidence when models agree

- **WHEN** all models report similar temperatures for an hour (spread ≤
  `CONFIDENCE_HIGH_MAX`)
- **THEN** the confidence level for that hour is `"high"`

#### Scenario: Confidence degrades at longer lead times

- **WHEN** models diverge significantly for an hour far in the future
- **THEN** the confidence level reflects that disagreement (`"medium"` or `"low"`)

### Requirement: Thin stateless hourly HTTP layer

The HTTP layer SHALL contain no forecasting logic beyond request parsing and
response serialization, delegating all fetching and aggregation to the library
core.

#### Scenario: Logic delegated to the core

- **WHEN** the `/hourly` endpoint handles a request
- **THEN** it calls the library client and serializes the result without
  performing aggregation itself
