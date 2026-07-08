## Context

Daily uses `timezone=auto`; hourly uses `timezone=UTC`. This inconsistency is invisible to
existing consumers that read hourly as a flat series anchored at `hours[0] = now`, but it
breaks any client that wants to slice the hourly series by the daily calendar.

## Decision

Align hourly to the daily convention: fetch hourly with `timezone=auto`.

### Why not expose the UTC offset instead?

We could keep hourly in UTC and add `utc_offset_seconds` (or a `timezone`) to the response so
clients convert themselves. That is strictly more surface area (a new field, client-side
offset math, DST edge cases) to reach the same place the daily forecast already reaches for
free. Matching the daily convention is the smaller, more consistent change.

### Why `hours[0]` is unaffected

The hourly fetch passes `forecast_hours=N`, which returns N hours starting at the **current
hour**. That anchor is a point in time; the `timezone` param only changes how each timestamp
is *printed*. So `hours[0]` remains the current hour under `auto` — current-conditions
semantics are preserved.

### Merge alignment

`aggregate_hourly` keys models by exact timestamp equality. Both the general and local
providers call the same `fetch_open_meteo_hourly`, so both request `timezone=auto` for the
same location and return identical local timestamps — the merge still lines up.

## Risks / Trade-offs

- **Timestamp offset now varies by location** (e.g. `+02:00`), where before it was always
  UTC. Documented in the README; ISO-8601 with offset is still valid ISO-8601.
- Tests that assumed UTC-labelled hourly timestamps get updated. The provider fixtures use
  naive `YYYY-MM-DDTHH:MM` strings (no offset), which parse the same way regardless of the
  request `timezone`, so most assertions on *values* are unaffected.
