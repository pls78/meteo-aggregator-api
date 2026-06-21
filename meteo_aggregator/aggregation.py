"""Combine model series into a per-day consensus with confidence + breakdown."""

from __future__ import annotations

import statistics
from datetime import date as Date
from datetime import datetime, timezone

from meteo_aggregator import config
from meteo_aggregator.models import (
    AggregatedForecast,
    AggregatedHourlyForecast,
    Confidence,
    DailyValue,
    DailyValues,
    DayConsensus,
    HourConsensus,
    HourContribution,
    HourSeries,
    Location,
    ModelContribution,
    ModelSeries,
)

# (name, series, that day's values) for the models present on a given day.
_Present = list[tuple[str, ModelSeries, DailyValues]]


def _confidence(consensus: float | None, values: list[float], ensemble_spread: float | None) -> Confidence:
    """Confidence from inter-model disagreement and (if present) ensemble spread.

    Spread is the larger of the two signals; level comes from configured
    thresholds; the numeric range is consensus +/- spread.
    """
    disagreement = statistics.pstdev(values) if len(values) >= 2 else 0.0
    candidates = [disagreement]
    if ensemble_spread is not None:
        candidates.append(ensemble_spread)
    spread = max(candidates)

    if spread <= config.CONFIDENCE_HIGH_MAX:
        level = "high"
    elif spread <= config.CONFIDENCE_MEDIUM_MAX:
        level = "medium"
    else:
        level = "low"

    low = high = None
    if consensus is not None:
        low = consensus - spread
        high = consensus + spread
    return Confidence(level=level, low=low, high=high, spread=spread)


def aggregate(
    location: Location,
    series_list: list[ModelSeries],
    ensemble_spread: dict[Date, float] | None = None,
    variables: list[str] | None = None,
) -> AggregatedForecast:
    variables = variables or config.DAILY_VARIABLES
    ensemble_spread = ensemble_spread or {}

    # Index every model's day by date for quick lookup.
    by_model: dict[str, tuple[ModelSeries, dict[Date, dict]]] = {
        s.name: (s, {d.date: d.values for d in s.days}) for s in series_list
    }
    all_dates = sorted({d.date for s in series_list for d in s.days})

    days: list[DayConsensus] = []
    for lead_day, day in enumerate(all_dates):
        # Models present this day, with provenance, for the breakdown.
        present = [
            (name, series, day_values[day])
            for name, (series, day_values) in by_model.items()
            if day in day_values
        ]
        breakdown = [
            ModelContribution(model=name, role=series.role, values=vals)
            for name, series, vals in present
        ]

        # Consensus per variable. Numeric variables are weight-blended (with
        # renormalization over present weights); non-blendable variables
        # (sunrise/sunset/weather_code) take the highest-weighted model's value.
        consensus_values: DailyValues = {}
        for var in variables:
            if var in config.NON_BLENDABLE_VARIABLES:
                consensus_values[var] = _pick_representative(present, var, lead_day)
                continue
            weighted: list[tuple[float, float]] = []  # (weight, value)
            for name, _series, vals in present:
                val = vals.get(var)
                if val is None:
                    continue
                weighted.append((config.weight_for(name, lead_day), val))
            consensus_values[var] = _blend(weighted)

        # Confidence on the representative variable.
        conf_var = config.CONFIDENCE_VARIABLE
        conf_values = [
            vals[conf_var]
            for _name, _series, vals in present
            if vals.get(conf_var) is not None
        ]
        confidence = _confidence(
            consensus_values.get(conf_var), conf_values, ensemble_spread.get(day)
        )

        days.append(
            DayConsensus(
                date=day,
                lead_day=lead_day,
                values=consensus_values,
                confidence=confidence,
                breakdown=breakdown,
            )
        )

    return AggregatedForecast(
        location=location,
        generated_at=datetime.now(timezone.utc),
        days=days,
    )


def aggregate_hourly(
    location: Location,
    series_list: list[HourSeries],
    variables: list[str] | None = None,
) -> AggregatedHourlyForecast:
    """Combine hourly model series into a per-hour consensus with confidence."""
    variables = variables or config.HOURLY_VARIABLES

    by_model: dict[str, tuple[HourSeries, dict[datetime, dict]]] = {
        s.name: (s, {h.date: h.values for h in s.hours}) for s in series_list
    }
    all_times = sorted({h.date for s in series_list for h in s.hours})

    hours: list[HourConsensus] = []
    for lead_hour, ts in enumerate(all_times):
        present = [
            (name, series, hour_values[ts])
            for name, (series, hour_values) in by_model.items()
            if ts in hour_values
        ]
        breakdown = [
            HourContribution(model=name, role=series.role, values=vals)
            for name, series, vals in present
        ]

        lead_day = lead_hour // 24
        consensus_values: DailyValues = {}
        for var in variables:
            if var in config.NON_BLENDABLE_VARIABLES:
                consensus_values[var] = _pick_representative(present, var, lead_day)
                continue
            weighted: list[tuple[float, float]] = []
            for name, _series, vals in present:
                val = vals.get(var)
                if val is None:
                    continue
                weighted.append((config.weight_for(name, lead_day), val))
            consensus_values[var] = _blend(weighted)

        conf_var = config.HOURLY_CONFIDENCE_VARIABLE
        conf_values = [
            vals[conf_var]
            for _name, _series, vals in present
            if vals.get(conf_var) is not None
        ]
        confidence = _confidence(consensus_values.get(conf_var), conf_values, None)

        hours.append(
            HourConsensus(
                date=ts,
                lead_hour=lead_hour,
                values=consensus_values,
                confidence=confidence,
                breakdown=breakdown,
            )
        )

    return AggregatedHourlyForecast(
        location=location,
        generated_at=datetime.now(timezone.utc),
        hours=hours,
    )


def _blend(weighted: list[tuple[float, float]]) -> float | None:
    """Weighted mean; falls back to a plain mean if all weights are zero."""
    if not weighted:
        return None
    total_w = sum(w for w, _ in weighted)
    if total_w <= 0:
        return statistics.fmean(v for _w, v in weighted)
    return sum(w * v for w, v in weighted) / total_w


def _pick_representative(present: _Present, var: str, lead_day: int) -> DailyValue:
    """Value of the highest-weighted present model for a non-blendable variable.

    Ties (and the all-zero-weight case) fall back to source order, so the first
    listed model wins.
    """
    candidates = [
        (config.weight_for(name, lead_day), idx, vals.get(var))
        for idx, (name, _series, vals) in enumerate(present)
        if vals.get(var) is not None
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda c: (-c[0], c[1]))
    return candidates[0][2]
