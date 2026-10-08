"""Physical ground-truth model for EV battery charging, driving, and stress.

This module represents actual physical reality inside the digital twin.
It is never accessed directly by perception or planner except via observable telemetry.
"""

from typing import Tuple


def charge_step(
    soc: float,
    battery_kwh: float,
    charger_kw: float,
    step_hours: float = 0.25,
    efficiency: float = 0.92,
    target_soc: float = 0.90,
) -> Tuple[float, float, float]:
    """Simulate a single charging timestep.

    Args:
        soc: Current battery state of charge [0.0, 1.0].
        battery_kwh: Total battery pack capacity in kWh.
        charger_kw: Maximum charging power capacity in kW.
        step_hours: Timestep duration in hours (default 0.25 h = 15 min).
        efficiency: Grid-to-battery charging efficiency (default 0.92).
        target_soc: Target SOC cutoff [0.0, 1.0].

    Returns:
        Tuple of (new_soc, power_kw_drawn, energy_kwh_delivered).
    """
    if soc >= target_soc or charger_kw <= 0.0 or step_hours <= 0.0:
        return soc, 0.0, 0.0

    # Taper charging power if SOC > 0.85
    taper_factor = 1.0
    if soc > 0.85:
        taper_factor = max(0.2, (1.0 - soc) / 0.15)

    effective_charger_kw = charger_kw * taper_factor

    # Stored energy needed to reach target SOC
    energy_needed_kwh = max(0.0, (target_soc - soc) * battery_kwh)

    # Maximum energy deliverable by charger in this time interval
    max_stored_kwh = effective_charger_kw * step_hours * efficiency

    # Energy actually stored in the battery
    energy_stored_kwh = min(energy_needed_kwh, max_stored_kwh)

    # Energy drawn from the grid
    energy_delivered_kwh = energy_stored_kwh / efficiency if efficiency > 0.0 else 0.0
    power_kw_drawn = energy_delivered_kwh / step_hours if step_hours > 0.0 else 0.0

    # Conservation invariant check
    max_possible_grid_kwh = charger_kw * step_hours
    if energy_delivered_kwh > max_possible_grid_kwh + 1e-6:
        energy_delivered_kwh = max_possible_grid_kwh
        energy_stored_kwh = energy_delivered_kwh * efficiency
        power_kw_drawn = charger_kw

    new_soc = min(1.0, max(0.0, soc + (energy_stored_kwh / battery_kwh)))
    return new_soc, power_kw_drawn, energy_delivered_kwh


def discharge_step(
    soc: float,
    battery_kwh: float,
    distance_km: float,
    base_wh_km: float = 160.0,
    traffic_factor: float = 1.0,
    driver_factor: float = 1.0,
    hvac_kw: float = 0.0,
    avg_speed_kmh: float = 35.0,
) -> Tuple[float, float]:
    """Simulate battery discharge during a driving trip.

    Args:
        soc: Current battery state of charge [0.0, 1.0].
        battery_kwh: Total battery pack capacity in kWh.
        distance_km: Distance driven in km during this step.
        base_wh_km: Vehicle base rated consumption Wh/km.
        traffic_factor: Multiplier for stop-and-go congestion.
        driver_factor: Multiplier for driving aggressiveness.
        hvac_kw: HVAC power consumption in kW.
        avg_speed_kmh: Average speed in km/h.

    Returns:
        Tuple of (new_soc, energy_used_kwh).
    """
    if distance_km <= 0.0:
        return soc, 0.0

    effective_speed = max(10.0, avg_speed_kmh)
    hvac_wh_km = (hvac_kw * 1000.0) / effective_speed
    total_wh_km = (base_wh_km * traffic_factor * driver_factor) + hvac_wh_km

    energy_used_kwh = (total_wh_km * distance_km) / 1000.0
    soc_drop = energy_used_kwh / battery_kwh if battery_kwh > 0.0 else 0.0

    new_soc = max(0.0, soc - soc_drop)
    return new_soc, energy_used_kwh


def compute_relative_stress_score(
    soc: float,
    power_kw: float,
    battery_kwh: float,
    temp_c: float = 30.0,
) -> float:
    """Compute normalized relative battery stress score [0.0, 1.0].

    Considers:
    - High SOC exposure (> 80%)
    - C-rate (power / battery_kwh)
    - High thermal exposure (> 35 °C)
    - Deep depth of discharge (SOC < 15%)
    """
    c_rate = (power_kw / battery_kwh) if battery_kwh > 0.0 else 0.0

    # High SOC penalty
    high_soc_penalty = max(0.0, (soc - 0.80) / 0.20) * 0.35

    # C-rate stress (fast charging accelerates degradation)
    c_rate_penalty = min(1.0, c_rate / 2.0) * 0.30

    # Temperature stress
    temp_penalty = max(0.0, (temp_c - 30.0) / 20.0) * 0.25

    # Low SOC / deep discharge stress
    low_soc_penalty = max(0.0, (0.15 - soc) / 0.15) * 0.10

    total_score = high_soc_penalty + c_rate_penalty + temp_penalty + low_soc_penalty
    return float(min(1.0, max(0.0, total_score)))
