from __future__ import annotations

import statistics
from datetime import date, timedelta

import pytest

from meteo_aggregator import config
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
    # Renormalized weighted mean over the present near-term weights; the local
    # model carries the most weight, so the consensus is pulled toward its 10.0.
    temps = {
        "italia_meteo_arpae_icon_2i": 10.0,
        "ecmwf_ifs025": 20.0,
        "icon_seamless": 20.0,
        "gfs_seamless": 20.0,
    }
    w = {n: config.weight_for(n, 0) for n in temps}
    expected = sum(w[n] * temps[n] for n in temps) / sum(w.values())
    assert consensus == pytest.approx(expected)
    assert consensus < plain_mean  # favoured toward the local model


def test_long_range_favors_ecmwf():
    # aggregate() assigns lead_day by position in the present dates, so provide
    # four consecutive days and inspect the 4th (lead_day 3 >= NEAR_TERM_DAYS),
    # which uses the range weight table. Filler values for leads 0..2 are unused.
    filler = [15.0, 15.0, 15.0]
    series = [
        _series("ecmwf_ifs025", "general", 0, filler + [10.0]),
        _series("icon_seamless", "general", 0, filler + [20.0]),
        _series("gfs_seamless", "general", 0, filler + [20.0]),
    ]
    day = aggregate(LOC, series).days[3]
    assert day.lead_day == 3
    consensus = day.values["temperature_2m_max"]
    plain_mean = statistics.fmean([10.0, 20.0, 20.0])  # 16.67
    # Renormalized weighted mean over the range weights; ECMWF carries the most
    # weight at range, so the consensus is pulled toward its 10.0.
    temps = {"ecmwf_ifs025": 10.0, "icon_seamless": 20.0, "gfs_seamless": 20.0}
    w = {n: config.weight_for(n, 3) for n in temps}
    expected = sum(w[n] * temps[n] for n in temps) / sum(w.values())
    assert consensus == pytest.approx(expected)
    assert consensus < plain_mean  # favoured toward ECMWF


def test_weights_renormalize_when_local_absent():
    # Near-term day but only ecmwf + gfs present (local & icon missing).
    series = [
        _series("ecmwf_ifs025", "general", 0, [10.0]),
        _series("gfs_seamless", "general", 0, [20.0]),
    ]
    forecast = aggregate(LOC, series)
    consensus = forecast.days[0].values["temperature_2m_max"]
    # Renormalized over only the present models' weights.
    temps = {"ecmwf_ifs025": 10.0, "gfs_seamless": 20.0}
    w = {n: config.weight_for(n, 0) for n in temps}
    expected = sum(w[n] * temps[n] for n in temps) / sum(w.values())
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
    wl = config.weight_for("italia_meteo_arpae_icon_2i", 0)
    we = config.weight_for("ecmwf_ifs025", 0)
    expected_temp = (wl * 10.0 + we * 20.0) / (wl + we)
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
