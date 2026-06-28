## ADDED Requirements

### Requirement: Aggregated forecast endpoint

The system SHALL expose an HTTP endpoint `GET /forecast` that accepts `lat`, `lon`, and an optional `days` parameter, and returns the aggregated forecast as JSON.

#### Scenario: Successful forecast request

- **WHEN** a client requests `GET /forecast?lat=45.5&lon=9.5&days=7`
- **THEN** the response is JSON containing, for each day, the consensus values, the confidence level and range, and the per-model breakdown

#### Scenario: Default day count

- **WHEN** a client requests `GET /forecast?lat=45.5&lon=9.5` without `days`
- **THEN** the system returns the default 7-day forecast

#### Scenario: Invalid coordinates

- **WHEN** a client requests the endpoint with missing or non-numeric `lat`/`lon`
- **THEN** the system responds with a client error and does not call upstream providers

### Requirement: Thin stateless HTTP layer

The HTTP layer SHALL contain no forecasting logic beyond request parsing and response serialization, delegating all fetching and aggregation to the library core.

#### Scenario: Logic delegated to the core

- **WHEN** the endpoint handles a request
- **THEN** it calls the library client to produce the forecast and serializes the result without performing aggregation itself
