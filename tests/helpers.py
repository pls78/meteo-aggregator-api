"""Shared test helpers."""

from __future__ import annotations


def build_daily_response(times: list[str], model_values: dict[str, dict[str, list]]) -> dict:
    """Build an Open-Meteo daily response with model-suffixed keys.

    ``model_values`` maps model id -> {variable -> column list}.
    """
    daily: dict = {"time": list(times)}
    for model, variables in model_values.items():
        for var, col in variables.items():
            daily[f"{var}_{model}"] = col
    return {"daily": daily}
