# confidence-detail Specification

## ADDED Requirements

### Requirement: Confidence label is a distinct click target

Within a day row, the confidence label (`high`/`medium`/`low`) SHALL be a
separate, keyboard-accessible click target from the rest of the row. A click on
the label SHALL NOT trigger the day's hourly expansion, and a click anywhere
else on the row SHALL NOT trigger the confidence detail. This SHALL hold in both
the desktop and the mobile layouts.

#### Scenario: Clicking the label does not open the hourly forecast

- **WHEN** the user clicks the confidence label of a day
- **THEN** the day's hourly forecast is not shown
- **AND** the day's confidence detail is shown instead

#### Scenario: Clicking elsewhere on the row keeps hourly behavior

- **WHEN** the user clicks any part of the day row other than the confidence
  label
- **THEN** the day's hourly forecast is shown, unchanged from the prior behavior

#### Scenario: Label is keyboard operable

- **WHEN** the user focuses the confidence label and activates it via keyboard
- **THEN** the confidence detail for that day is shown

### Requirement: Confidence detail replaces the hourly expansion for the day

When the confidence label is activated, the system SHALL show that day's
confidence detail in the same expansion area that normally shows the day's
hourly forecast. Only one of the two views SHALL be visible for the selected day
at a time.

#### Scenario: Confidence detail takes the hourly slot

- **WHEN** the confidence detail is shown for a day
- **THEN** it occupies the day's expansion area (desktop hourly panel / mobile
  sheet detail section) and the hourly chart for that day is not shown

#### Scenario: Switching back to hourly

- **WHEN** the confidence detail is shown and the user then clicks elsewhere on
  the same day row
- **THEN** the view switches to that day's hourly forecast

#### Scenario: Toggling the label closes the detail

- **WHEN** the confidence detail is shown for a day and the user activates that
  day's confidence label again
- **THEN** the expansion collapses, matching the existing toggle behavior of the
  day row

### Requirement: Per-model temperatures are shown

The confidence detail SHALL list, for the selected day, the day-high temperature
contributed by each model present in the forecast breakdown, labelled by model,
together with the consensus value. The values SHALL be read from the existing
`/forecast` response (`breakdown[].values` and `values`); no additional API call
SHALL be required.

#### Scenario: Each contributing model is listed

- **WHEN** the confidence detail is shown for a day
- **THEN** it lists each model in that day's breakdown with its day-high
  temperature and shows the consensus day-high

#### Scenario: Missing model is omitted

- **WHEN** a model provides no value for the selected day
- **THEN** that model is omitted from the list rather than shown with an empty
  value

### Requirement: Confidence computation is explained

The confidence detail SHALL present a plain-language explanation of how the
level was derived: that it reflects how much the models disagree on the day's
high temperature (and ensemble spread when available), the resulting spread
value, and which threshold band that spread falls into (`high`, `medium`, or
`low`). The explanation SHALL use the confidence data already in the response
(`confidence.level`, `confidence.spread`).

#### Scenario: Explanation reflects the level and spread

- **WHEN** the confidence detail is shown for a day
- **THEN** it states the day's confidence level, the model spread value, and the
  band boundaries that map spread to that level

#### Scenario: Explanation consistent with the label

- **WHEN** a day is labelled `high` confidence
- **THEN** the explanation shown for that day describes the reasoning for `high`
  and not for another level
