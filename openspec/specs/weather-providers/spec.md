# weather-providers Specification

## Purpose
TBD - created by archiving change meteo-aggregator-mvp. Update Purpose after archive.
## Requirements
### Requirement: Provider interface with explicit role

The system SHALL define a forecast provider interface exposing a `name`, a `role` of either `general` or `local`, and an asynchronous operation that fetches forecasts for a location and a requested number of days, returning one or more model series.

#### Scenario: Provider reports its identity and role

- **WHEN** a configured provider is inspected
- **THEN** it exposes a non-empty `name` and a `role` equal to `general` or `local`

#### Scenario: Provider returns model series for a location

- **WHEN** `fetch(location, days)` is called with a valid location and a positive day count
- **THEN** the provider returns a list of model series, each tagged with its model name, role, native resolution, and maximum horizon

### Requirement: General provider via Open-Meteo global models

The system SHALL provide a `general` provider that retrieves multiple global models (ECMWF, GFS, ICON) from the Open-Meteo Forecast API in a single request, using the configured model list and daily variable set, without requiring an API key.

#### Scenario: Fetch multiple global models in one call

- **WHEN** the general provider fetches a 7-day forecast for a location
- **THEN** it issues a single Open-Meteo request listing the configured global models
- **AND** returns one model series per requested model, each covering the requested days

#### Scenario: Requested horizon is bounded

- **WHEN** a forecast is requested for more than the supported maximum (16 days)
- **THEN** the provider limits the request to the supported maximum

### Requirement: Swappable specialized-local provider

The system SHALL provide a `local` provider whose model is selected by configuration (default `italia_meteo_arpae_icon_2i`), so that relocating to a different region requires only a configuration change and no code change.

#### Scenario: Default local model is ICON-2i

- **WHEN** no override is configured
- **THEN** the local provider fetches the `italia_meteo_arpae_icon_2i` model from Open-Meteo

#### Scenario: Local model is swapped by configuration

- **WHEN** the configured local model id is changed
- **THEN** the local provider fetches the newly configured model with no source-code changes

#### Scenario: Local provider self-limits to its native horizon

- **WHEN** a 7-day forecast is requested but the local model only provides ~3 days
- **THEN** the local provider returns series covering only the days the model actually provides

### Requirement: Ensemble spread retrieval

The system SHALL retrieve ensemble spread for a location from the Open-Meteo Ensemble API to support confidence computation, and SHALL degrade gracefully when ensemble data is unavailable.

#### Scenario: Ensemble spread is available

- **WHEN** ensemble data is requested for a location
- **THEN** the system returns per-day spread information suitable for confidence scoring

#### Scenario: Ensemble fetch fails

- **WHEN** the ensemble request fails or returns no data
- **THEN** the system continues without ensemble spread rather than failing the forecast

