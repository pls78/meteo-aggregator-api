## ADDED Requirements

### Requirement: Place-name search endpoint

The system SHALL expose an HTTP endpoint `GET /search` that accepts a `name`
query string and optional `count` and `language` parameters, and returns a
ranked list of matching places — each with a name, coordinates, and available
provenance (country, region, timezone, population) — as JSON.

#### Scenario: Successful search

- **WHEN** a client requests `GET /search?name=Milano`
- **THEN** the response is a JSON array of places, each containing at least a
  `name`, `latitude`, and `longitude`, suitable for feeding into `GET /forecast`

#### Scenario: No match

- **WHEN** a client searches for a name with no geocoding match
- **THEN** the system responds `200 OK` with an empty JSON array

#### Scenario: Empty query

- **WHEN** a client requests the endpoint with a missing or empty `name`
- **THEN** the system responds with a client error and does not call the upstream
  geocoding service

### Requirement: Thin stateless search layer

The HTTP layer SHALL contain no search logic beyond request parsing and response
serialization, delegating the geocoding fetch and parsing to the library core.

#### Scenario: Logic delegated to the core

- **WHEN** the endpoint handles a search request
- **THEN** it calls the library client to produce the place list and serializes
  the result without performing the geocoding fetch itself
