"""Simulation runner for the digital twin."""

import time
from typing import Any, Callable, Dict, List, Optional
from twin.world import World


def run_simulation(
    world: Optional[World] = None,
    seed: int = 42,
    n_users: int = 2000,
    n_steps: int = 672,  # 7 days * 96 steps/day
    policy_fn: Optional[Callable[[World], List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Execute a digital twin simulation run.

    Args:
        world: Optional existing World instance. If None, instantiates World(seed, n_users).
        seed: Random seed if world is instantiated.
        n_users: Number of EVs in the synthetic fleet.
        n_steps: Total 15-minute simulation intervals to advance (672 = 7 days).
        policy_fn: Optional decision policy callback: policy_fn(world) -> list of decisions.
                   If None, runs unmanaged default behavior (B0 baseline).

    Returns:
        Dict with 'timeline', 'metrics', and 'outcomes'.
    """
    if world is None:
        world = World(seed=seed, n_users=n_users)

    timeline: List[Dict[str, Any]] = []
    all_outcomes: List[Dict[str, Any]] = []
    nudges_count = 0

    start_time = time.perf_counter()

    for step_idx in range(n_steps):
        # Apply policy if supplied
        if policy_fn is not None:
            candidates = world.candidates()
            if candidates:
                decisions = policy_fn(world)
                if decisions:
                    world.apply_decisions(decisions)
                    for d in decisions:
                        if d.get("frame", "none") != "none" and d.get("plan", {}).get("type") != "default":
                            nudges_count += 1

        # Advance world by one step
        telemetry = world.step()
        timeline.append(telemetry)

        # Collect any resolved outcomes
        outcomes = world.pop_outcomes()
        if outcomes:
            all_outcomes.extend(outcomes)

    elapsed_s = time.perf_counter() - start_time

    # Calculate overall summary metrics
    feeder_loads = [t["feeder_load_mw"] for t in timeline]
    ev_loads = [t["ev_load_mw"] for t in timeline]
    stresses = [t["grid_stress"] for t in timeline]
    total_energy_kwh = sum(t["energy_kwh_delivered"] for t in timeline)
    total_kwh_shifted = sum(o.get("kwh_shifted", 0.0) for o in all_outcomes)

    metrics = {
        "seed": world.seed,
        "n_users": world.n_users,
        "steps_simulated": n_steps,
        "elapsed_seconds": round(elapsed_s, 2),
        "peak_feeder_load_mw": round(max(feeder_loads), 4) if feeder_loads else 0.0,
        "peak_ev_load_mw": round(max(ev_loads), 4) if ev_loads else 0.0,
        "avg_grid_stress": round(sum(stresses) / len(stresses), 4) if stresses else 0.0,
        "max_grid_stress": round(max(stresses), 4) if stresses else 0.0,
        "total_energy_kwh": round(total_energy_kwh, 2),
        "total_nudges_sent": nudges_count,
        "total_kwh_shifted": round(total_kwh_shifted, 2),
        "outcomes_count": len(all_outcomes),
    }

    return {
        "timeline": timeline,
        "metrics": metrics,
        "outcomes": all_outcomes,
    }
