"""Unit and integration tests for GridNudge evaluation harness (M11)."""

import json
from pathlib import Path
import pytest

from eval.baselines import (
    create_policy_b3,
    create_policy_b4,
    get_policy_by_name,
    policy_b0,
    policy_b1,
    policy_b2,
)
from eval.calibration import compute_calibration_curve, evaluate_synthetic_calibration
from eval.make_replay import generate_replay_timeline
from eval.metrics import (
    aggregate_policy_runs,
    compute_confidence_intervals,
    compute_run_metrics,
)
from eval.plots import (
    plot_calibration_reliability,
    plot_fleet_load_comparison,
    plot_peak_reduction_bars,
)
from eval.run import run_benchmark
from eval.stress import run_misspecification_test, run_non_stationarity_test
from twin.runner import run_simulation
from twin.world import World


class TestBaselines:
    def test_policy_b0_returns_empty(self):
        w = World(seed=42, n_users=50)
        assert policy_b0(w) == []

    def test_policy_b1_nudges_at_peak(self):
        w = World(seed=42, n_users=200)
        # Advance world to peak window (step 72 = 18:00)
        w.current_step = 72
        # Ensure at least some users are plugged
        for u in w.fleet.users[:10]:
            u.plugged = True
        decisions = policy_b1(w)
        assert len(decisions) > 0
        for d in decisions:
            assert d["plan"]["type"] == "delay"
            assert d["frame"] == "cost"

    def test_policy_b2_filters_low_soc(self):
        w = World(seed=42, n_users=200)
        w.current_step = 72
        # Set one user with low SOC (< 0.25) and one with high SOC (0.7)
        u_low = w.fleet.users[0]
        u_low.plugged = True
        u_low.soc = 0.18

        u_high = w.fleet.users[1]
        u_high.plugged = True
        u_high.soc = 0.75

        decisions = policy_b2(w)
        user_ids = [d["user_id"] for d in decisions]
        assert u_high.user_id in user_ids
        assert u_low.user_id not in user_ids

    def test_policy_b3_and_b4_execution(self):
        w = World(seed=42, n_users=100)
        pol_b3 = create_policy_b3(seed=42)
        res_b3 = run_simulation(world=w, n_steps=8, policy_fn=pol_b3)
        assert res_b3["metrics"]["steps_simulated"] == 8

        w4 = World(seed=42, n_users=100)
        pol_b4 = create_policy_b4(seed=42)
        res_b4 = run_simulation(world=w4, n_steps=8, policy_fn=pol_b4)
        assert res_b4["metrics"]["steps_simulated"] == 8

    def test_crn_reproducibility(self):
        """Identical seed must yield identical trajectories across runs."""
        w1 = World(seed=999, n_users=150)
        r1 = run_simulation(world=w1, n_steps=20, policy_fn=policy_b0)

        w2 = World(seed=999, n_users=150)
        r2 = run_simulation(world=w2, n_steps=20, policy_fn=policy_b0)

        loads1 = [t["feeder_load_mw"] for t in r1["timeline"]]
        loads2 = [t["feeder_load_mw"] for t in r2["timeline"]]
        assert loads1 == loads2

    def test_get_policy_by_name(self):
        for name in ["B0", "B1", "B2", "B3", "B4"]:
            pol = get_policy_by_name(name, seed=42)
            assert callable(pol)

        with pytest.raises(ValueError):
            get_policy_by_name("B99_UNKNOWN")


class TestMetrics:
    def test_compute_run_metrics(self):
        w0 = World(seed=42, n_users=200)
        res_b0 = run_simulation(world=w0, n_steps=24, policy_fn=policy_b0)

        w1 = World(seed=42, n_users=200)
        res_b1 = run_simulation(world=w1, n_steps=24, policy_fn=policy_b1)

        m = compute_run_metrics(res_b1, b0_run_output=res_b0, n_days=0.25)
        assert "overall_peak_mw" in m
        assert "evening_peak_mw" in m
        assert "stranded_trips_attributable" in m
        assert m["stranded_trips_attributable"] == 0

    def test_compute_confidence_intervals(self):
        data = [10.0, 12.0, 11.0, 13.0, 10.5]
        mean_val, ci_half, std_err = compute_confidence_intervals(data)
        assert 11.0 <= mean_val <= 11.5
        assert ci_half > 0.0
        assert std_err > 0.0

    def test_aggregate_policy_runs(self):
        w0 = World(seed=42, n_users=50)
        res0 = run_simulation(world=w0, n_steps=12, policy_fn=policy_b0)

        w4 = World(seed=42, n_users=50)
        pol4 = create_policy_b4(seed=42)
        res4 = run_simulation(world=w4, n_steps=12, policy_fn=pol4)

        agg = aggregate_policy_runs(
            runs_by_policy={"B0": [res0], "B4": [res4]},
            b0_runs=[res0],
        )
        assert "B0" in agg
        assert "B4" in agg
        assert "formatted" in agg["B4"]["evening_peak_reduction_pct"]


class TestCalibration:
    def test_calibration_curve_calculation(self):
        probs = [0.1, 0.2, 0.45, 0.5, 0.85, 0.9]
        actuals = [0, 0, 0, 1, 1, 1]
        res = compute_calibration_curve(probs, actuals, n_bins=5)
        assert res["held_out_trips_count"] == 6
        assert "expected_calibration_error" in res
        assert len(res["bins"]) == 5

    def test_synthetic_calibration(self):
        cal = evaluate_synthetic_calibration(n_trips=200, seed=42)
        assert cal["held_out_trips_count"] == 200
        assert cal["expected_calibration_error"] >= 0.0
        assert cal["interval_coverage_80"] > 0.5


class TestStressTests:
    def test_misspecification_test(self):
        res = run_misspecification_test(seed=42, n_users=80, n_steps=20)
        assert res["safety_maintained"] is True
        assert res["stranded_trips_attributable"] == 0
        assert res["status"] == "passed"

    def test_non_stationarity_test(self):
        res = run_non_stationarity_test(seed=42, n_users=80, n_steps=24)
        assert res["status"] == "passed"
        assert res["steps_simulated"] == 24


class TestReplayAndPlots:
    def test_generate_replay_timeline(self, tmp_path):
        out_file = tmp_path / "replay_timeline.json"
        res = generate_replay_timeline(
            seed=42,
            n_users=100,
            n_steps=16,
            scenario="heatwave",
            output_path=str(out_file),
        )
        assert out_file.exists()
        assert len(res["timesteps"]) == 16
        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "summary" in data

    def test_plot_generation(self, tmp_path):
        # 1. Fleet load
        timelines = {
            "B0_uncontrolled": [{"step": i, "feeder_load_mw": 5.0 + i * 0.1, "hour_of_day": i * 0.25} for i in range(24)],
            "B4_gridnudge": [{"step": i, "feeder_load_mw": 4.5 + i * 0.05, "hour_of_day": i * 0.25} for i in range(24)],
        }
        f1 = plot_fleet_load_comparison(timelines, str(tmp_path / "load.png"), max_steps=24)
        assert Path(f1).exists()

        # 2. Peak reduction bars
        summary = {
            "B0_uncontrolled": {"evening_peak_reduction_pct": {"mean": 0.0, "ci95": 0.0}},
            "B4_gridnudge": {"evening_peak_reduction_pct": {"mean": 14.5, "ci95": 1.2}},
        }
        f2 = plot_peak_reduction_bars(summary, str(tmp_path / "bars.png"))
        assert Path(f2).exists()

        # 3. Calibration
        calib_data = compute_calibration_curve([0.2, 0.8], [0, 1], n_bins=2)
        f3 = plot_calibration_reliability(calib_data, str(tmp_path / "calib.png"))
        assert Path(f3).exists()


class TestBenchmarkRunner:
    def test_run_benchmark_fast(self, tmp_path):
        """Run quick benchmark with 2 seeds and 3 policies."""
        res = run_benchmark(
            seeds=[42, 143],
            n_users=60,
            n_steps=12,
            scenario="heatwave",
            policies=["B0", "B1", "B4"],
            output_dir=str(tmp_path),
        )
        assert Path(res["summary_csv"]).exists()
        assert Path(res["timeline_json"]).exists()
        assert Path(res["replay_json"]).exists()
        assert "B0" in res["summary"]
        assert "B4" in res["summary"]
