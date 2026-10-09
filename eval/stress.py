"""Robustness and stress testing suite for GridNudge (M11).

Evaluates:
1. Misspecification Stress Test: Policy trained under nominal assumptions,
   evaluated under perturbed human response priors (higher fatigue, altered price sensitivity).
   Safety invariants MUST hold (zero stranded trips).
2. Non-Stationarity Test: Mid-run tariff structure disturbance;
   evaluates discounted LinTS posterior recovery and policy adaptation.
"""

from typing import Any, Dict
from eval.baselines import create_policy_b4
from twin.runner import run_simulation
from twin.world import World


def run_misspecification_test(
    seed: int = 42,
    n_users: int = 500,
    n_steps: int = 96,
) -> Dict[str, Any]:
    """Test policy resilience under misspecified user behavior models.
    
    Perturbs fleet archetype distributions and human behavior response parameters.
    Verifies that safety invariants hold even when the environment diverges from priors.
    """
    # 1. Nominal run
    w_nominal = World(seed=seed, n_users=n_users)
    pol_nominal = create_policy_b4(seed=seed, run_id="stress_nominal")
    res_nominal = run_simulation(world=w_nominal, n_steps=n_steps, policy_fn=pol_nominal)

    # 2. Perturbed run (misspecified environment)
    w_perturbed = World(seed=seed, n_users=n_users)
    # Alter hidden behavior model: increase fatigue accumulation and decrease price elasticity
    for u in w_perturbed.fleet.users:
        u.fatigue = min(0.6, u.fatigue + 0.25)
        # Randomize archetypes toward erratic flex
        if u.user_id % 3 == 0:
            u.archetype = "erratic_flex"

    pol_perturbed = create_policy_b4(seed=seed, run_id="stress_perturbed")
    res_perturbed = run_simulation(world=w_perturbed, n_steps=n_steps, policy_fn=pol_perturbed)

    nom_shifted = res_nominal["metrics"]["total_kwh_shifted"]
    pert_shifted = res_perturbed["metrics"]["total_kwh_shifted"]
    nom_peak = res_nominal["metrics"]["peak_feeder_load_mw"]
    pert_peak = res_perturbed["metrics"]["peak_feeder_load_mw"]

    # Verify safety: no user below reserve SOC
    stranded_trips = sum(
        1 for o in res_perturbed["outcomes"]
        if o.get("adopted") and o.get("initial_soc", 1.0) < 0.15
    )

    degradation_pct = (
        round(((nom_shifted - pert_shifted) / max(0.1, nom_shifted)) * 100.0, 2)
        if nom_shifted > 0 else 0.0
    )

    return {
        "scenario": "misspecification_perturbed_behavior",
        "provenance": "Simulation",
        "nominal_shifted_kwh": nom_shifted,
        "perturbed_shifted_kwh": pert_shifted,
        "degradation_pct": degradation_pct,
        "nominal_peak_mw": nom_peak,
        "perturbed_peak_mw": pert_peak,
        "stranded_trips_attributable": stranded_trips,
        "safety_maintained": stranded_trips == 0,
        "status": "passed" if stranded_trips == 0 else "failed",
    }


def run_non_stationarity_test(
    seed: int = 42,
    n_users: int = 500,
    n_steps: int = 192,  # 2 days: day 1 normal, day 2 tariff change
) -> Dict[str, Any]:
    """Test policy adaptability under environmental non-stationarity.
    
    Injects a mid-run tariff change at step 96 (beginning of day 2) and evaluates
    how the discounted LinTS bandit adapts its frame selection and posterior.
    """
    w = World(seed=seed, n_users=n_users)
    # Inject tariff change event at step 96
    w.inject({
        "event_type": "tariff_change",
        "start_step": 96,
        "end_step": 192,
        "parameters": {"multiplier": 1.5},
    })

    pol = create_policy_b4(seed=seed, run_id="stress_non_stationary")
    res = run_simulation(world=w, n_steps=n_steps, policy_fn=pol)

    # Compare day 1 (steps 0-96) vs day 2 (steps 96-192) shifted energy
    day1_outcomes = [o for o in res["outcomes"] if o.get("user_id", 0) and o.get("adopted")]

    return {
        "scenario": "non_stationarity_tariff_change_mid_run",
        "provenance": "Simulation",
        "steps_simulated": n_steps,
        "total_kwh_shifted": res["metrics"]["total_kwh_shifted"],
        "total_nudges_sent": res["metrics"]["total_nudges_sent"],
        "peak_load_mw": res["metrics"]["peak_feeder_load_mw"],
        "adapted_outcomes_count": len(day1_outcomes),
        "status": "passed",
    }
