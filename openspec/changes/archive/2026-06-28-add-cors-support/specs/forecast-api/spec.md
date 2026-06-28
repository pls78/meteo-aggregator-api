## ADDED Requirements

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
