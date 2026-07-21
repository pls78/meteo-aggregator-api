## Context

The UI (`meteo-aggregator-ui`, React + TS + Zustand-style store + React Query)
renders daily forecasts in two runtime-switched layouts: desktop `LocationCard`
and mobile `WeatherSheet`. Each day is a single full-width `<button>` whose
`onClick` calls `selectDay(date)` on the shared app store; the confidence label
is a `<span>` nested as the 4th grid child inside that button. `selectDay`
toggles `selectedDay: string | null`. When set, the expansion area (desktop
`HourlyPanel`, mobile sheet "full" section) lazily fetches and renders the
hourly chart for that day.

The `/forecast` response already carries everything the new view needs:
`day.breakdown[]` (per-model `{model, role, values}`, including
`temperature_2m_max`) and `day.confidence` (`{level, low, high, spread}`). Both
are typed in `src/api/types.ts` but currently unused by the day rows. Confidence
is computed backend-side (`meteo_aggregator/aggregation.py::_confidence`) as a
band on `spread` = max(inter-model stddev of `temperature_2m_max`, ICON ensemble
stddev), with thresholds `high ≤ 1.5`, `medium ≤ 3.5`, else `low`.

## Goals / Non-Goals

**Goals:**
- Confidence-label click shows per-model day-high temps + a plain-language
  explanation of the level, in the same slot the hourly view uses.
- Any other click on the row keeps the existing hourly behavior, unchanged.
- One consistent implementation shared by desktop and mobile.
- No backend change, no extra network calls (reuse data already fetched).

**Non-Goals:**
- Exposing a new confidence "rationale" field from the API.
- Splitting the ensemble-spread vs inter-model-disagreement components (not in
  the response; the single `spread` number is what we explain).
- Reworking the hourly view itself or the day-row layout beyond what is needed
  to separate the label as a click target.

## Decisions

**1. UI-only; derive the explanation from existing data.**
The breakdown and `confidence.spread` are already in the response. The band
thresholds (1.5 / 3.5) and the confidence variable ("day-high temperature") are
backend config; we hardcode them in the explanation copy, consistent with the
existing "how it works" info page that already duplicates backend figures. Add a
short comment at each duplication point noting the backend source.
*Alternative — add a `rationale`/`reason` string to the backend `Confidence`
model:* rejected for now; it couples a UI wording change to a backend deploy and
duplicates thresholds the UI can already interpret. Left as an open question if
the copy needs to reflect the disagreement-vs-ensemble split.

**2. Track the selected day's view mode in the store.**
Add `selectedDayView: 'hourly' | 'confidence'` to the app store (default
`'hourly'`). New action `showDayConfidence(date)` sets `selectedDay = date` and
`selectedDayView = 'confidence'` (and toggles closed if the same day's
confidence is already open). Keep `selectDay(date)` behavior but have it set
`selectedDayView = 'hourly'`. This lets a single `selectedDay` drive both the
existing lazy hourly fetch and the new view, and both layouts read the same
state.
*Alternative — a separate `confidenceDay` field:* rejected; two open-day fields
risk both being set and complicate the "only one expansion" invariant.

**3. Restructure the day row to expose the label as its own target.**
A nested interactive element inside a `<button>` is invalid HTML. Change the row
from a single `<button>` into a grid container (`div`) holding two controls: a
main `<button>` covering the weekday/icon/temps columns (calls `selectDay`), and
the confidence label as its own `<button>` (calls `showDayConfidence`). Preserve
current classes, `aria-pressed`, hover/active styling, and the
`grid-cols-[2.5rem_1.5rem_1fr_auto]` template. Apply identically in
`LocationCard.tsx` and `WeatherSheet.tsx`.
*Alternative — keep the outer button and `stopPropagation()` on a
`role="button"` span:* workable but keeps invalid-nesting semantics and needs a
manual key handler; the two-button split is cleaner and equally small.

**4. One shared `ConfidenceDetail` component.**
New component takes a `DayConsensus` and renders: the consensus day-high, a list
of each present model's day-high (label by model, omit models missing the value),
and the explanation paragraph (level + spread + band boundaries). Rendered by
desktop `HourlyPanel` (when `selectedDayView === 'confidence'`, in place of the
chart) and by the mobile sheet's full section (same branch). Model display names
reuse whatever mapping the app already has for model IDs; if none, add a small
local label map.

## Risks / Trade-offs

- **Threshold copy drifts from backend config** → hardcoded 1.5 / 3.5 could go
  stale if backend thresholds change. Mitigation: comment at the duplication
  point referencing `meteo_aggregator/config.py`; this matches the existing
  info-page coupling the project already accepts.
- **Two layouts drift** → the row restructure and the detail branch must land in
  both `LocationCard` and `WeatherSheet`. Mitigation: shared store action +
  shared `ConfidenceDetail` component so only the row markup differs.
- **Accessibility of the split row** → two focusable controls per row instead of
  one. Mitigation: give each a clear `aria-label`/`title`; keep `aria-pressed`
  on the main button; ensure the label button has an accessible name beyond the
  bare level word (e.g. "Why medium confidence?").
- **Mobile ergonomics** → the label is a small tap target inside a dense row.
  Mitigation: keep adequate padding; the label already has `px-1.5 py-0.5`.

## Open Questions

- Should the explanation eventually reflect the ensemble-spread vs inter-model
  split? That would need a backend field; deferred (Decision 1).
- Model display names — confirm the UI already has an ID→name map to reuse, else
  add one in the new component.
