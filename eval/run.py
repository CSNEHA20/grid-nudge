"""Command-line benchmark evaluation harness for GridNudge (M11).

Executes multi-seed runs under Common Random Numbers (CRN) across policies:
- B0: Uncontrolled default charging
- B1: Broadcast rule-based delay nudge
- B2: Safe rule-based planner (reserve SOC >= 25%)
- B3: Contextual bandit without allocator
- B4: Full GridNudge decision system (uplift-aware + anti-herding allocator + verifier)

Produces:
- `results/summary.csv`
- `results/timeline.json`
- `results/plots/*.png`
- `results/replay/timeline.json`
"""

import argparse
import csv
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List

from eval.baselines import get_policy_by_name
from eval.calibration import evaluate_synthetic_calibration
from eval.make_replay import generate_replay_timeline
from eval.metrics import aggregate_policy_runs
from eval.plots import (
    plot_calibration_reliability,
    plot_fleet_load_comparison,
    plot_peak_reduction_bars,
)
from twin.runner import run_simulation
from twin.world import World

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval.run")


def run_benchmark(
    seeds: List[int],
    n_users: int = 2000,
    n_steps: int = 96,
    scenario: str = "heatwave",
    policies: List[str] = ["B0", "B1", "B2", "B3", "B4"],
    output_dir: str = "results",
) -> Dict[str, Any]:
    """Execute CRN benchmark comparison across policies and seeds.
    
    Args:
        seeds: List of random seeds to evaluate.
        n_users: Fleet EV count.
        n_steps: Steps per run (96 = 1 day, 672 = 7 days).
        scenario: Environmental event ('normal', 'heatwave', 'solar_drop').
        policies: List of policy names ('B0', 'B1', 'B2', 'B3', 'B4').
        output_dir: Output artifacts directory.
        
    Returns:
        Summary evaluation results dict.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    plots_path = out_path / "plots"
    plots_path.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Starting GridNudge benchmark: %d seeds, %d users, %d steps, scenario '%s', policies %s",
        len(seeds),
        n_users,
        n_steps,
        scenario,
        policies,
    )

    runs_by_policy: Dict[str, List[Dict[str, Any]]] = {p: [] for p in policies}
    first_timelines: Dict[str, List[Dict[str, Any]]] = {}

    start_total = time.perf_counter()

    for s_idx, seed in enumerate(seeds):
        logger.info("--- Running Seed %d/%d (seed=%d) ---", s_idx + 1, len(seeds), seed)

        for pol_name in policies:
            # Instantiate clean world with identical seed (CRN)
            w = World(seed=seed, n_users=n_users)
            if scenario == "heatwave":
                w.inject({
                    "event_type": "heatwave",
                    "start_step": 64,
                    "end_step": 92,
                    "parameters": {"temp_c": 44.0, "multiplier": 1.25},
                })
            elif scenario == "solar_drop":
                w.inject({
                    "event_type": "solar_drop",
                    "start_step": 40,
                    "end_step": 70,
                    "parameters": {"drop_fraction": 0.6},
                })

            policy_callable = get_policy_by_name(pol_name, seed=seed)
            run_res = run_simulation(world=w, n_steps=n_steps, policy_fn=policy_callable)
            runs_by_policy[pol_name].append(run_res)

            if pol_name not in first_timelines:
                first_timelines[pol_name] = run_res["timeline"]

            logger.info(
                "Seed %d | %s -> Peak: %.2f MW, Shifted: %.1f kWh, Nudges: %d",
                seed,
                pol_name,
                run_res["metrics"]["peak_feeder_load_mw"],
                run_res["metrics"]["total_kwh_shifted"],
                run_res["metrics"]["total_nudges_sent"],
            )

    # Use B0 runs as baseline reference for peak reduction calculations
    b0_runs = runs_by_policy.get("B0")

    # 1. Compute multi-seed statistical aggregation
    summary_stats = aggregate_policy_runs(runs_by_policy, b0_runs=b0_runs)

    # 2. Export summary.csv
    csv_file = out_path / "summary.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "policy",
            "seeds",
            "evening_peak_mw",
            "overall_peak_mw",
            "evening_peak_reduction_pct",
            "total_kwh_shifted",
            "nudges_per_user_per_day",
            "opt_out_rate_pct",
            "mean_uplift_per_nudge",
            "stranded_trips",
            "mean_savings_inr",
            "regret_vs_oracle",
        ])
        for pol_name in policies:
            st = summary_stats.get(pol_name, {})
            writer.writerow([
                pol_name,
                len(seeds),
                st.get("evening_peak_mw", {}).get("formatted", "N/A"),
                st.get("overall_peak_mw", {}).get("formatted", "N/A"),
                st.get("evening_peak_reduction_pct", {}).get("formatted", "0.00 ± 0.00"),
                st.get("total_kwh_shifted", {}).get("formatted", "N/A"),
                st.get("nudges_per_user_per_day", {}).get("formatted", "N/A"),
                st.get("opt_out_rate_pct", {}).get("formatted", "N/A"),
                st.get("mean_uplift_per_nudge", {}).get("formatted", "N/A"),
                st.get("stranded_trips_attributable", {}).get("formatted", "0.00 ± 0.00"),
                st.get("mean_savings_per_adopting_user", {}).get("formatted", "N/A"),
                st.get("regret_vs_oracle", {}).get("formatted", "N/A"),
            ])
    logger.info("Wrote summary statistics to %s", csv_file)

    # 3. Export timeline.json for dashboard reference
    timeline_file = out_path / "timeline.json"
    timeline_payload = {
        "scenario": scenario,
        "seeds": seeds,
        "n_users": n_users,
        "policies": policies,
        "timelines": {k: t[:96] for k, t in first_timelines.items()},
    }
    with open(timeline_file, "w", encoding="utf-8") as f:
        json.dump(timeline_payload, f, indent=2)
    logger.info("Wrote reference timeline to %s", timeline_file)

    # 4. Generate Figures
    plot_fleet_load_comparison(
        first_timelines,
        output_path=str(plots_path / "fleet_load_comparison.png"),
        max_steps=min(n_steps, 96),
    )
    plot_peak_reduction_bars(
        summary_stats,
        output_path=str(plots_path / "peak_load_reduction_bars.png"),
    )

    # 5. Calibration plot & evaluation
    calib_data = evaluate_synthetic_calibration(n_trips=1500, seed=seeds[0])
    calib_json = out_path / "calibration.json"
    with open(calib_json, "w", encoding="utf-8") as f:
        json.dump(calib_data, f, indent=2)
    plot_calibration_reliability(
        calib_data,
        output_path=str(plots_path / "calibration_reliability.png"),
    )
    logger.info("Generated evaluation plots in %s", plots_path)

    # 6. Generate replay dataset
    replay_file = out_path / "replay" / "timeline.json"
    generate_replay_timeline(
        seed=seeds[0],
        n_users=n_users,
        n_steps=min(n_steps, 96),
        scenario=scenario,
        output_path=str(replay_file),
    )
    logger.info("Generated replay timeline in %s", replay_file)

    elapsed_total = time.perf_counter() - start_total
    logger.info("Benchmark complete in %.2f seconds.", elapsed_total)

    return {
        "summary": summary_stats,
        "summary_csv": str(csv_file),
        "timeline_json": str(timeline_file),
        "replay_json": str(replay_file),
        "elapsed_seconds": round(elapsed_total, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="GridNudge Multi-Seed Benchmark Evaluation Harness")
    parser.add_argument("--seeds", type=int, default=5, help="Number of random seeds (default: 5)")
    parser.add_argument("--users", type=int, default=2000, help="Synthetic fleet user count (default: 2000)")
    parser.add_argument("--days", type=int, default=1, help="Simulation duration in days (default: 1 day = 96 steps)")
    parser.add_argument("--steps", type=int, default=None, help="Explicit simulation steps override")
    parser.add_argument("--scenario", type=str, default="heatwave", choices=["normal", "heatwave", "solar_drop", "tariff_change"])
    parser.add_argument("--policies", nargs="+", default=["B0", "B1", "B2", "B3", "B4"], help="Policies to evaluate")
    parser.add_argument("--output_dir", type=str, default="results", help="Directory for output artifacts")
    parser.add_argument("--seed_start", type=int, default=42, help="Starting random seed value")

    args = parser.parse_args()

    n_steps = args.steps if args.steps is not None else args.days * 96
    seed_list = [args.seed_start + i * 101 for i in range(args.seeds)]

    run_benchmark(
        seeds=seed_list,
        n_users=args.users,
        n_steps=n_steps,
        scenario=args.scenario,
        policies=args.policies,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
