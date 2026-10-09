"""Plotting utilities for GridNudge benchmark evaluation (M11).

Generates high-contrast, publication-quality figures:
- Fleet load curves with evening peak shading (B0 vs B1 vs B4)
- Peak reduction bar charts with 95% confidence interval whiskers
- Calibration reliability diagram (ECE + diagonal line)
- Cumulative regret curves over simulation steps
"""

from pathlib import Path
from typing import Any, Dict, List
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_fleet_load_comparison(
    timelines_by_policy: Dict[str, List[Dict[str, Any]]],
    output_path: str,
    title: str = "Fleet Feeder Load Comparison (Simulation)",
    max_steps: int = 192,  # 2 days default for clear visual resolution
) -> str:
    """Plot timeline feeder load comparing baseline and GridNudge policies."""
    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)

    # Shading for evening peak window (18:00 - 22:00, steps 72-88 each day)
    for day in range(max_steps // 96 + 1):
        peak_start = day * 96 + 72
        peak_end = day * 96 + 88
        if peak_start < max_steps:
            ax.axvspan(
                peak_start,
                min(peak_end, max_steps),
                color="#ffebee",
                alpha=0.6,
                label="Peak Window (18:00 - 22:00)" if day == 0 else "",
            )

    colors = {
        "B0_uncontrolled": "#d32f2f",      # Red
        "B1_rule_based": "#f57c00",         # Orange
        "B2_safe_planner": "#1976d2",       # Blue
        "B3_bandit_no_alloc": "#7b1fa2",    # Purple
        "B4_gridnudge": "#2e7d32",          # Green
    }

    labels = {
        "B0_uncontrolled": "B0: Uncontrolled Default",
        "B1_rule_based": "B1: Rule-Based Delay",
        "B2_safe_planner": "B2: Safe Planner",
        "B3_bandit_no_alloc": "B3: Bandit (No Allocator)",
        "B4_gridnudge": "B4: GridNudge (Full Uplift + Staggered)",
    }

    for pol_key, timeline in timelines_by_policy.items():
        steps = [t["step"] for t in timeline[:max_steps]]
        loads = [t["feeder_load_mw"] for t in timeline[:max_steps]]
        c = colors.get(pol_key, "#455a64")
        lbl = labels.get(pol_key, pol_key)
        lw = 2.4 if "gridnudge" in pol_key.lower() or "b4" in pol_key.lower() else 1.6
        ax.plot(steps, loads, label=lbl, color=c, linewidth=lw)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Simulation Step (15-min intervals)", fontsize=11)
    ax.set_ylabel("Feeder Load (MW)", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_file)
    plt.close(fig)
    return str(out_file)


def plot_peak_reduction_bars(
    aggregated_summary: Dict[str, Dict[str, Any]],
    output_path: str,
    title: str = "Evening Peak Load Reduction vs B0 (Simulation, Mean ± 95% CI)",
) -> str:
    """Plot bar chart of peak reduction percentage with 95% CI whiskers."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)

    policies = []
    means = []
    cis = []

    display_names = {
        "B0_uncontrolled": "B0: Uncontrolled",
        "B1_rule_based": "B1: Broadcast Delay",
        "B2_safe_planner": "B2: Safe Planner",
        "B3_bandit_no_alloc": "B3: Bandit (No Alloc)",
        "B4_gridnudge": "B4: GridNudge",
    }
    palette = ["#9e9e9e", "#ff9800", "#2196f3", "#9c27b0", "#4caf50"]

    idx = 0
    bar_colors = []
    for pol_key, stats in aggregated_summary.items():
        pol_display = display_names.get(pol_key, pol_key)
        metric_data = stats.get("evening_peak_reduction_pct", {})
        mean_val = float(metric_data.get("mean", 0.0))
        ci_val = float(metric_data.get("ci95", 0.0))

        policies.append(pol_display)
        means.append(mean_val)
        cis.append(ci_val)
        bar_colors.append(palette[idx % len(palette)])
        idx += 1

    x_pos = np.arange(len(policies))
    bars = ax.bar(
        x_pos,
        means,
        yerr=cis,
        capsize=6,
        color=bar_colors,
        edgecolor="#333333",
        linewidth=1.2,
        alpha=0.88,
    )

    # Value annotations on top of bars
    for bar, m, ci in zip(bars, means, cis):
        y_val = bar.get_height()
        ax.annotate(
            f"{m:.1f}%\n±{ci:.1f}",
            xy=(bar.get_x() + bar.get_width() / 2, y_val),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(policies, rotation=15, ha="right", fontsize=9)
    ax.set_ylabel("Peak Reduction (%)", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_file)
    plt.close(fig)
    return str(out_file)


def plot_calibration_reliability(
    calibration_data: Dict[str, Any],
    output_path: str,
    title: str = "Journey Confidence Calibration Reliability Diagram (Simulation)",
) -> str:
    """Plot calibration reliability diagram with ECE and ideal diagonal."""
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(7, 7), dpi=150, gridspec_kw={"height_ratios": [3, 1]}
    )

    bins = calibration_data.get("bins", [])
    ece = calibration_data.get("expected_calibration_error", 0.0)
    cov = calibration_data.get("interval_coverage_80")

    pred_means = [b["mean_predicted"] for b in bins]
    obs_freqs = [b["observed_freq"] for b in bins]
    counts = [b["count"] for b in bins]

    # Upper panel: Reliability Curve
    ax1.plot([0, 1], [0, 1], "k--", label="Perfect Calibration", linewidth=1.5)
    ax1.plot(pred_means, obs_freqs, "s-", color="#1976d2", label=f"GridNudge (ECE = {ece:.3f})", linewidth=2.0, markersize=6)
    subtitle = f"ECE: {ece:.3f}"
    if cov is not None:
        subtitle += f" | 80% Coverage: {cov * 100:.1f}%"
    ax1.set_title(f"{title}\n{subtitle}", fontsize=11, fontweight="bold", pad=10)
    ax1.set_ylabel("Observed Frequency P(arrive >= reserve)", fontsize=10)
    ax1.set_xlim([0.0, 1.0])
    ax1.set_ylim([0.0, 1.0])
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", fontsize=9)

    # Lower panel: Bin Sample Counts Histogram
    bin_centers = [(b["bin_start"] + b["bin_end"]) / 2.0 for b in bins]
    widths = [b["bin_end"] - b["bin_start"] for b in bins]
    ax2.bar(bin_centers, counts, width=widths, color="#90caf9", edgecolor="#1565c0", alpha=0.8)
    ax2.set_xlabel("Mean Predicted Journey Confidence", fontsize=10)
    ax2.set_ylabel("Trip Count", fontsize=10)
    ax2.set_xlim([0.0, 1.0])
    ax2.grid(True, linestyle="--", alpha=0.5)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_file)
    plt.close(fig)
    return str(out_file)
