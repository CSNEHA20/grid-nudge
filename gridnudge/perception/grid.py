"""Grid stress and green charging window perception engine.

Produces probabilistic quantiles of distribution feeder stress (load / capacity)
and identifies optimal renewable/solar green charging windows.
"""

from typing import Tuple
import numpy as np

from gridnudge.contracts import GridView


def compute_diurnal_grid_stress_profile(
    current_hour: float,
    current_feeder_load_mw: float,
    feeder_capacity_mw: float = 12.0,
    base_peak_mw: float = 8.5,
    base_offpeak_mw: float = 4.2,
    horizon_hours: int = 24,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute forecasted stress quantiles (q50, q90) over upcoming horizon hours.

    Uses seasonal diurnal profile scaled to observed current telemetry.
    """
    capacity = max(1.0, float(feeder_capacity_mw))
    hours = np.array([(current_hour + h) % 24.0 for h in range(horizon_hours)])

    # Normalized diurnal curve (evening peak ~ 20:30, overnight dip ~ 04:30)
    t_rad = (hours / 24.0) * 2.0 * np.pi
    h1 = -np.cos(t_rad - 0.5)
    h2 = 0.35 * -np.cos(2.0 * t_rad - 1.2)
    h3 = 0.15 * -np.cos(3.0 * t_rad)
    normalized = np.clip((h1 + h2 + h3 + 1.2) / 2.4, 0.0, 1.0)

    forecast_base = base_offpeak_mw + normalized * (base_peak_mw - base_offpeak_mw)

    # Scale to match current observation
    current_t_rad = (current_hour / 24.0) * 2.0 * np.pi
    curr_norm = max(0.01, float((-np.cos(current_t_rad - 0.5) + 1.2) / 2.4))
    curr_expected = base_offpeak_mw + curr_norm * (base_peak_mw - base_offpeak_mw)
    scale_factor = np.clip(current_feeder_load_mw / max(1.0, curr_expected), 0.75, 1.40)

    q50_loads = forecast_base * scale_factor
    # q90 incorporates peak volatility and potential EV stacking (+15%)
    q90_loads = q50_loads * 1.15

    stress_q50_curve = q50_loads / capacity
    stress_q90_curve = q90_loads / capacity

    return stress_q50_curve, stress_q90_curve


def identify_green_charging_window(
    solar_peak_hour: float = 13.0,
    start_threshold_hour: float = 10.5,
    end_threshold_hour: float = 15.5,
) -> Tuple[str, str]:
    """Identify diurnal solar generation green window start and end clock times."""
    start_h = int(start_threshold_hour)
    start_m = int((start_threshold_hour - start_h) * 60)
    end_h = int(end_threshold_hour)
    end_m = int((end_threshold_hour - end_h) * 60)

    start_str = f"{start_h:02d}:{start_m:02d}"
    end_str = f"{end_h:02d}:{end_m:02d}"
    return start_str, end_str


def evaluate_grid_view(
    feeder_load_mw: float,
    feeder_capacity_mw: float = 12.0,
    hour_of_day: float = 18.0,
    base_peak_mw: float = 8.5,
    base_offpeak_mw: float = 4.2,
    horizon_hours: int = 12,
) -> GridView:
    """Evaluate grid state and forecast stress quantiles and green window.

    Args:
        feeder_load_mw: Current observed feeder load in MW.
        feeder_capacity_mw: Maximum safe feeder transformer capacity in MW.
        hour_of_day: Current time of day (0.0 to 23.99).
        base_peak_mw: Normal diurnal base peak load in MW.
        base_offpeak_mw: Normal diurnal off-peak load in MW.
        horizon_hours: Forecasting lookahead horizon in hours.

    Returns:
        GridView contract object.
    """
    capacity = max(1.0, float(feeder_capacity_mw))
    current_stress = float(feeder_load_mw) / capacity

    q50_curve, q90_curve = compute_diurnal_grid_stress_profile(
        current_hour=hour_of_day,
        current_feeder_load_mw=feeder_load_mw,
        feeder_capacity_mw=capacity,
        base_peak_mw=base_peak_mw,
        base_offpeak_mw=base_offpeak_mw,
        horizon_hours=horizon_hours,
    )

    # Summary quantiles across the lookahead window
    stress_q50 = float(np.median(q50_curve))
    stress_q90 = float(np.max(q90_curve))

    # Weight immediate current stress into q50 for recency
    stress_q50 = round(float(0.4 * current_stress + 0.6 * stress_q50), 4)
    stress_q90 = round(float(max(current_stress, stress_q90)), 4)

    green_start, green_end = identify_green_charging_window()

    return GridView(
        stress_q50=stress_q50,
        stress_q90=stress_q90,
        green_window_start=green_start,
        green_window_end=green_end,
    )
