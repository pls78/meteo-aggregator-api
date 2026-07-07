## ADDED Requirements

### Requirement: Curated, visually rich layer catalog

The configured EUMETView layer catalog SHALL favour visually informative
products — including RGB composite imagery (e.g. Geo Colour, Dust, Cloud Phase,
Airmass, Convection) — and SHALL avoid near-duplicate layers that convey the same
information, retaining the most informative of any such group. All layers SHALL
remain keyless EUMETView WMS layers whose tiles are fetched directly by the map
client.

#### Scenario: Catalog includes RGB composite imagery

- **WHEN** the imagery endpoint returns the configured layers
- **THEN** the set includes RGB composite products, not only single-channel or
  derived-index layers

#### Scenario: No redundant near-duplicate layers

- **WHEN** two candidate layers would convey essentially the same product (e.g.
  the same channel at different scan cadences, or two equivalent convective
  instability indices)
- **THEN** only the most informative one is retained in the catalog
