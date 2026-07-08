## 1. Align the hourly fetch timezone

- [x] 1.1 In `meteo_aggregator/providers/open_meteo.py`, change `fetch_open_meteo_hourly`'s
      request param from `"timezone": "UTC"` to `"timezone": "auto"`

## 2. Docs

- [x] 2.1 Update the README "Hourly forecast" section to state that hourly timestamps are in
      the location's local timezone (matching the daily forecast), and that `hours[0]` is
      current conditions
- [x] 2.2 Update `api/README.md` if it documents the hourly timestamp timezone

## 3. Tests

- [x] 3.1 Add a test asserting that, given a location off UTC, the aggregated hourly `date`
      values group under the same local calendar day as the daily forecast (or that the fetch
      requests `timezone=auto`)
- [x] 3.2 Run `pytest`; update any existing hourly/provider assertion that assumed UTC-labelled
      timestamps

## 4. Verify

- [x] 4.1 `pytest` passes
- [x] 4.2 Live check (`METEO_LIVE=1 pytest` or a manual `curl`): for an Italian location, the
      first `/hourly` hours share the local day of the first `/forecast` day
