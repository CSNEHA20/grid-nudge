"""Evaluation harness, baselines, metrics, and fixtures for GridNudge (M11)."""

from eval.baselines import (
    create_policy_b3,
    create_policy_b4,
    get_policy_by_name,
    policy_b0,
    policy_b1,
    policy_b2,
    run_baseline_comparison,
)
from eval.calibration import compute_calibration_curve, evaluate_synthetic_calibration
from eval.metrics import aggregate_policy_runs, compute_confidence_intervals, compute_run_metrics
from eval.stress import run_misspecification_test, run_non_stationarity_test

__all__ = [
    "policy_b0",
    "policy_b1",
    "policy_b2",
    "create_policy_b3",
    "create_policy_b4",
    "get_policy_by_name",
    "run_baseline_comparison",
    "compute_run_metrics",
    "compute_confidence_intervals",
    "aggregate_policy_runs",
    "compute_calibration_curve",
    "evaluate_synthetic_calibration",
    "run_misspecification_test",
    "run_non_stationarity_test",
]
