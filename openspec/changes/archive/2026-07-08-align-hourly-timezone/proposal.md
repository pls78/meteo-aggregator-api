## Why

The daily `GET /forecast` returns each day's `date` in the **location's local timezone**
(`timezone=auto`), but the hourly `GET /hourly` returns each hour's `date` in **UTC**
(`timezone=UTC`). A client therefore cannot reliably answer "which hours belong to forecast
day X?" — the two calendars are offset by the location's UTC offset, which the hourly
response does not expose. For Italy (UTC+1/+2) grouping hourly-by-daily-day naively drops the
late-evening hours of each local day and pulls in early hours of the next.

The new UI **hourly-for-a-day** view (tap a day → see that day's hours, and compare two
locations' hours for the same day) needs the two calendars to align.

## What Changes

- The hourly Open-Meteo fetch uses `timezone=auto` (the location's local timezone), matching
  the daily forecast. Hourly `date` values become location-local, so an hour's `YYYY-MM-DD`
  prefix matches the daily `date` for the same calendar day.
- `hours[0]` **stays** current conditions: the fetch anchors to the current hour via
  `forecast_hours`, which is independent of the `timezone` label, so the first returned hour
  is still "now" — only its printed offset changes.
- Both hourly providers (general and local) share the one fetch function, so they keep
  merging on identical per-hour timestamps.
- Update the README hourly note and the affected tests.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `hourly-forecast`: hourly timestamps are returned in the location's local timezone,
  consistent with the daily forecast, so hours can be grouped under a daily day.

## Impact

- **Code:** `meteo_aggregator/providers/open_meteo.py` (`fetch_open_meteo_hourly` timezone
  param). No change to aggregation, models, or the HTTP layer.
- **Docs/tests:** `README.md` hourly section; `tests/test_hourly.py` /
  `tests/test_providers.py` fixtures/assertions as needed.
- **Consumers:** the UI hourly-view change (`../meteo-aggregator-ui`
  `2026-07-08-add-hourly-view`) depends on this alignment.
