"""Baseline charging and nudging policies for benchmarking GridNudge.

B0: Uncontrolled default charging (charge immediately upon plugging in).
B1: Simple rule-based shifting (nudge every plugged EV during peak to delay).
B2: Safe rule-based planner (nudge only when SOC >= 25% to preserve reserve).
"""

from typing import Any, Dict, List
from twin.runner import run_simulation
from twin.world import World


def policy_b0(world: World) -> List[Dict[str, Any]]:
    """B0: Uncontrolled baseline. Zero interventions."""
    return []


def policy_b1(world: World) -> List[Dict[str, Any]]:
    """B1: Simple rule-based peak shifting.

    Nudges all candidates plugged during peak hours (17:00 - 23:00) with a cost-frame delay.
    """
    state = world.grid_state()
    if not state.get("is_peak_window", False):
        return []

    candidates = world.candidates()
    decisions = []
    for c in candidates:
        decisions.append({
            "decision_id": f"b1_s{world.current_step}_u{c['user_id']}",
            "user_id": c["user_id"],
            "plan": {"type": "delay"},
            "frame": "cost",
            "timing": "at_plug_in",
            "savings_inr": 65.0,
            "delay_hours": 3.5,
        })
    return decisions


def policy_b2(world: World) -> List[Dict[str, Any]]:
    """B2: Safe rule-based planner.

    Nudges users during peak, but applies a safety rule:
    only delay if current SOC >= 0.25 so journey confidence is not compromised.
    """
    state = world.grid_state()
    if not state.get("is_peak_window", False):
        return []

    candidates = world.candidates()
    decisions = []
    for c in candidates:
        if c.get("soc", 0.0) < 0.25:
            # Safety rule: do not delay low-SOC vehicle
            continue

        decisions.append({
            "decision_id": f"b2_s{world.current_step}_u{c['user_id']}",
            "user_id": c["user_id"],
            "plan": {"type": "delay"},
            "frame": "cost",
            "timing": "at_plug_in",
            "savings_inr": 65.0,
            "delay_hours": 3.5,
        })
    return decisions


def run_baseline_comparison(
    seed: int = 42,
    n_users: int = 2000,
    n_steps: int = 96,  # 1 day by default
) -> Dict[str, Dict[str, Any]]:
    """Compare B0 and B1 under Common Random Numbers (CRN)."""
    # Run B0
    w0 = World(seed=seed, n_users=n_users)
    res_b0 = run_simulation(world=w0, n_steps=n_steps, policy_fn=policy_b0)

    # Run B1 with identical seed
    w1 = World(seed=seed, n_users=n_users)
    res_b1 = run_simulation(world=w1, n_steps=n_steps, policy_fn=policy_b1)

    return {
        "B0_uncontrolled": res_b0["metrics"],
        "B1_rule_based": res_b1["metrics"],
    }
