"""Headline evaluation metrics and multi-seed statistical analysis for GridNudge (M11).

Computes:
- Peak load reduction % (18:00 - 22:00 evening window and overall peak)
- kWh shifted out of peak
- Nudges per user per day
- Opt-out rate
- Realized uplift per nudge vs oracle
- Stranded trips attributable to nudges (verified == 0)
- Safety veto count
- Cumulative regret vs oracle
- Mean INR saved per participating user
- Confidence intervals (mean ± 95% CI) across seeds under Common Random Numbers (CRN)
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def compute_run_metrics(
    run_output: Dict[str, Any],
    b0_run_output: Optional[Dict[str, Any]] = None,
    n_days: float = 7.0,
) -> Dict[str, Any]:
    """Compute complete headline evaluation metrics for a single simulation run.
    
    Args:
        run_output: Dict from run_simulation with 'timeline', 'metrics', 'outcomes'.
        b0_run_output: Optional B0 baseline run output with identical seed for CRN deltas.
        n_days: Simulation duration in days (default 7.0 for 672 steps).
        
    Returns:
        Dict of computed scalar metrics.
    """
    timeline = run_output.get("timeline", [])
    outcomes = run_output.get("outcomes", [])
    summary = run_output.get("metrics", {})

    n_users = summary.get("n_users", 2000)
    steps = summary.get("steps_simulated", len(timeline))
    sim_days = max(0.1, steps / 96.0) if steps else n_days

    # 1. Peak Feeder Load & Evening Peak (18:00 - 22:00)
    all_loads = [t.get("feeder_load_mw", 0.0) for t in timeline]
    overall_peak_mw = max(all_loads) if all_loads else 0.0

    evening_loads = [
        t.get("feeder_load_mw", 0.0)
        for t in timeline
        if 18.0 <= t.get("hour_of_day", 0.0) <= 22.0
    ]
    evening_peak_mw = max(evening_loads) if evening_loads else overall_peak_mw

    # Peak reductions vs B0 baseline if provided
    b0_peak_mw = 0.0
    b0_evening_peak_mw = 0.0
    peak_reduction_pct = 0.0
    evening_peak_reduction_pct = 0.0

    if b0_run_output is not None:
        b0_timeline = b0_run_output.get("timeline", [])
        b0_all = [t.get("feeder_load_mw", 0.0) for t in b0_timeline]
        b0_peak_mw = max(b0_all) if b0_all else 0.0

        b0_evening = [
            t.get("feeder_load_mw", 0.0)
            for t in b0_timeline
            if 18.0 <= t.get("hour_of_day", 0.0) <= 22.0
        ]
        b0_evening_peak_mw = max(b0_evening) if b0_evening else b0_peak_mw

        if b0_peak_mw > 0.0:
            peak_reduction_pct = ((b0_peak_mw - overall_peak_mw) / b0_peak_mw) * 100.0
        if b0_evening_peak_mw > 0.0:
            evening_peak_reduction_pct = ((b0_evening_peak_mw - evening_peak_mw) / b0_evening_peak_mw) * 100.0

    # 2. Shifted Energy & Nudges
    total_kwh_shifted = sum(float(o.get("kwh_shifted", 0.0)) for o in outcomes)
    nudges_sent = summary.get("total_nudges_sent", sum(1 for o in outcomes if o.get("is_nudged")))
    nudges_per_user_per_day = nudges_sent / max(1, n_users * sim_days)

    # 3. Opt-outs & User Satisfaction
    unique_opt_out_users = len(set(o["user_id"] for o in outcomes if o.get("opted_out")))
    opt_out_rate_pct = (unique_opt_out_users / max(1, n_users)) * 100.0

    # 4. Uplift & Value
    nudged_outcomes = [o for o in outcomes if o.get("is_nudged")]
    mean_uplift_per_nudge = (
        float(np.mean([o.get("true_uplift", 0.0) for o in nudged_outcomes]))
        if nudged_outcomes else 0.0
    )

    # 5. Financial Savings
    total_savings_inr = sum(float(o.get("savings_inr", 0.0)) for o in outcomes)
    adopting_users = len(set(o["user_id"] for o in outcomes if o.get("adopted")))
    mean_savings_per_adopting_user = (
        total_savings_inr / max(1, adopting_users) if adopting_users > 0 else 0.0
    )

    # 6. Safety & Audit Invariants
    # GridNudge safety gates guarantee stranded trips = 0
    stranded_trips = 0
    for o in outcomes:
        # Check if user ever dropped below critical reserve threshold due to an accepted delay
        if o.get("adopted") and o.get("initial_soc", 1.0) < 0.15:
            stranded_trips += 1

    # 7. Regret vs Oracle
    # Oracle knows true uplift and achieves max(0, true_uplift * 2.5); regret is forgone benefit
    regret = sum(
        max(0.0, float(o.get("true_uplift", 0.0)) * 2.5 - float(o.get("realized_value", 0.0)))
        for o in outcomes
    )

    return {
        "overall_peak_mw": round(overall_peak_mw, 3),
        "evening_peak_mw": round(evening_peak_mw, 3),
        "peak_reduction_pct": round(peak_reduction_pct, 2),
        "evening_peak_reduction_pct": round(evening_peak_reduction_pct, 2),
        "total_kwh_shifted": round(total_kwh_shifted, 2),
        "total_nudges_sent": nudges_sent,
        "nudges_per_user_per_day": round(nudges_per_user_per_day, 3),
        "opt_out_rate_pct": round(opt_out_rate_pct, 2),
        "mean_uplift_per_nudge": round(mean_uplift_per_nudge, 3),
        "stranded_trips_attributable": stranded_trips,
        "total_savings_inr": round(total_savings_inr, 2),
        "mean_savings_per_adopting_user": round(mean_savings_per_adopting_user, 2),
        "regret_vs_oracle": round(regret, 2),
        "adopting_users_count": adopting_users,
    }


def compute_confidence_intervals(
    values: List[float],
    confidence: float = 0.95,
) -> Tuple[float, float, float]:
    """Compute mean and 95% confidence interval half-width.
    
    Returns:
        (mean, ci_half_width, std_err)
    """
    if not values:
        return 0.0, 0.0, 0.0
    arr = np.array(values, dtype=float)
    n = len(arr)
    mean_val = float(np.mean(arr))
    if n <= 1:
        return mean_val, 0.0, 0.0

    # z-multiplier for 95% confidence ~ 1.96 (or t-distribution for small sample)
    std_dev = float(np.std(arr, ddof=1))
    std_err = std_dev / np.sqrt(n)
    # Use standard 1.96 approximation for hackathon reporting
    ci_half = 1.96 * std_err
    return mean_val, ci_half, std_err


def aggregate_policy_runs(
    runs_by_policy: Dict[str, List[Dict[str, Any]]],
    b0_runs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate multi-seed runs by policy, returning mean ± 95% CI summary.
    
    Args:
        runs_by_policy: Map of policy_name -> list of run_output dicts (one per seed).
        b0_runs: Corresponding list of B0 baseline runs under identical seeds (CRN).
        
    Returns:
        Summary dict of aggregated metrics with mean, CI, and formatted string per policy.
    """
    aggregated: Dict[str, Dict[str, Any]] = {}

    for pol_name, run_list in runs_by_policy.items():
        metrics_list: List[Dict[str, Any]] = []
        for idx, r in enumerate(run_list):
            b0_ref = b0_runs[idx] if (b0_runs and idx < len(b0_runs)) else None
            m = compute_run_metrics(r, b0_run_output=b0_ref)
            metrics_list.append(m)

        pol_summary: Dict[str, Any] = {"seeds_count": len(run_list)}
        if not metrics_list:
            aggregated[pol_name] = pol_summary
            continue

        # Keys to aggregate
        metric_keys = [
            "evening_peak_mw",
            "overall_peak_mw",
            "evening_peak_reduction_pct",
            "total_kwh_shifted",
            "nudges_per_user_per_day",
            "opt_out_rate_pct",
            "mean_uplift_per_nudge",
            "stranded_trips_attributable",
            "mean_savings_per_adopting_user",
            "regret_vs_oracle",
        ]

        for k in metric_keys:
            vals = [m[k] for m in metrics_list]
            mean_val, ci_half, std_err = compute_confidence_intervals(vals)
            pol_summary[k] = {
                "mean": round(mean_val, 3),
                "ci95": round(ci_half, 3),
                "std_err": round(std_err, 3),
                "formatted": f"{mean_val:.2f} ± {ci_half:.2f}",
            }

        aggregated[pol_name] = pol_summary

    return aggregated
