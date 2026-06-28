# forecast-aggregation Specification

## Purpose
TBD - created by archiving change meteo-aggregator-mvp. Update Purpose after archive.
## Requirements
### Requirement: Lead-time-weighted daily consensus

The system SHALL combine all model series into a per-day, per-variable consensus value using a lead-time-dependent weight table that favors the high-resolution local model for the near term (days 1–3) and ECMWF at longer range (days 4–7).

#### Scenario: Near-term days favor the local high-res model

- **WHEN** computing the consensus for days within the local model's horizon
- **THEN** the local high-resolution model receives greater weight than the global models per the configured weight table

#### Scenario: Longer-range days favor ECMWF

- **WHEN** computing the consensus for days beyond the local model's horizon
- **THEN** ECMWF receives greater weight than the other available global models

### Requirement: Automatic weight renormalization

The system SHALL renormalize weights over the models actually present for a given day, so that missing models (e.g. the local model beyond its horizon) do not distort the consensus.

#### Scenario: Local model absent past its horizon

- **WHEN** the local model provides no value for a given day
- **THEN** the consensus is computed from the remaining models with their weights renormalized to sum to 1

### Requirement: Per-day confidence

The system SHALL compute a per-day confidence consisting of a categorical level (`high`, `medium`, or `low`) and a numeric range, derived from inter-model disagreement and, when available, ensemble spread.

#### Scenario: Tight agreement yields high confidence

- **WHEN** models agree closely and ensemble spread is small for a day
- **THEN** that day is reported with `high` confidence and a narrow numeric range

#### Scenario: Wide disagreement yields low confidence

- **WHEN** models disagree widely or ensemble spread is large for a day
- **THEN** that day is reported with `low` confidence and a wider numeric range

#### Scenario: Confidence without ensemble data

- **WHEN** ensemble spread is unavailable
- **THEN** confidence is computed from inter-model disagreement alone

### Requirement: Non-blendable variables use a representative value

The system SHALL NOT numerically average variables for which averaging is
meaningless (timestamps and categorical codes such as `sunrise`, `sunset`, and
`weather_code`). For these, the consensus SHALL be the value from the
highest-weighted model present for that day, preserving the value's native type.

#### Scenario: Categorical/timestamp variable takes the top-weighted model's value

- **WHEN** computing the consensus for a non-blendable variable on a given day
- **THEN** the value is taken from the highest-weighted model that provides it
- **AND** its native type is preserved (string for sunrise/sunset, integer code for weather_code)

#### Scenario: Top-weighted model missing the value

- **WHEN** the highest-weighted model has no value for a non-blendable variable
- **THEN** the value is taken from the next highest-weighted model that provides it

### Requirement: Per-model breakdown preserved

The system SHALL include the full per-model breakdown, with provenance, alongside the consensus for every day, so clients can display the headline value or drill into individual models.

#### Scenario: Breakdown accompanies consensus

- **WHEN** an aggregated forecast is produced
- **THEN** each day includes the consensus value, the confidence, and the contributing per-model values tagged by model name and role

