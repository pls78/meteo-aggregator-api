# forecast-api Specification

## Purpose
TBD - created by archiving change meteo-aggregator-mvp. Update Purpose after archive.
## Requirements
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

### Requirement: Browser CORS for the local web UI

The HTTP layer SHALL emit CORS headers that permit the configured local web-UI
origins (`http://localhost:5173` and `http://127.0.0.1:5173`) to read responses
from the API. The grant SHALL be limited to `GET` requests, since the API is
read-only. Origins that are not on the allow-list SHALL NOT be granted access.

#### Scenario: Allowed origin can read a response

- **WHEN** a browser at `http://localhost:5173` issues `GET /forecast?lat=45.5&lon=9.5`
- **THEN** the response includes an `Access-Control-Allow-Origin` header for that
  origin, so the page can read the JSON body

#### Scenario: Preflight for an allowed origin succeeds

- **WHEN** the browser sends a `OPTIONS` preflight for a `GET` from
  `http://localhost:5173`
- **THEN** the response approves the request and advertises `GET` as an allowed
  method

#### Scenario: Disallowed origin is not granted access

- **WHEN** a request carries an `Origin` that is not on the allow-list
- **THEN** the response does not grant that origin via
  `Access-Control-Allow-Origin`

