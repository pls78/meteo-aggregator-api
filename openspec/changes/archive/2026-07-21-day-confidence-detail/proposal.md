## Why

Today a day row expands to hourly forecasts no matter where you click. The
confidence label (`high`/`medium`/`low`) tells the user *what* the confidence is
but never *why* — the per-model temperatures and the disagreement that drove the
level are fetched from the API but never shown. Clicking the confidence label is
the natural place to reveal that reasoning.

## What Changes

- Clicking a day's **confidence label** reveals, in place of that day's hourly
  forecast, the per-model day-high temperatures and an explanation of how the
  confidence level was computed (model spread → band).
- Clicking **anywhere else** on the day row keeps the existing behavior: expand
  the hourly forecast for that day.
- The day row is restructured so the confidence label is a separate click target
  from the rest of the row (the row is currently a single `<button>`; a nested
  interactive element is invalid). Applied in **both** layouts — desktop
  (`LocationCard`) and mobile (`WeatherSheet`).
- The shared expansion slot (desktop `HourlyPanel`, mobile sheet "full" section)
  gains a second mode: hourly chart **or** confidence detail for the selected day.
- No backend change: the per-model breakdown and confidence spread are already in
  the `/forecast` response. The confidence-band thresholds are surfaced in the UI
  copy (hardcoded, consistent with the existing "how it works" page coupling).

## Capabilities

### New Capabilities
- `confidence-detail`: the UI interaction and view that, on a confidence-label
  click, replaces a day's hourly expansion with the per-model temperatures and a
  plain-language explanation of the computed confidence level.

### Modified Capabilities
<!-- None. The /forecast response already exposes breakdown[] and confidence.spread;
     no backend requirement changes. -->

## Impact

- **UI repo** (`meteo-aggregator-ui`, local only):
  - `src/components/panels/LocationCard.tsx` — desktop day row restructure + label handler
  - `src/components/mobile/WeatherSheet.tsx` — mobile day row restructure + label handler + full-section branch
  - `src/components/hourly/HourlyPanel.tsx` — desktop expansion-slot branch
  - `src/store/appStore.tsx` — track which view (hourly vs confidence) the selected day shows
  - new shared `ConfidenceDetail` component
  - `src/api/types.ts` — already carries `breakdown` and `confidence.spread`; no change expected
- **Backend**: none.
- **Coupling**: the confidence thresholds/variable in the new copy are backend
  config values, hardcoded in the UI like the existing info page; note them where
  they are duplicated.
