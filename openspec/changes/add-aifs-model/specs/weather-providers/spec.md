## MODIFIED Requirements

### Requirement: General provider via Open-Meteo global models

The system SHALL provide a `general` provider that retrieves multiple global
models from the Open-Meteo Forecast API in a single request, using the configured
model list and daily variable set, without requiring an API key. The configured
model list SHALL include both physics-based models (ECMWF IFS, GFS, ICON) and the
ECMWF AIFS machine-learning model, and models that do not supply a given variable
SHALL simply be absent from that variable's consensus (the blend renormalizes over
the models present per variable).

#### Scenario: Fetch multiple global models in one call

- **WHEN** the general provider fetches a 7-day forecast for a location
- **THEN** it issues a single Open-Meteo request listing the configured global
  models
- **AND** returns one model series per requested model, each covering the
  requested days

#### Scenario: Machine-learning model included in the mix

- **WHEN** the general provider fetches a forecast
- **THEN** the ECMWF AIFS model (`ecmwf_aifs025_single`) is among the returned
  series and contributes to the variables it supplies

#### Scenario: Model missing a variable is excluded from that variable

- **WHEN** a configured global model does not supply a given variable (e.g. AIFS
  for `precipitation_probability`)
- **THEN** that model does not contribute to that variable's consensus, while the
  other models' weights renormalize over the values actually present

#### Scenario: Requested horizon is bounded

- **WHEN** a forecast is requested for more than the supported maximum (16 days)
- **THEN** the provider limits the request to the supported maximum
