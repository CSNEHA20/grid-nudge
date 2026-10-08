"""Battery stress perception engine with semi-empirical degradation range modeling.

Evaluates relative battery health stress and comparative state-of-health (SOH) delta
intervals between candidate charging plans and default charging.

CRITICAL RULE (AGENTS.md Section 9): Never predict or claim absolute battery lifespan.
Always report relative differences between plans.
"""

from typing import Optional, Tuple
import numpy as np

from gridnudge.contracts import BatteryView


def compute_battery_stress_score(
    soc: float,
    charging_kw: float,
    battery_kwh: float,
    ambient_temp_c: float = 30.0,
    hours_at_high_soc: float = 0.0,
    depth_of_discharge: float = 0.50,
) -> float:
    """Compute normalized relative battery stress score [0.0, 1.0].

    Components:
    - High SOC exposure (> 80%): accelerated calendar aging.
    - C-rate (power / capacity): high charging current heat and mechanical stress.
    - Ambient/operating temperature (> 30 °C): Arrhenius thermal degradation.
    - Depth of discharge (DoD) during driving cycle.
    """
    soc_clamped = max(0.0, min(1.0, float(soc)))
    battery_kwh = max(1.0, float(battery_kwh))
    c_rate = max(0.0, float(charging_kw)) / battery_kwh

    # High SOC penalty (weighted by dwell duration at top of charge)
    high_soc_term = max(0.0, (soc_clamped - 0.80) / 0.20)
    dwell_term = min(1.0, hours_at_high_soc / 8.0)
    high_soc_penalty = (0.6 * high_soc_term + 0.4 * dwell_term) * 0.35

    # C-rate penalty (e.g. 50kW on 30kWh = 1.67C)
    c_rate_penalty = min(1.0, c_rate / 1.5) * 0.30

    # Temperature penalty (exponential Arrhenius tendency above 30°C)
    temp_penalty = max(0.0, (ambient_temp_c - 30.0) / 18.0) * 0.25

    # Depth of discharge penalty
    dod_penalty = max(0.0, (depth_of_discharge - 0.50) / 0.50) * 0.10

    total_score = high_soc_penalty + c_rate_penalty + temp_penalty + dod_penalty
    return round(float(min(1.0, max(0.0, total_score))), 4)


def estimate_soh_delta_range(
    plan_type: str,
    delay_hours: float = 0.0,
    is_slow_charge: bool = False,
    temp_drop_c: float = 4.0,
    n_draws: int = 200,
    seed: int = 42,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, float]:
    """Estimate relative SOH difference percentage range [p10, p90] vs default unmanaged plan.

    Positive values indicate relative SOH improvement (less degradation).
    Negative values indicate higher degradation than default.
    """
    if plan_type == "default":
        return (0.0, 0.0)

    draw_rng = rng if rng is not None else np.random.default_rng(seed)

    # Literature-grounded parameter distributions for calendar and cycle sensitivity
    # k_cal: % degradation avoided per hour of delayed high-SOC dwell at cooler night temps
    k_cal = draw_rng.uniform(0.0005, 0.0025, size=n_draws)
    # k_therm: % degradation avoided per °C reduction during charging
    k_therm = draw_rng.uniform(0.0003, 0.0012, size=n_draws)
    # k_slow: % degradation avoided by slow AC charging instead of fast DC charging
    k_slow = draw_rng.uniform(0.0020, 0.0080, size=n_draws)

    if plan_type in ("delay", "relocate"):
        # Benefits from cooler night temperature and avoiding long idle time at 100% SOC
        benefit = (k_cal * delay_hours) + (k_therm * max(0.0, temp_drop_c))
    elif plan_type == "slow_charge" or is_slow_charge:
        benefit = k_slow + (k_therm * max(0.0, temp_drop_c * 0.5))
    elif plan_type == "top_up_now":
        # Charging immediately during hot daytime adds a slight relative stress
        benefit = -1.0 * (draw_rng.uniform(0.001, 0.004, size=n_draws) + k_therm * 2.0)
    else:
        benefit = np.zeros(n_draws)

    p10 = float(np.percentile(benefit, 10))
    p90 = float(np.percentile(benefit, 90))

    # Return ordered range (min, max) in percentage units
    return (round(min(p10, p90), 4), round(max(p10, p90), 4))


def evaluate_battery_view(
    soc: float,
    battery_kwh: float,
    charging_kw: float,
    ambient_temp_c: float = 30.0,
    hours_at_high_soc: float = 0.0,
    depth_of_discharge: float = 0.50,
    plan_type: str = "default",
    delay_hours: float = 0.0,
    temp_drop_c: float = 4.0,
    n_draws: int = 200,
    seed: int = 42,
) -> BatteryView:
    """Evaluate and construct typed BatteryView contract object."""
    stress_score = compute_battery_stress_score(
        soc=soc,
        charging_kw=charging_kw,
        battery_kwh=battery_kwh,
        ambient_temp_c=ambient_temp_c,
        hours_at_high_soc=hours_at_high_soc,
        depth_of_discharge=depth_of_discharge,
    )
    soh_delta_range = estimate_soh_delta_range(
        plan_type=plan_type,
        delay_hours=delay_hours,
        temp_drop_c=temp_drop_c,
        n_draws=n_draws,
        seed=seed,
    )
    return BatteryView(
        stress_score=stress_score,
        soh_delta_range_pct=soh_delta_range,
    )
