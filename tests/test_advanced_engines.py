"""Tests for C11 Advanced Engines: Digital Test Drive and Doubly-Robust OPE."""

from eval.ope import doubly_robust_evaluation, inverse_propensity_scoring
from gridnudge.perception.grid import forecast_feeder_load
from gridnudge.testdrive import run_digital_test_drive
import numpy as np


def test_digital_test_drive_suitability_and_confidence():
    """Test Drive engine generates comprehensive 52-week ownership evaluation."""
    # Strong fit case (home charging + moderate commute)
    res_fit = run_digital_test_drive(
        daily_commute_km=30.0,
        weekend_trip_km=100.0,
        home_charging_access=True,
    )
    assert res_fit["outputs"]["ownership_confidence_pct"] >= 80.0
    assert res_fit["outputs"]["suitability_verdict"] == "STRONG_FIT"
    assert res_fit["outputs"]["annual_savings_inr"] > 0
    assert len(res_fit["outputs"]["weekly_risk_timeline"]) == 52

    # Negative case (high commute + no home charging = significant friction)
    res_unfit = run_digital_test_drive(
        daily_commute_km=90.0,
        weekend_trip_km=300.0,
        home_charging_access=False,
    )
    assert res_unfit["outputs"]["suitability_verdict"] in ("BORDERLINE", "NOT_RECOMMENDED")
    assert res_unfit["outputs"]["weeks_at_risk_out_of_52"] > 0


def test_off_policy_evaluation_ips_and_dr():
    """Off-policy evaluation produces consistent estimators on synthetic bandit log."""
    logged = [
        {"action": "delay", "propensity": 0.25, "realized_value": 2.5},
        {"action": "delay", "propensity": 0.25, "realized_value": 2.0},
        {"action": "none", "propensity": 0.50, "realized_value": 0.0},
        {"action": "slow_charge", "propensity": 0.25, "realized_value": 1.0},
    ]

    def target_policy(item):
        return "delay"

    def direct_model(item, act):
        return 2.2 if act == "delay" else 0.5

    ips_val, ips_low, ips_high = inverse_propensity_scoring(logged, target_policy)
    assert ips_val > 0.0
    assert ips_low <= ips_val <= ips_high

    dr_val, dr_low, dr_high = doubly_robust_evaluation(logged, target_policy, direct_model)
    assert dr_val > 0.0
    assert dr_low <= dr_val <= dr_high


def test_forecast_feeder_load_chronos_and_naive():
    """Grid forecast supports seasonal naive and zero-shot quantile models."""
    history = np.random.uniform(5.0, 10.0, size=48)
    naive = forecast_feeder_load(history, horizon_hours=24, forecaster="seasonal_naive")
    assert naive["forecaster"] == "seasonal_naive"
    assert len(naive["q50"]) == 24

    chronos = forecast_feeder_load(history, horizon_hours=24, forecaster="chronos")
    assert chronos["forecaster"] == "chronos"
    assert len(chronos["q90"]) == 24
    assert chronos["peak_expected_mw"] > 0.0
