from __future__ import annotations

import statistics
from datetime import date, timedelta

import pytest

from meteo_aggregator.aggregation import _confidence, aggregate
from meteo_aggregator.models import Location, ModelDay, ModelSeries

LOC = Location(latitude=45.46, longitude=9.19)
D0 = date(2026, 6, 16)


def _series(name, role, start_lead, temps, var="temperature_2m_max"):
    """Build a series whose days start at lead `start_lead` with given temps."""
    days = [
        ModelDay(date=D0 + timedelta(days=start_lead + i), values={var: t})
        for i, t in enumerate(temps)
    ]
    return ModelSeries(name=name, role=role, days=days)


def test_near_term_favors_local_high_res():
    series = [
        _series("italia_meteo_arpae_icon_2i", "local", 0, [10.0]),
        _series("ecmwf_ifs025", "general", 0, [20.0]),
        _series("icon_seamless", "general", 0, [20.0]),
        _series("gfs_seamless", "general", 0, [20.0]),
    ]
    forecast = aggregate(LOC, series)
    consensus = forecast.days[0].values["temperature_2m_max"]
    plain_mean = statistics.fmean([10.0, 20.0, 20.0, 20.0])  # 17.5
    # local weight 0.5 -> 0.5*10 + 0.5*20 = 15, pulled toward the local model.
    assert consensus == pytest.approx(15.0)
    assert consensus < plain_mean


def test_long_range_favors_ecmwf():
    # lead_day 3 (>= NEAR_TERM_DAYS): use the range weight table.
    series = [
        _series("ecmwf_ifs025", "general", 3, [10.0]),
        _series("icon_seamless", "general", 3, [20.0]),
        _series("gfs_seamless", "general", 3, [20.0]),
    ]
    forecast = aggregate(LOC, series)
    consensus = forecast.days[0].values["temperature_2m_max"]
    plain_mean = statistics.fmean([10.0, 20.0, 20.0])  # 16.67
    # ecmwf weight 0.5 -> 0.5*10 + 0.25*20 + 0.25*20 = 15, pulled toward ECMWF.
    assert consensus == pytest.approx(15.0)
    assert consensus < plain_mean


def test_weights_renormalize_when_local_absent():
    # Near-term day but only ecmwf + gfs present (local & icon missing).
    series = [
        _series("ecmwf_ifs025", "general", 0, [10.0]),
        _series("gfs_seamless", "general", 0, [20.0]),
    ]
    forecast = aggregate(LOC, series)
    consensus = forecast.days[0].values["temperature_2m_max"]
    # Renormalized over present weights: (0.25*10 + 0.10*20) / 0.35.
    expected = (0.25 * 10.0 + 0.10 * 20.0) / 0.35
    assert consensus == pytest.approx(expected)


def test_breakdown_preserves_every_present_model():
    series = [
        _series("italia_meteo_arpae_icon_2i", "local", 0, [10.0]),
        _series("ecmwf_ifs025", "general", 0, [20.0]),
    ]
    forecast = aggregate(LOC, series)
    breakdown = forecast.days[0].breakdown
    assert {c.model for c in breakdown} == {
        "italia_meteo_arpae_icon_2i",
        "ecmwf_ifs025",
    }
    local = next(c for c in breakdown if c.role == "local")
    assert local.values["temperature_2m_max"] == 10.0


def test_confidence_high_when_models_agree():
    conf = _confidence(consensus=20.0, values=[20.0, 20.5, 21.0], ensemble_spread=None)
    assert conf.level == "high"
    assert conf.low is not None and conf.high is not None


def test_confidence_low_when_models_disagree():
    conf = _confidence(consensus=20.0, values=[10.0, 20.0, 30.0], ensemble_spread=None)
    assert conf.level == "low"


def test_confidence_uses_ensemble_spread_when_larger():
    # Models agree (small disagreement) but ensemble spread is large -> low.
    conf = _confidence(consensus=20.0, values=[20.0, 20.1], ensemble_spread=5.0)
    assert conf.spread == pytest.approx(5.0)
    assert conf.level == "low"


def test_confidence_falls_back_to_disagreement_without_ensemble():
    conf = _confidence(consensus=20.0, values=[19.0, 21.0], ensemble_spread=None)
    # pstdev([19, 21]) = 1.0 -> high.
    assert conf.spread == pytest.approx(1.0)
    assert conf.level == "high"


def test_non_blendable_variables_pick_highest_weighted_model():
    # Near-term (lead_day 0): the local model carries the highest weight (0.50).
    series = [
        ModelSeries(
            name="italia_meteo_arpae_icon_2i",
            role="local",
            days=[
                ModelDay(
                    date=D0,
                    values={
                        "temperature_2m_max": 10.0,
                        "weather_code": 3,
                        "sunrise": "2026-06-16T05:30",
                    },
                )
            ],
        ),
        ModelSeries(
            name="ecmwf_ifs025",
            role="general",
            days=[
                ModelDay(
                    date=D0,
                    values={
                        "temperature_2m_max": 20.0,
                        "weather_code": 80,
                        "sunrise": "2026-06-16T05:31",
                    },
                )
            ],
        ),
    ]
    day = aggregate(LOC, series).days[0]
    # Numeric temp is blended (weights renormalized over the two present models),
    # pulled toward the higher-weighted local model.
    expected_temp = (0.50 * 10.0 + 0.25 * 20.0) / (0.50 + 0.25)
    assert day.values["temperature_2m_max"] == pytest.approx(expected_temp)
    # Categorical/string take the highest-weighted (local) model's value.
    assert day.values["weather_code"] == 3
    assert day.values["sunrise"] == "2026-06-16T05:30"


def test_non_blendable_skips_models_missing_the_value():
    # Highest-weighted model lacks weather_code -> fall through to the next.
    series = [
        ModelSeries(
            name="italia_meteo_arpae_icon_2i",
            role="local",
            days=[ModelDay(date=D0, values={"weather_code": None})],
        ),
        ModelSeries(
            name="ecmwf_ifs025",
            role="general",
            days=[ModelDay(date=D0, values={"weather_code": 61})],
        ),
    ]
    day = aggregate(LOC, series).days[0]
    assert day.values["weather_code"] == 61
