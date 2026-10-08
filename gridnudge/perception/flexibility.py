"""Flexibility envelope forecasting perception engine.

Estimates the aggregate shiftable power (MW) available across the plugged EV fleet
by analyzing energy requirements, departure deadlines, and predicted nudge adoption probabilities.

DATA HONESTY (AGENTS.md Section 1.1): Labeled strictly as "Simulation".
"""

from typing import Any, Dict, List, Optional
import numpy as np


def compute_ev_shiftable_kwh(
    current_soc: float,
    target_soc: float,
    battery_kwh: float,
    charger_kw: float,
    hours_until_departure: float,
    peak_window_hours_remaining: float = 3.0,
) -> float:
    """Compute how much energy (kWh) an EV can safely shift out of the peak window.

    Args:
        current_soc: Current battery SOC [0.0, 1.0].
        target_soc: Target battery SOC at departure [0.0, 1.0].
        battery_kwh: Total battery pack size in kWh.
        charger_kw: Charging power limit in kW.
        hours_until_departure: Hours until scheduled departure deadline.
        peak_window_hours_remaining: Remaining duration of the evening peak period.
    """
    if current_soc >= target_soc or charger_kw <= 0.0 or hours_until_departure <= 0.0:
        return 0.0

    energy_needed_kwh = max(0.0, (target_soc - current_soc) * battery_kwh)

    # Energy that default uncontrolled charging would draw inside peak window
    peak_draw_limit_kwh = charger_kw * peak_window_hours_remaining
    e_default_in_peak = min(energy_needed_kwh, peak_draw_limit_kwh)

    # Time available to charge outside the peak window before departure
    hours_outside_peak = max(0.0, hours_until_departure - peak_window_hours_remaining)
    energy_possible_outside_peak = charger_kw * hours_outside_peak

    # The maximum energy that can be safely shifted without compromising departure target
    shiftable = min(e_default_in_peak, energy_possible_outside_peak)
    return round(float(max(0.0, shiftable)), 3)


def estimate_fleet_flexibility(
    eligible_evs: List[Dict[str, Any]],
    default_adoption_prob: float = 0.35,
    n_draws: int = 500,
    seed: int = 42,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, Any]:
    """Estimate probabilistic fleet flexibility envelope via Monte Carlo simulation.

    Args:
        eligible_evs: List of dicts with keys:
            current_soc, target_soc, battery_kwh, charger_kw,
            hours_until_departure, adoption_prob (optional).
        default_adoption_prob: Baseline expected adoption probability if not specified.
        n_draws: Number of Monte Carlo draws for adoption realization.
        seed: Random seed.
        rng: Optional explicit generator.

    Returns:
        Dict with median and quantile shiftable MW, labeled "Simulation".
    """
    if not eligible_evs:
        return {
            "eligible_ev_count": 0,
            "shiftable_mw_q50": 0.0,
            "shiftable_mw_q10": 0.0,
            "shiftable_mw_q90": 0.0,
            "total_potential_mwh": 0.0,
            "label": "Simulation",
        }

    draw_rng = rng if rng is not None else np.random.default_rng(seed)

    shiftable_kwh_list = []
    probs = []

    for ev in eligible_evs:
        kwh = compute_ev_shiftable_kwh(
            current_soc=ev.get("current_soc", 0.3),
            target_soc=ev.get("target_soc", 0.9),
            battery_kwh=ev.get("battery_kwh", 40.0),
            charger_kw=ev.get("charger_kw", 7.4),
            hours_until_departure=ev.get("hours_until_departure", 8.0),
            peak_window_hours_remaining=ev.get("peak_window_hours_remaining", 3.0),
        )
        p = ev.get("adoption_prob", default_adoption_prob)
        shiftable_kwh_list.append(kwh)
        probs.append(p)

    shiftable_arr = np.array(shiftable_kwh_list, dtype=float)
    probs_arr = np.clip(np.array(probs, dtype=float), 0.0, 1.0)

    # Monte Carlo realization of fleet adoption
    # Shape: (n_draws, n_evs)
    uniform_draws = draw_rng.uniform(0.0, 1.0, size=(n_draws, len(eligible_evs)))
    adoption_matrix = uniform_draws < probs_arr[np.newaxis, :]

    # Shifted kWh per realization
    shifted_kwh_draws = np.dot(adoption_matrix, shiftable_arr)
    # Average power over a 2-hour peak window in MW (kWh / 2h / 1000)
    shifted_mw_draws = shifted_kwh_draws / (2.0 * 1000.0)

    q10 = float(np.percentile(shifted_mw_draws, 10))
    q50 = float(np.percentile(shifted_mw_draws, 50))
    q90 = float(np.percentile(shifted_mw_draws, 90))
    total_potential_mwh = float(np.sum(shiftable_arr) / 1000.0)

    return {
        "eligible_ev_count": len(eligible_evs),
        "shiftable_mw_q50": round(q50, 3),
        "shiftable_mw_q10": round(q10, 3),
        "shiftable_mw_q90": round(q90, 3),
        "total_potential_mwh": round(total_potential_mwh, 3),
        "label": "Simulation",
    }
