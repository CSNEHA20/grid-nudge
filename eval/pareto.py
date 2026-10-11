"""Pareto frontier evaluation harness for GridNudge (A5).

Sweeps nudge budget for B4 (GridNudge) and B3 (bandit without allocator),
and caps nudge volume for B1 (broadcast) and B2 (safe rule-based),
measuring evening peak reduction (%) versus nudges / user / day with 95% CI
under Common Random Numbers (CRN).

Outputs:
- `results/pareto.csv`
- `results/plots/pareto_frontier.png`
"""

import argparse
import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from eval.baselines import (
    create_policy_b1,
    create_policy_b2,
    create_policy_b3,
    create_policy_b4,
    policy_b0,
)
from eval.metrics import compute_confidence_intervals, compute_run_metrics
from twin.runner import run_simulation
from twin.world import World

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval.pareto")


def run_pareto_evaluation(
    seeds: List[int],
    n_users: int = 500,
    n_steps: int = 96,
    scenario: str = "heatwave",
    output_dir: str = "results",
) -> Dict[str, Any]:
    """Execute multi-seed Pareto sweeps across policies.

    Args:
        seeds: List of random seeds for CRN comparison.
        n_users: Fleet size.
        n_steps: Timesteps (96 = 1 day).
        scenario: Environmental stress event.
        output_dir: Output directory.

    Returns:
        Summary dict of Pareto points.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    plots_path = out_path / "plots"
    plots_path.mkdir(parents=True, exist_ok=True)

    # Define sweep points per policy
    configurations = [
        # B1 variants: broadcast with varying eligibility rate
        {"policy": "B1", "param": 0.25, "label": "B1 (cap 25%)", "factory": lambda s, p: create_policy_b1(max_rate=p)},
        {"policy": "B1", "param": 0.50, "label": "B1 (cap 50%)", "factory": lambda s, p: create_policy_b1(max_rate=p)},
        {"policy": "B1", "param": 0.75, "label": "B1 (cap 75%)", "factory": lambda s, p: create_policy_b1(max_rate=p)},
        {"policy": "B1", "param": 1.00, "label": "B1 (full broadcast)", "factory": lambda s, p: create_policy_b1(max_rate=p)},

        # B2 variants: rule-based with varying eligibility rate
        {"policy": "B2", "param": 0.25, "label": "B2 (cap 25%)", "factory": lambda s, p: create_policy_b2(max_rate=p)},
        {"policy": "B2", "param": 0.50, "label": "B2 (cap 50%)", "factory": lambda s, p: create_policy_b2(max_rate=p)},
        {"policy": "B2", "param": 0.75, "label": "B2 (cap 75%)", "factory": lambda s, p: create_policy_b2(max_rate=p)},
        {"policy": "B2", "param": 1.00, "label": "B2 (full rule-based)", "factory": lambda s, p: create_policy_b2(max_rate=p)},

        # B3 variants: bandit without allocator with varying sample rates
        {"policy": "B3", "param": 0.25, "label": "B3 (sample 25%)", "factory": lambda s, p: create_policy_b3(seed=s, sample_rate=p)},
        {"policy": "B3", "param": 0.50, "label": "B3 (sample 50%)", "factory": lambda s, p: create_policy_b3(seed=s, sample_rate=p)},
        {"policy": "B3", "param": 0.75, "label": "B3 (sample 75%)", "factory": lambda s, p: create_policy_b3(seed=s, sample_rate=p)},
        {"policy": "B3", "param": 1.00, "label": "B3 (full bandit)", "factory": lambda s, p: create_policy_b3(seed=s, sample_rate=p)},

        # B4 variants: full GridNudge with varying attention budget percentage
        {"policy": "B4", "param": 0.03, "label": "B4 (budget 3%)", "factory": lambda s, p: create_policy_b4(seed=s, budget_pct=p)},
        {"policy": "B4", "param": 0.05, "label": "B4 (budget 5%)", "factory": lambda s, p: create_policy_b4(seed=s, budget_pct=p)},
        {"policy": "B4", "param": 0.08, "label": "B4 (budget 8% nominal)", "factory": lambda s, p: create_policy_b4(seed=s, budget_pct=p)},
        {"policy": "B4", "param": 0.12, "label": "B4 (budget 12%)", "factory": lambda s, p: create_policy_b4(seed=s, budget_pct=p)},
        {"policy": "B4", "param": 0.18, "label": "B4 (budget 18%)", "factory": lambda s, p: create_policy_b4(seed=s, budget_pct=p)},
    ]

    logger.info("Executing Pareto evaluation across %d seeds and %d variants", len(seeds), len(configurations))

    # Pre-run B0 references per seed for exact CRN delta calculation
    b0_runs: Dict[int, Dict[str, Any]] = {}
    for s in seeds:
        w_b0 = World(seed=s, n_users=n_users)
        if scenario == "heatwave":
            w_b0.inject({
                "event_type": "heatwave",
                "start_step": 64,
                "end_step": 92,
                "parameters": {"temp_c": 44.0, "multiplier": 1.25},
            })
        b0_res = run_simulation(w_b0, n_steps=n_steps, policy_fn=policy_b0)
        b0_runs[s] = b0_res

    results_table: List[Dict[str, Any]] = []

    for cfg in configurations:
        p_name = cfg["policy"]
        param_val = cfg["param"]
        lbl = cfg["label"]
        factory = cfg["factory"]

        nudges_list: List[float] = []
        reduction_list: List[float] = []
        shifted_list: List[float] = []
        efficiency_list: List[float] = []

        for s in seeds:
            w = World(seed=s, n_users=n_users)
            if scenario == "heatwave":
                w.inject({
                    "event_type": "heatwave",
                    "start_step": 64,
                    "end_step": 92,
                    "parameters": {"temp_c": 44.0, "multiplier": 1.25},
                })

            pol = factory(s, param_val)
            run_res = run_simulation(w, n_steps=n_steps, policy_fn=pol)
            b0_ref = b0_runs[s]
            metrics = compute_run_metrics(run_res, b0_run_output=b0_ref)

            n_nudges_user_day = metrics["nudges_per_user_per_day"]
            peak_red_pct = metrics["evening_peak_reduction_pct"]
            shifted_kwh = metrics["total_kwh_shifted"]
            eff = shifted_kwh / max(1.0, run_res["metrics"]["total_nudges_sent"])

            nudges_list.append(n_nudges_user_day)
            reduction_list.append(peak_red_pct)
            shifted_list.append(shifted_kwh)
            efficiency_list.append(eff)

        n_mean, n_ci, _ = compute_confidence_intervals(nudges_list)
        r_mean, r_ci, _ = compute_confidence_intervals(reduction_list)
        s_mean, s_ci, _ = compute_confidence_intervals(shifted_list)
        e_mean, e_ci, _ = compute_confidence_intervals(efficiency_list)

        results_table.append({
            "policy": p_name,
            "variant": lbl,
            "param": param_val,
            "seeds": len(seeds),
            "nudges_per_user_per_day_mean": round(n_mean, 3),
            "nudges_per_user_per_day_ci95": round(n_ci, 3),
            "evening_peak_reduction_pct_mean": round(r_mean, 2),
            "evening_peak_reduction_pct_ci95": round(r_ci, 2),
            "kwh_shifted_mean": round(s_mean, 1),
            "kwh_shifted_ci95": round(s_ci, 1),
            "shifted_kwh_per_nudge_mean": round(e_mean, 2),
            "shifted_kwh_per_nudge_ci95": round(e_ci, 2),
        })

        logger.info(
            "%s: Nudges/u/d=%.2f ± %.2f, Peak Red=%.2f%% ± %.2f%%, Shifted/Nudge=%.2f kWh",
            lbl,
            n_mean,
            n_ci,
            r_mean,
            r_ci,
            e_mean,
        )

    # 1. Export results/pareto.csv
    csv_file = out_path / "pareto.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results_table[0].keys()))
        writer.writeheader()
        writer.writerows(results_table)
    logger.info("Wrote Pareto results to %s", csv_file)

    # 2. Generate Pareto Frontier Plot
    plot_file = plots_path / "pareto_frontier.png"
    fig, ax = plt.subplots(figsize=(10, 6), dpi=180)

    policy_styles = {
        "B1": {"color": "#ef5350", "marker": "s", "label": "B1: Broadcast Alert"},
        "B2": {"color": "#ffa726", "marker": "^", "label": "B2: Rule-Based Planner"},
        "B3": {"color": "#42a5f5", "marker": "v", "label": "B3: Bandit (No Allocator)"},
        "B4": {"color": "#2e7d32", "marker": "o", "label": "B4: GridNudge (Full System)"},
    }

    for p_code in ["B1", "B2", "B3", "B4"]:
        pts = [row for row in results_table if row["policy"] == p_code]
        pts.sort(key=lambda x: x["nudges_per_user_per_day_mean"])
        if not pts:
            continue

        xs = [p["nudges_per_user_per_day_mean"] for p in pts]
        ys = [p["evening_peak_reduction_pct_mean"] for p in pts]
        x_errs = [p["nudges_per_user_per_day_ci95"] for p in pts]
        y_errs = [p["evening_peak_reduction_pct_ci95"] for p in pts]

        st = policy_styles[p_code]
        ax.errorbar(
            xs,
            ys,
            xerr=x_errs,
            yerr=y_errs,
            fmt=st["marker"] + "-",
            color=st["color"],
            linewidth=2.0,
            capsize=4,
            markersize=7,
            label=st["label"],
            alpha=0.9,
        )

    ax.set_title(
        f"Pareto Frontier: Evening Peak Shaving vs. Nudge Fatigue ({scenario.title()} Scenario)",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Nudge Volume (nudges / user / day)", fontsize=11, fontweight="medium")
    ax.set_ylabel("Evening Peak Reduction (%)", fontsize=11, fontweight="medium")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, facecolor="#f8f9fa", edgecolor="#cfd8dc", fontsize=10)

    # Shade the low-fatigue attention budget target zone (<= 0.60 nudges/user/day)
    ax.axvspan(0.0, 0.60, color="#e8f5e9", alpha=0.35, label="Attention Budget Target (<= 0.60 nudges/user/day)")

    plt.tight_layout()
    fig.savefig(plot_file)
    plt.close(fig)
    logger.info("Saved Pareto frontier plot to %s", plot_file)

    return {
        "results_csv": str(csv_file),
        "plot_path": str(plot_file),
        "records": results_table,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="GridNudge Pareto Frontier Evaluation Harness")
    parser.add_argument("--seeds", nargs="+", type=int, default=[101, 102, 103], help="Random seeds list")
    parser.add_argument("--users", type=int, default=500, help="Fleet user count")
    parser.add_argument("--days", type=int, default=1, help="Simulation duration in days")
    parser.add_argument("--scenario", type=str, default="heatwave", choices=["normal", "heatwave", "solar_drop"])
    parser.add_argument("--output_dir", type=str, default="results")

    args = parser.parse_args()
    n_steps = args.days * 96

    run_pareto_evaluation(
        seeds=args.seeds,
        n_users=args.users,
        n_steps=n_steps,
        scenario=args.scenario,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
