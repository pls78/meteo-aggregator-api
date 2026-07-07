## MODIFIED Requirements

### Requirement: Browser CORS with a configurable allow-list

The HTTP layer SHALL emit CORS headers that permit a configurable set of browser
origins to read responses from the API. The allow-list SHALL be read from the
`ALLOWED_ORIGINS` environment variable (comma-separated); when it is unset, the
system SHALL fall back to the local web-UI dev origins (`http://localhost:5173`
and `http://127.0.0.1:5173`). The grant SHALL be limited to `GET` requests, since
the API is read-only. Origins that are not on the allow-list SHALL NOT be granted
access.

#### Scenario: Allowed origin can read a response

- **WHEN** a browser at an allow-listed origin issues `GET /forecast?lat=45.5&lon=9.5`
- **THEN** the response includes an `Access-Control-Allow-Origin` header for that
  origin, so the page can read the JSON body

#### Scenario: Production origin configured via environment

- **WHEN** `ALLOWED_ORIGINS` is set to a deployed UI origin (e.g.
  `https://meteo-aggregator.pages.dev`) and a browser at that origin issues a `GET`
- **THEN** the response grants that origin via `Access-Control-Allow-Origin`

#### Scenario: Default dev origins when unset

- **WHEN** `ALLOWED_ORIGINS` is not set
- **THEN** the local dev origins `http://localhost:5173` and
  `http://127.0.0.1:5173` are allowed

#### Scenario: Disallowed origin is not granted access

- **WHEN** a request carries an `Origin` that is not on the allow-list
- **THEN** the response does not grant that origin via
  `Access-Control-Allow-Origin`

## ADDED Requirements

### Requirement: Health-check endpoint

The HTTP layer SHALL expose `GET /health` that returns `200 OK` with a small JSON
body and performs no upstream provider calls, so container platforms and uptime
monitors can probe liveness cheaply.

#### Scenario: Health probe succeeds without upstream calls

- **WHEN** a client requests `GET /health`
- **THEN** the response is `200 OK` with body `{"status": "ok"}` and no upstream
  provider is contacted
