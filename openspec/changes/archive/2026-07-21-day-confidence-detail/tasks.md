## 1. Store: track the selected day's view mode

- [x] 1.1 Add `selectedDayView: 'hourly' | 'confidence'` to the app store in `src/store/appStore.tsx` (default `'hourly'`); reset it whenever `selectedDay` is cleared (no location, `clearDay`).
- [x] 1.2 Update `selectDay(date)` to set `selectedDayView = 'hourly'` while keeping its existing toggle-closed behavior on the same date.
- [x] 1.3 Add action `showDayConfidence(date)` that sets `selectedDay = date` and `selectedDayView = 'confidence'`, toggling closed when that day's confidence view is already open.
- [x] 1.4 Expose `selectedDayView` and `showDayConfidence` through the store hook/context so both layouts can read them.

## 2. Shared ConfidenceDetail component

- [x] 2.1 Create `src/components/confidence/ConfidenceDetail.tsx` taking a `DayConsensus`; render the consensus day-high and a list of each present model's `temperature_2m_max` from `day.breakdown`, omitting models missing the value.
- [x] 2.2 Add a model ID→display-name label (reuse an existing map if the app has one; otherwise define a small local map) for the per-model rows.
- [x] 2.3 Render the explanation paragraph from `day.confidence` (`level`, `spread`) stating that confidence reflects model disagreement on the day's high (and ensemble spread when available) and the band boundaries `high ≤ 1.5°C`, `medium ≤ 3.5°C`, else `low`; add a comment noting these mirror `meteo_aggregator/config.py`.

## 3. Desktop layout (LocationCard + HourlyPanel)

- [x] 3.1 In `src/components/panels/LocationCard.tsx`, restructure the day row from a single `<button>` into a grid `div` holding a main `<button>` (weekday/icon/temps → `selectDay`) and the confidence label as its own `<button>` (→ `showDayConfidence`), preserving classes, grid template, `aria-pressed`, hover/active styling.
- [x] 3.2 Give the confidence-label button an accessible name (e.g. `aria-label="Why {level} confidence?"`) and keep the visible level text.
- [x] 3.3 In `src/components/hourly/HourlyPanel.tsx`, when `selectedDayView === 'confidence'`, render `ConfidenceDetail` for the selected day in place of the hourly chart; otherwise render the chart as before. Skip the hourly fetch (or ignore its result) while in confidence mode.

## 4. Mobile layout (WeatherSheet)

- [x] 4.1 In `src/components/mobile/WeatherSheet.tsx`, apply the same day-row restructure (main button + separate confidence-label button) as the desktop card.
- [x] 4.2 In the sheet's "full" detail section, branch on `selectedDayView`: render `ConfidenceDetail` when `'confidence'`, the hourly chart when `'hourly'`.

## 5. Verify

- [x] 5.1 Desktop: clicking a day's confidence label shows per-model temps + explanation in the hourly slot; clicking elsewhere shows hourly; re-clicking the label collapses.
- [x] 5.2 Mobile: same behavior inside the bottom sheet's full section.
- [x] 5.3 Confirm keyboard focus/activation works for both the row button and the confidence-label button, and that a label click never triggers the hourly fetch/view (and vice versa).
- [x] 5.4 Confirm the explanation text matches the rendered level for high/medium/low days across a location with mixed confidence.
