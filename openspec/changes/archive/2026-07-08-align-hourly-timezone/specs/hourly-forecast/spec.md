## ADDED Requirements

### Requirement: Hourly timestamps in the location's local timezone

Each hour's `date` in the `GET /hourly` response SHALL be expressed in the location's local
timezone, consistent with the daily `GET /forecast` `date`, so that a client can group the
hourly series by daily calendar day (an hour's `YYYY-MM-DD` prefix matches the daily `date`
for the same local day). The first returned hour SHALL remain the current hour (current
conditions).

#### Scenario: Hourly and daily calendars align

- **WHEN** a client requests `GET /hourly` and `GET /forecast` for the same location
- **THEN** each hour whose local calendar day is `D` carries a `date` beginning with `D`, and
  `D` matches the `date` of the corresponding daily-forecast day

#### Scenario: First hour is current conditions

- **WHEN** a client requests `GET /hourly`
- **THEN** `hours[0]` is the current hour for the location, regardless of the location's UTC
  offset
