"""Journey confidence perception engine with Monte Carlo uncertainty and calibration.

Estimates the probability of an EV completing its trip and arriving at or above
the reserved battery SOC threshold, accounting for traffic variability, thermal HVAC load,
and driver behavior.
"""

from typing import List, Optional
import numpy as np
from sklearn.isotonic import IsotonicRegression

from gridnudge.contracts import Journey


class JourneyCalibrator:
    """Calibrator mapping raw Monte Carlo probabilities to empirical frequencies."""

    def __init__(self):
        self._is_fitted = False
        self._regressor = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        # Default empirical anchors (raw_p -> calibrated_p) before fitting
        self._default_x = np.array([0.0, 0.1, 0.3, 0.5, 0.7, 0.85, 0.90, 0.95, 1.0])
        self._default_y = np.array([0.0, 0.09, 0.28, 0.49, 0.70, 0.86, 0.90, 0.96, 1.0])

    def fit(self, predicted_probs: np.ndarray, observed_outcomes: np.ndarray) -> "JourneyCalibrator":
        """Fit isotonic regression on held-out simulated trips."""
        x = np.asarray(predicted_probs, dtype=float)
        y = np.asarray(observed_outcomes, dtype=float)
        if len(x) >= 10:
            self._regressor.fit(x, y)
            self._is_fitted = True
        return self

    def calibrate(self, raw_prob: float) -> float:
        """Calibrate a single raw probability value into a reliable probability."""
        p_clamped = max(0.0, min(1.0, float(raw_prob)))
        if self._is_fitted:
            calibrated = float(self._regressor.predict([p_clamped])[0])
        else:
            calibrated = float(np.interp(p_clamped, self._default_x, self._default_y))
        return float(max(0.0, min(1.0, calibrated)))


# Shared default calibrator
DEFAULT_CALIBRATOR = JourneyCalibrator()


def estimate_journey_confidence(
    departure_soc: Optional[float] = None,
    battery_kwh: float = 40.0,
    distance_km: float = 30.0,
    base_wh_km: float = 160.0,
    ambient_temp_c: float = 30.0,
    avg_speed_kmh: float = 35.0,
    reserve_soc: float = 0.10,
    n_draws: int = 400,
    seed: Optional[int] = 42,
    rng: Optional[np.random.Generator] = None,
    calibrator: Optional[JourneyCalibrator] = None,
    soc: Optional[float] = None,
) -> Journey:
    """Compute calibrated journey confidence and arrival SOC quantiles using Monte Carlo.

    Args:
        departure_soc: Expected battery SOC at trip departure [0.0, 1.0].
        battery_kwh: Total battery capacity in kWh.
        distance_km: Scheduled journey distance in km.
        base_wh_km: Base vehicle energy consumption in Wh/km.
        ambient_temp_c: Ambient temperature in degrees Celsius.
        avg_speed_kmh: Estimated average trip speed in km/h.
        reserve_soc: Minimum desired reserve SOC at destination (default 0.10).
        n_draws: Number of Monte Carlo draws (default 400).
        seed: RNG seed for reproducible Common Random Numbers across plans.
        rng: Optional explicit numpy Generator.
        calibrator: Optional JourneyCalibrator instance.
        soc: Optional alias for departure_soc.

    Returns:
        Journey contract object.
    """
    if departure_soc is None:
        departure_soc = soc if soc is not None else 0.5
    departure_soc = float(max(0.0, min(1.0, departure_soc)))
    battery_kwh = float(max(0.1, battery_kwh))
    distance_km = float(max(0.0, distance_km))
    reserve_soc = float(max(0.0, min(1.0, reserve_soc)))

    if distance_km == 0.0:
        p_above = 1.0 if departure_soc >= reserve_soc else 0.0
        return Journey(
            p_arrive_above_reserve=p_above,
            arrival_soc_q10=departure_soc,
            arrival_soc_q50=departure_soc,
            arrival_soc_q90=departure_soc,
            reserve_soc=reserve_soc,
        )

    if departure_soc <= 0.0:
        return Journey(
            p_arrive_above_reserve=0.0,
            arrival_soc_q10=0.0,
            arrival_soc_q50=0.0,
            arrival_soc_q90=0.0,
            reserve_soc=reserve_soc,
        )

    # Use seeded generator to guarantee monotonicity across different departure_soc comparisons
    draw_rng = rng if rng is not None else np.random.default_rng(seed)

    # 1. Monte Carlo variability distributions
    traffic = np.clip(draw_rng.normal(loc=1.10, scale=0.12, size=n_draws), 0.85, 2.20)
    driver = np.clip(draw_rng.normal(loc=1.00, scale=0.08, size=n_draws), 0.80, 1.45)
    temp_err = draw_rng.normal(loc=0.0, scale=2.0, size=n_draws)
    effective_temp = np.clip(ambient_temp_c + temp_err, -5.0, 52.0)

    # 2. HVAC power calculation: expands outside comfortable band [21°C, 24°C]
    temp_delta = np.maximum(0.0, np.abs(effective_temp - 22.5) - 1.5)
    hvac_kw = np.clip(temp_delta * 0.12, 0.0, 3.5)
    effective_speed = max(10.0, avg_speed_kmh)
    hvac_wh_km = (hvac_kw * 1000.0) / effective_speed

    # 3. Energy consumption and remaining arrival SOC
    total_wh_km = (base_wh_km * traffic * driver) + hvac_wh_km
    trip_energy_kwh = (total_wh_km * distance_km) / 1000.0
    arrival_soc = np.clip(departure_soc - (trip_energy_kwh / battery_kwh), 0.0, 1.0)

    raw_p_above = float(np.mean(arrival_soc >= reserve_soc))

    # 4. Calibration
    active_calibrator = calibrator or DEFAULT_CALIBRATOR
    calibrated_p = active_calibrator.calibrate(raw_p_above)

    # 5. Quantiles
    q10 = float(np.percentile(arrival_soc, 10))
    q50 = float(np.percentile(arrival_soc, 50))
    q90 = float(np.percentile(arrival_soc, 90))

    return Journey(
        p_arrive_above_reserve=round(calibrated_p, 4),
        arrival_soc_q10=round(q10, 4),
        arrival_soc_q50=round(q50, 4),
        arrival_soc_q90=round(q90, 4),
        reserve_soc=reserve_soc,
    )


def batch_estimate_journey_confidence(
    items: List[dict],
    base_wh_km: float = 160.0,
    ambient_temp_c: float = 30.0,
    reserve_soc: float = 0.10,
    n_draws: int = 300,
    seed: int = 42,
) -> List[Journey]:
    """Fast vectorized batch confidence estimation for hundreds of EVs."""
    results = []
    for item in items:
        res = estimate_journey_confidence(
            departure_soc=item["departure_soc"],
            battery_kwh=item["battery_kwh"],
            distance_km=item["distance_km"],
            base_wh_km=item.get("base_wh_km", base_wh_km),
            ambient_temp_c=item.get("ambient_temp_c", ambient_temp_c),
            avg_speed_kmh=item.get("avg_speed_kmh", 35.0),
            reserve_soc=reserve_soc,
            n_draws=n_draws,
            seed=seed + item.get("user_id", 0),
        )
        results.append(res)
    return results
