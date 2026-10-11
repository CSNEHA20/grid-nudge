"""Warm-start pretraining for LinTS contextual bandit without evaluation data leakage.

Runs a logging policy (B2-style delay + cost with epsilon exploration) on DEVELOPMENT
seeds (seeds >= 100) for 1-2 simulated days. Updates LinTS parameters from observed
(features, action, reward) tuples.
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np

from gridnudge.contracts import (
    Allocation,
    DecisionRecord,
    Language,
    Persuasion,
    Plan,
    Safety,
)
from gridnudge.persuasion.features import FEATURE_DIM
from gridnudge.persuasion.lints import LinTS
from gridnudge.state import InMemoryStore

logger = logging.getLogger("gridnudge.persuasion.pretrain")


def pretrain_bandit(
    bandit: Optional[LinTS] = None,
    dev_seeds: List[int] = [101, 102],
    n_users: int = 500,
    days: int = 2,
    epsilon: float = 0.20,
    store: Optional[InMemoryStore] = None,
) -> LinTS:
    """Pretrain LinTS contextual bandit using a logging policy on development seeds.

    Args:
        bandit: Existing LinTS instance, or created if None.
        dev_seeds: Seed list for training. Must all be >= 100 to prevent leakage with final seeds (1-5).
        n_users: Number of fleet users in simulated pretraining environment.
        days: Duration in days (1 day = 96 steps of 15 min).
        epsilon: Exploration probability for logging policy.
        store: StateStore instance (defaults to InMemoryStore if None).

    Returns:
        Trained LinTS instance with warm-started posterior parameters (A, b).
    """
    from gridnudge.pipeline import process_outcomes
    from twin.world import World

    for s in dev_seeds:
        if s < 100:
            raise ValueError(f"Development seeds must be >= 100 to avoid test leakage. Got seed {s}")

    if bandit is None:
        bandit = LinTS(d=FEATURE_DIM, seed=dev_seeds[0])
    if store is None:
        store = InMemoryStore()

    n_steps = days * 96
    frames = ["cost", "green", "battery", "convenience", "none"]

    for seed in dev_seeds:
        rng = np.random.default_rng(seed)
        world = World(seed=seed, n_users=n_users)
        # Apply heatwave during pretrain to observe peak stress behavior
        world.inject({
            "event_type": "heatwave",
            "start_step": 64,
            "end_step": 92,
            "parameters": {"temp_c": 42.0, "multiplier": 1.20},
        })

        for step in range(n_steps):
            # 1. Process closed outcomes from prior steps
            closed = world.pop_outcomes()
            if closed:
                process_outcomes(closed, store=store, bandit=bandit)

            # 2. Check peak window
            grid_st = world.grid_state()
            if not grid_st.get("is_peak_window", False):
                world.step()
                continue

            candidates = world.candidates()
            if not candidates:
                world.step()
                continue

            decisions_to_store: List[Dict[str, Any]] = []
            applied_to_world: List[Dict[str, Any]] = []

            for c in candidates:
                u_id = c["user_id"]
                soc = float(c["soc"])
                batt_kwh = float(c["battery_kwh"])
                charger_kw = float(c["charger_kw"])
                target_soc = float(c.get("target_soc", 0.90))
                dep_step = c.get("departure_step", -1)
                hours_dep = (
                    max(1.0, (dep_step - world.current_step) * (world.step_minutes / 60.0))
                    if dep_step is not None and dep_step > world.current_step
                    else 8.0
                )

                # Compute shiftable peak kWh
                energy_needed = max(0.0, (target_soc - soc) * batt_kwh)
                overlap_start = max(world.hour_of_day, 18.0)
                overlap_end = min(world.hour_of_day + hours_dep, 22.0)
                overlap_hours = max(0.0, overlap_end - overlap_start)
                shiftable_kwh = max(0.0, min(energy_needed, charger_kw * overlap_hours))
                overlaps_peak = 1.0 if (overlap_hours > 0.0 and shiftable_kwh > 0.0) else 0.0

                too_soon = (dep_step is not None and dep_step > world.current_step and hours_dep < 5.0)
                is_safe = (soc >= 0.25) and not too_soon and (c.get("nudges_today", 0) < 1)

                # Logging policy action selection
                explore = rng.random() < epsilon
                if not is_safe:
                    chosen_frame = "none"
                    chosen_plan_type = "default"
                elif explore:
                    chosen_frame = rng.choice(frames)
                    chosen_plan_type = "delay" if chosen_frame != "none" else "default"
                else:
                    # B2-style delay + cost default
                    chosen_frame = "cost"
                    chosen_plan_type = "delay"

                d_id = f"pretrain_s{world.current_step}_u{u_id}"
                plan_id = f"plan_{chosen_plan_type}_{u_id}"
                plan_obj = Plan(
                    plan_id=plan_id,
                    type=chosen_plan_type,
                    start=world.current_time.isoformat(),
                    kw=charger_kw,
                    where="home",
                    outcomes={
                        "cost_saving_inr": 65.0 if chosen_plan_type == "delay" else 0.0,
                        "delay_hours": 3.5,
                        "kwh_shifted": shiftable_kwh if chosen_plan_type == "delay" else 0.0,
                    },
                )

                d_rec = DecisionRecord(
                    decision_id=d_id,
                    run_id="pretrain_logging",
                    sim_time=world.current_time.isoformat(),
                    user_id=str(u_id),
                    ev={
                        "battery_kwh": batt_kwh,
                        "current_soc": soc,
                        "charger_kw": charger_kw,
                        "target_soc": target_soc,
                        "shiftable_peak_kwh": round(shiftable_kwh, 3),
                        "overlaps_peak": overlaps_peak,
                    },
                    context={
                        "archetype": c["archetype"],
                        "fatigue": c["fatigue"],
                        "last_frame": c.get("last_frame", "none"),
                        "nudges_today": c.get("nudges_today", 0),
                        "shiftable_peak_kwh": round(shiftable_kwh, 3),
                        "overlaps_peak": overlaps_peak,
                    },
                    plans=[plan_obj],
                    safety=Safety(
                        invariants_ok=True,
                        cedar="ALLOW",
                        vetoed=[],
                    ),
                    persuasion=Persuasion(
                        chosen_plan=plan_id if chosen_frame != "none" else None,
                        frame=chosen_frame,
                        timing="at_plug_in" if chosen_frame != "none" else None,
                        uplift_mean=0.15 if chosen_frame != "none" else 0.0,
                        uplift_p10=0.08 if chosen_frame != "none" else 0.0,
                        propensity=1.0 - epsilon if chosen_frame == "cost" else epsilon / len(frames),
                        explored=explore,
                    ),
                    allocation=Allocation(
                        selected=True if chosen_frame != "none" else False,
                        shadow_price=0.0,
                    ),
                    language=Language(verified=True, source="template"),
                )

                decisions_to_store.append(d_rec.model_dump())

                if chosen_frame != "none":
                    applied_to_world.append({
                        "decision_id": d_id,
                        "user_id": int(u_id),
                        "plan": {"type": "delay"},
                        "frame": chosen_frame,
                        "timing": "at_plug_in",
                        "savings_inr": 65.0,
                        "delay_hours": 3.5,
                    })
                else:
                    applied_to_world.append({
                        "decision_id": d_id,
                        "user_id": int(u_id),
                        "plan": {"type": "default"},
                        "frame": "none",
                        "timing": None,
                        "savings_inr": 0.0,
                        "delay_hours": 0.0,
                    })

            store.put_decisions(decisions_to_store)
            world.apply_decisions(applied_to_world)
            world.step()

        # Final drain of remaining outcomes
        closed = world.pop_outcomes()
        if closed:
            process_outcomes(closed, store=store, bandit=bandit)

    logger.info("Pretrained bandit on seeds %s. Total updates: %d", dev_seeds, bandit.update_count)
    return bandit
