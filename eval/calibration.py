"""Calibration reliability and uncertainty evaluation for GridNudge (M11).

Evaluates whether predicted probabilities P(arrival SOC >= reserve) are well-calibrated
against empirical outcomes on held-out simulated trips.
Computes Expected Calibration Error (ECE), Maximum Calibration Error (MCE),
and prediction interval coverage.
"""

from typing import Any, Dict, List
import numpy as np


def compute_calibration_curve(
    predicted_probs: List[float],
    actual_outcomes: List[int],
    n_bins: int = 10,
) -> Dict[str, Any]:
    """Compute calibration reliability diagram metrics.
    
    Args:
        predicted_probs: Model predicted probabilities in [0.0, 1.0].
        actual_outcomes: Binary actual outcomes (1 = arrival SOC >= reserve, 0 = below).
        n_bins: Number of equal-width probability bins.
        
    Returns:
        Structured calibration dictionary matching dashboard format.
    """
    if len(predicted_probs) != len(actual_outcomes):
        raise ValueError("Lengths of predicted_probs and actual_outcomes must match.")

    p_arr = np.clip(np.array(predicted_probs, dtype=float), 0.0, 1.0)
    y_arr = np.array(actual_outcomes, dtype=int)
    n_total = len(p_arr)

    if n_total == 0:
        return {
            "metric": "Journey Confidence P(arrival SOC >= reserve)",
            "provenance": "Simulation",
            "held_out_trips_count": 0,
            "expected_calibration_error": 0.0,
            "max_calibration_error": 0.0,
            "bins": [],
        }

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    bins_data: List[Dict[str, Any]] = []

    ece = 0.0
    mce = 0.0

    for i in range(n_bins):
        b_start = float(bin_boundaries[i])
        b_end = float(bin_boundaries[i + 1])

        if i == n_bins - 1:
            in_bin = (p_arr >= b_start) & (p_arr <= b_end)
        else:
            in_bin = (p_arr >= b_start) & (p_arr < b_end)

        bin_count = int(np.sum(in_bin))
        if bin_count > 0:
            mean_pred = float(np.mean(p_arr[in_bin]))
            obs_freq = float(np.mean(y_arr[in_bin]))
            diff = abs(obs_freq - mean_pred)
            ece += (bin_count / n_total) * diff
            mce = max(mce, diff)
        else:
            mean_pred = (b_start + b_end) / 2.0
            obs_freq = mean_pred  # Neutral unpopulated bin

        bins_data.append({
            "bin_start": round(b_start, 2),
            "bin_end": round(b_end, 2),
            "mean_predicted": round(mean_pred, 3),
            "observed_freq": round(obs_freq, 3),
            "count": bin_count,
        })

    return {
        "metric": "Journey Confidence P(arrival SOC >= reserve)",
        "provenance": "Simulation",
        "held_out_trips_count": n_total,
        "expected_calibration_error": round(float(ece), 4),
        "max_calibration_error": round(float(mce), 4),
        "bins": bins_data,
    }


def evaluate_synthetic_calibration(
    n_trips: int = 2000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Generate held-out simulated trips and evaluate perception journey model calibration.
    
    Uses a split-conformal calibration set (development seed >= 100) to calibrate prediction
    probabilities and quantile interval widths, then evaluates true coverage and ECE on
    the held-out evaluation sample.
    """
    from gridnudge.perception.journey import JourneyCalibrator, estimate_journey_confidence
    from twin.battery_truth import discharge_step

    # 1. Fit isotonic calibrator and conformal quantile width on independent calibration split
    calib_rng = np.random.default_rng(seed + 1000)
    n_calib = 500
    calib_preds = []
    calib_actuals = []
    nonconformity_scores = []
    calibrator = JourneyCalibrator()

    for _ in range(n_calib):
        batt = float(calib_rng.choice([30.0, 40.0, 60.0]))
        soc_val = float(calib_rng.uniform(0.3, 0.9))
        dist = float(calib_rng.uniform(15.0, 75.0))
        tf = float(calib_rng.uniform(0.9, 1.4))
        temp = float(calib_rng.uniform(22.0, 42.0))
        hvac = 1.5 if temp > 35 else 0.5

        jp = estimate_journey_confidence(
            departure_soc=soc_val,
            battery_kwh=batt,
            distance_km=dist,
            ambient_temp_c=temp,
            reserve_soc=0.15,
        )
        act_tf = tf * float(calib_rng.normal(1.0, 0.08))
        act_hvac = hvac * float(calib_rng.uniform(0.9, 1.15))
        act_soc, _ = discharge_step(
            soc=soc_val,
            battery_kwh=batt,
            distance_km=dist,
            base_wh_km=140.0,
            traffic_factor=act_tf,
            hvac_kw=act_hvac,
        )

        calib_preds.append(jp.p_arrive_above_reserve)
        calib_actuals.append(1 if act_soc >= 0.15 else 0)
        # Nonconformity score for 80% coverage interval [q10, q90]
        s = max(jp.arrival_soc_q10 - act_soc, act_soc - jp.arrival_soc_q90)
        nonconformity_scores.append(s)

    calibrator.fit(np.array(calib_preds), np.array(calib_actuals))
    # 80% conformal quantile adjustment with finite sample correction (1 - alpha)(1 + 1/n)
    alpha = 0.20
    q_level = min(1.0, (1.0 - alpha) * (1.0 + 1.0 / n_calib))
    q_hat = float(np.quantile(nonconformity_scores, q_level))

    # 2. Evaluate on held-out test trips
    rng = np.random.default_rng(seed)
    predicted_probs: List[float] = []
    actual_outcomes: List[int] = []
    interval_hits = 0

    for _ in range(n_trips):
        battery_kwh = float(rng.choice([30.0, 40.0, 60.0]))
        current_soc = float(rng.uniform(0.3, 0.9))
        distance_km = float(rng.uniform(15.0, 75.0))
        traffic_factor = float(rng.uniform(0.9, 1.4))
        temp_c = float(rng.uniform(22.0, 42.0))
        hvac_kw = 1.5 if temp_c > 35 else 0.5

        journey_pred = estimate_journey_confidence(
            departure_soc=current_soc,
            battery_kwh=battery_kwh,
            distance_km=distance_km,
            ambient_temp_c=temp_c,
            reserve_soc=0.15,
            calibrator=calibrator,
        )
        p_conf = journey_pred.p_arrive_above_reserve
        q10 = journey_pred.arrival_soc_q10 - q_hat
        q90 = journey_pred.arrival_soc_q90 + q_hat

        actual_traffic = traffic_factor * float(rng.normal(1.0, 0.08))
        actual_hvac = hvac_kw * float(rng.uniform(0.9, 1.15))
        actual_soc, _ = discharge_step(
            soc=current_soc,
            battery_kwh=battery_kwh,
            distance_km=distance_km,
            base_wh_km=140.0,
            traffic_factor=actual_traffic,
            hvac_kw=actual_hvac,
        )

        is_success = 1 if actual_soc >= 0.15 else 0
        predicted_probs.append(p_conf)
        actual_outcomes.append(is_success)

        if q10 <= actual_soc <= q90:
            interval_hits += 1

    calib_result = compute_calibration_curve(predicted_probs, actual_outcomes, n_bins=10)
    calib_result["interval_coverage_80"] = round(interval_hits / max(1, n_trips), 3)
    calib_result["conformal_quantile_adjustment"] = round(q_hat, 4)
    return calib_result
