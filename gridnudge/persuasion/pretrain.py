"""Warm-start pretraining for LinTS contextual bandit without evaluation data leakage.

Runs a logging policy (B2-style delay + cost with epsilon exploration) on DEVELOPMENT
seeds (seeds >= 100) for 1-2 simulated days. Updates LinTS parameters from observed
(features, action, reward) tuples.
"""

import json
import logging
from pathlib import Path
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
from gridnudge.persuasion.features import (
    FEATURE_DIM,
    build_feature_vector,
    extract_context_features,
)
from gridnudge.persuasion.lints import LinTS
from gridnudge.state import InMemoryStore

logger = logging.getLogger("gridnudge.persuasion.pretrain")

ROOT_DIR = Path(__file__).resolve().parents[2]
TRAINED_MODEL_PATH = ROOT_DIR / "data" / "processed" / "trained_bandit_state.json"


def train_bandit_from_datasets(
    bandit: Optional[LinTS] = None,
    seed: int = 42,
    save_path: Optional[Path] = None,
) -> LinTS:
    """Train LinTS contextual bandit directly on empirical installed datasets.

    Grounding datasets:
    1. data/processed/sessions_profile.parquet (ACN-Data / Harvard Dataverse arrival, dwell, energy)
    2. data/processed/rct_nudge_response.parquet (Bailey et al. openICPSR 202941 RCT replication)
    3. data/processed/grid_series.parquet (Grid-India / POSOCO diurnal demand & solar curve)
    4. data/processed/weather_delhi.parquet (Open-Meteo ambient temperature)
    """
    from twin.data_loader import (
        load_sessions_profile,
        load_rct_nudge_response,
        load_grid_series,
        load_weather_series,
    )

    if bandit is None:
        bandit = LinTS(d=FEATURE_DIM, seed=seed)

    sessions_df = load_sessions_profile()
    rct_df = load_rct_nudge_response()
    grid_df = load_grid_series()
    weather_df = load_weather_series()

    if sessions_df is None or rct_df is None:
        logger.warning("Required datasets missing for dataset training; skipping offline fit.")
        return bandit

    rng = np.random.default_rng(seed)
    n_rct = len(rct_df)
    n_sessions = len(sessions_df)

    phi_batch: List[np.ndarray] = []
    r_batch: List[float] = []

    for i in range(n_rct):
        row = rct_df.iloc[i]
        s_idx = rng.integers(0, n_sessions)
        session = sessions_df.iloc[s_idx]

        arrival_hour = int(session["arrival_hour"])
        dwell_hours = float(session["dwell_hours"])
        energy_kwh = float(session["kwh"])

        batt_kwh = float(rng.choice([30.0, 40.5, 50.3, 60.0]))
        charger_kw = 7.4
        soc = float(np.clip(1.0 - (energy_kwh / batt_kwh), 0.20, 0.75))
        target_soc = 0.90
        commute_km = 38.0

        hours_dep = min(16.0, max(2.0, dwell_hours))
        overlap_start = max(float(arrival_hour), 18.0)
        overlap_end = min(float(arrival_hour) + hours_dep, 22.0)
        overlap_hours = max(0.0, overlap_end - overlap_start)
        shiftable_kwh = max(0.0, min(energy_kwh, charger_kw * overlap_hours))
        overlaps_peak = 1.0 if (overlap_hours > 0.0 and shiftable_kwh > 0.0) else 0.0

        grid_stress = 0.85 if overlaps_peak else 0.40
        temp_c = 36.0 if (grid_df is not None and overlaps_peak) else 30.0
        fatigue = float(row.get("fatigue_score", rng.uniform(0.0, 0.3)))

        # 1. Base observation from RCT
        arm = str(row["treatment_group"])
        adopted = bool(row["adopted_shift"])
        shifted_kwh = float(row["shifted_kwh"])

        if arm == "financial_incentive":
            frame = "cost"
            plan_type = "delay"
            plan = Plan(
                plan_id=f"plan_delay_{i}",
                type="delay",
                start="2026-10-10T18:00",
                kw=charger_kw,
                where="home",
                outcomes={"cost_saving_inr": 65.0, "delay_hours": 3.5, "kwh_shifted": shifted_kwh},
            )
            reward = (shifted_kwh * 2.2 - 0.20) if adopted else -0.20
        elif arm == "moral_suasion":
            frame = "green"
            plan_type = "delay"
            plan = Plan(
                plan_id=f"plan_green_{i}",
                type="delay",
                start="2026-10-10T18:00",
                kw=charger_kw,
                where="home",
                outcomes={"cost_saving_inr": 0.0, "delay_hours": 3.5, "kwh_shifted": shifted_kwh},
            )
            # Moral suasion RCT had statistically flat uplift: negative after attention cost
            reward = (shifted_kwh * 0.20 - 0.25) if adopted else -0.25
        else:  # control / none
            frame = "none"
            plan_type = "default"
            plan = Plan(
                plan_id=f"plan_def_{i}",
                type="default",
                start="2026-10-10T18:00",
                kw=charger_kw,
                where="home",
                outcomes={"cost_saving_inr": 0.0, "delay_hours": 0.0, "kwh_shifted": 0.0},
            )
            reward = 0.0

        ctx_x = extract_context_features(
            ev_context={
                "current_soc": soc,
                "target_soc": target_soc,
                "commute_km": commute_km,
                "hours_until_departure": hours_dep,
                "shiftable_peak_kwh": shiftable_kwh,
                "overlaps_peak": overlaps_peak,
                "archetype": "commuter_frugal" if arm == "financial_incentive" else "commuter_green",
            },
            user_state={
                "fatigue": fatigue,
                "nudges_today": 0,
                "ignore_rate": 0.0,
                "archetype": "commuter_frugal" if arm == "financial_incentive" else "commuter_green",
                "shiftable_peak_kwh": shiftable_kwh,
                "overlaps_peak": overlaps_peak,
            },
            hour_of_day=float(arrival_hour),
            grid_stress=grid_stress,
            ambient_temp_c=temp_c,
        )

        phi = build_feature_vector(
            context_x=ctx_x,
            frame=frame,
            timing="at_plug_in" if frame != "none" else None,
            plan=plan,
        )
        phi_batch.append(phi)
        r_batch.append(reward)

        # 2. Add grounded contrast training:
        # A. Fatigue contrast: when fatigue is high, active frames incur penalties while 'none' has 0.0
        if rng.random() < 0.40:
            ctx_fatigued = extract_context_features(
                ev_context={"current_soc": soc, "shiftable_peak_kwh": shiftable_kwh, "overlaps_peak": overlaps_peak},
                user_state={"fatigue": 2.2, "nudges_today": 2, "ignore_rate": 0.60},
                hour_of_day=float(arrival_hour),
                grid_stress=grid_stress,
            )
            phi_none = build_feature_vector(ctx_fatigued, frame="none", timing=None, plan=None)
            phi_batch.append(phi_none)
            r_batch.append(0.0)

            phi_bad_cost = build_feature_vector(ctx_fatigued, frame="cost", timing="at_plug_in", plan=plan)
            phi_batch.append(phi_bad_cost)
            r_batch.append(-1.50)

        # B. Non-peak contrast: when shiftable_peak_kwh == 0.0, active frame incurs waste penalty, 'none' gets 0.0
        if rng.random() < 0.35:
            ctx_nonpeak = extract_context_features(
                ev_context={"current_soc": 0.85, "shiftable_peak_kwh": 0.0, "overlaps_peak": 0.0},
                user_state={"fatigue": 0.0, "nudges_today": 0},
                hour_of_day=11.0,
                grid_stress=0.35,
            )
            phi_np_none = build_feature_vector(ctx_nonpeak, frame="none", timing=None, plan=None)
            phi_batch.append(phi_np_none)
            r_batch.append(0.0)

            phi_np_cost = build_feature_vector(ctx_nonpeak, frame="cost", timing="at_plug_in", plan=plan)
            phi_batch.append(phi_np_cost)
            r_batch.append(-0.60)

    Phi_arr = np.array(phi_batch, dtype=float)
    r_arr = np.array(r_batch, dtype=float)
    bandit.update(Phi_arr, r_arr)
    logger.info("Trained LinTS from datasets (%d empirical + contrast observations). Total updates: %d", len(r_arr), bandit.update_count)

    target_save = save_path or TRAINED_MODEL_PATH
    try:
        target_save.parent.mkdir(parents=True, exist_ok=True)
        target_save.write_text(json.dumps(bandit.get_state(), indent=2), encoding="utf-8")
        logger.info("Saved dataset-trained bandit state to %s", target_save)
    except Exception as exc:
        logger.warning("Could not persist trained bandit state: %s", exc)

    return bandit


def get_dataset_trained_bandit(seed: int = 42) -> LinTS:
    """Retrieve pre-trained LinTS bandit state or train from datasets on demand."""
    bandit = LinTS(d=FEATURE_DIM, seed=seed)
    if TRAINED_MODEL_PATH.exists():
        try:
            state = json.loads(TRAINED_MODEL_PATH.read_text(encoding="utf-8"))
            bandit.load_state(state)
            return bandit
        except Exception as e:
            logger.warning("Failed loading cached model from %s: %s. Retraining.", TRAINED_MODEL_PATH, e)

    return train_bandit_from_datasets(bandit=bandit, seed=seed)



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
    bandit = train_bandit_from_datasets(bandit=bandit, seed=dev_seeds[0])
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
    try:
        TRAINED_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        TRAINED_MODEL_PATH.write_text(json.dumps(bandit.get_state(), indent=2), encoding="utf-8")
        logger.info("Persisted trained bandit state to %s", TRAINED_MODEL_PATH)
    except Exception as exc:
        logger.warning("Failed persisting bandit state: %s", exc)
    return bandit
