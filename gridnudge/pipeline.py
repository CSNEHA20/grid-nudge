"""GridNudge decision pipeline orchestrator.

Orchestrates the complete decision path across modules:
Perception (M3) -> Planner (M4) -> Safety Gate #1 (M5) -> Persuasion Engine / LinTS (M6)
-> Fleet Allocator (M7) -> Safety Gate #2 (M5) -> Language & Verifier (M8)
over a swappable StateStore (M9) with strict fail-silent error wrapping.
"""

from datetime import datetime
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid
import numpy as np

from gridnudge.contracts import (
    Allocation,
    DecisionRecord,
    Language,
    Outcome,
    Persuasion,
    Plan,
    Safety,
)
from gridnudge.language.render import render_nudge_message
from gridnudge.perception.battery import evaluate_battery_view
from gridnudge.perception.grid import estimate_grid_stress
from gridnudge.perception.journey import estimate_journey_confidence
from gridnudge.perception.station import estimate_station_wait
from gridnudge.persuasion.fatigue import update_fatigue_after_nudge
from gridnudge.persuasion.features import (
    build_feature_vector,
    extract_context_features,
)
from gridnudge.persuasion.lints import LinTS
from gridnudge.persuasion.uplift import (
    compute_causal_reward,
    select_persuasion_action,
)
from gridnudge.planner import generate_candidate_plans
from gridnudge.safety.cedar_check import check_nudge_authorization, evaluate_cedar_policy
from gridnudge.safety.failsilent import build_fail_silent_record
from gridnudge.safety.invariants import check_invariants
from gridnudge.state import InMemoryStore, StateStore
from gridnudge.allocator import allocate_fleet_nudges

logger = logging.getLogger(__name__)


def decide_batch(
    request: Dict[str, Any],
    store: Optional[StateStore] = None,
    bandit: Optional[LinTS] = None,
    render_llm: bool = False,
    apply_allocation: bool = True,
) -> List[DecisionRecord]:
    """Execute batched inference across candidate EVs plugged in at current simulation timestep.

    Args:
        request: Request dictionary matching API schema (run_id, sim_time, candidates, grid_forecast).
        store: Swappable StateStore instance (defaults to InMemoryStore if None).
        bandit: LinTS contextual bandit instance (loaded from store or created if None).
        render_llm: Whether to attempt Bedrock LLM generation in language stage.

    Returns:
        List of typed, verified DecisionRecord objects.
    """
    if store is None:
        store = InMemoryStore()

    run_id = str(request.get("run_id", f"run_{uuid.uuid4().hex[:6]}"))
    sim_time_iso = str(request.get("sim_time", datetime.now().isoformat()))
    candidates = request.get("candidates", [])
    grid_fc = request.get("grid_forecast") or {}

    try:
        sim_dt = datetime.fromisoformat(sim_time_iso.replace("Z", "+00:00"))
        hour_of_day = sim_dt.hour + (sim_dt.minute / 60.0)
    except Exception:
        hour_of_day = 18.0

    feeder_load_mw = float(grid_fc.get("feeder_load_mw", 6.0))
    capacity_mw = float(grid_fc.get("capacity_mw", 12.0))
    grid_stress = float(grid_fc.get("grid_stress", feeder_load_mw / max(0.1, capacity_mw)))
    ambient_temp_c = float(grid_fc.get("ambient_temp_c", 30.0))

    # Initialize / load bandit model from store if not provided
    if bandit is None:
        model_dict = store.get_model("lints_persuasion")
        bandit = LinTS(seed=42)
        if model_dict and "A" in model_dict:
            bandit.load_state(model_dict)

    # Pre-fetch user states for all candidate users
    user_ids = [str(c.get("user_id")) for c in candidates if c.get("user_id") is not None]
    stored_users = store.get_users(user_ids)

    # -------------------------------------------------------------
    # Stage 1: Individual candidate perception, planning, safety #1, persuasion
    # -------------------------------------------------------------
    candidate_records: List[Dict[str, Any]] = []
    stage1_results: List[Dict[str, Any]] = []

    for c in candidates:
        user_id = str(c.get("user_id", "unknown")) if isinstance(c, dict) else "unknown"
        ev_ctx: Dict[str, Any] = {}
        try:
            if not isinstance(c, dict):
                raise ValueError("Candidate item must be a dictionary")
            ev_raw = c.get("ev")
            if not isinstance(ev_raw, dict):
                raise ValueError("Candidate 'ev' must be a dictionary")
            ev_ctx = dict(ev_raw)
            trip_raw = c.get("trip")
            trip_ctx = dict(trip_raw) if isinstance(trip_raw, dict) else {}
            ctx_raw = c.get("context")
            user_state = dict(stored_users.get(user_id, ctx_raw if isinstance(ctx_raw, dict) else {}))

            # 1. Perception (M3)
            soc = float(ev_ctx.get("current_soc", ev_ctx.get("soc", 0.5)))
            batt_kwh = float(ev_ctx.get("battery_kwh", 40.0))
            dist_km = float(trip_ctx.get("commute_km", 30.0))

            journey_view = estimate_journey_confidence(
                departure_soc=soc,
                battery_kwh=batt_kwh,
                distance_km=dist_km,
                ambient_temp_c=ambient_temp_c,
            )
            battery_view = evaluate_battery_view(
                soc=soc,
                battery_kwh=batt_kwh,
                charging_kw=float(ev_ctx.get("charger_kw", 7.4)),
                ambient_temp_c=ambient_temp_c,
            )
            station_view = estimate_station_wait(
                station_id=c.get("station_id", "station_cs_01"),
                eta_step=0,
            )
            grid_view = estimate_grid_stress(
                feeder_load_mw=feeder_load_mw,
                capacity_mw=capacity_mw,
            )

            # 2. Planner (M4)
            all_plans = generate_candidate_plans(
                user_id=user_id,
                ev_context=ev_ctx,
                sim_time_iso=sim_time_iso,
                hour_of_day=hour_of_day,
                grid_stress=grid_stress,
                commute_distance_km=dist_km,
                ambient_temp_c=ambient_temp_c,
            )

            # 3. Safety Filter #1 (M5)
            safe_plans: List[Plan] = []
            vetoed_reasons: List[str] = []

            for p in all_plans:
                invariants_ok, inv_reasons = check_invariants(
                    plan=p,
                    ev_context=ev_ctx,
                    sim_time_iso=sim_time_iso,
                )
                cedar_verdict, cedar_reasons = check_nudge_authorization(
                    user_id=user_id,
                    decision_id=f"d_{user_id}",
                    plan=p,
                    ev_context=ev_ctx,
                    hour_of_day=hour_of_day,
                    nudges_today=int(user_state.get("nudges_today", 0)),
                    opted_out=bool(user_state.get("opted_out", False)),
                    invariants_ok=invariants_ok,
                )

                if invariants_ok and cedar_verdict == "ALLOW":
                    safe_plans.append(p)
                else:
                    vetoed_reasons.extend(inv_reasons + cedar_reasons)

            safety_record = Safety(
                invariants_ok=len(safe_plans) > 0,
                cedar="ALLOW" if safe_plans else "DENY",
                vetoed=vetoed_reasons,
            )

            # 4. Persuasion Engine / LinTS (M6)
            persuasion, phi, chosen_act = select_persuasion_action(
                user_id=user_id,
                ev_context=ev_ctx,
                user_state=user_state,
                safe_plans=safe_plans,
                bandit=bandit,
                hour_of_day=hour_of_day,
                grid_stress=grid_stress,
                ambient_temp_c=ambient_temp_c,
            )

            chosen_plan_obj: Optional[Plan] = None
            if persuasion.chosen_plan:
                for p in safe_plans:
                    if p.plan_id == persuasion.chosen_plan:
                        chosen_plan_obj = p
                        break

            # Collect for Fleet Allocator
            candidate_id = f"cand_{user_id}"
            alloc_cand = {
                "candidate_id": candidate_id,
                "user_id": user_id,
                "persuasion": persuasion,
                "plan": chosen_plan_obj,
                "user_state": user_state,
                "ev_context": ev_ctx,
            }
            candidate_records.append(alloc_cand)

            stage1_results.append({
                "candidate_id": candidate_id,
                "user_id": user_id,
                "ev_ctx": ev_ctx,
                "user_state": user_state,
                "journey_view": journey_view,
                "battery_view": battery_view,
                "station_view": station_view,
                "grid_view": grid_view,
                "all_plans": all_plans,
                "safe_plans": safe_plans,
                "safety_record": safety_record,
                "persuasion": persuasion,
                "chosen_plan_obj": chosen_plan_obj,
                "phi": phi,
                "fail_silent": False,
                "error": None,
            })

        except Exception as ex:
            logger.exception("Error processing candidate %s in stage 1: %s", user_id, ex)
            fail_rec = build_fail_silent_record(
                run_id=run_id,
                sim_time=sim_time_iso,
                user_id=user_id,
                ev=ev_ctx,
                error_message=str(ex),
            )
            stage1_results.append({
                "candidate_id": f"cand_{user_id}",
                "user_id": user_id,
                "fail_silent": True,
                "fail_record": fail_rec,
                "error": str(ex),
            })

    # -------------------------------------------------------------
    # Stage 2: Fleet Allocator (M7)
    # -------------------------------------------------------------
    allocations_by_id: Dict[str, Allocation] = {}
    if candidate_records:
        if not apply_allocation:
            # Policy B3: bandit without allocator
            for c_rec in candidate_records:
                allocations_by_id[c_rec["candidate_id"]] = Allocation(
                    selected=True,
                    shadow_price=0.0,
                    slot=sim_time_iso,
                )
        else:
            try:
                allocations_by_id = allocate_fleet_nudges(
                    candidate_records=candidate_records,
                    total_plugged_count=max(len(candidates), 1),
                    sim_time_iso=sim_time_iso,
                    feeder_capacity_mw=capacity_mw,
                    base_load_mw=float(grid_fc.get("base_offpeak_mw", 5.5)),
                )
            except Exception as ex:
                logger.exception("Allocator failed; failing silent for batch allocation: %s", ex)
                # Default to no active allocation
                for c_rec in candidate_records:
                    allocations_by_id[c_rec["candidate_id"]] = Allocation(
                        selected=False,
                        shadow_price=0.0,
                        slot=None,
                    )

    # -------------------------------------------------------------
    # Stage 3: Safety #2, Language & Verifier (M8), DecisionRecord packaging
    # -------------------------------------------------------------
    final_records: List[DecisionRecord] = []
    updated_users: Dict[str, Dict[str, Any]] = {}

    for res in stage1_results:
        if res.get("fail_silent"):
            final_records.append(res["fail_record"])
            continue

        user_id = res["user_id"]
        cid = res["candidate_id"]
        persuasion = res["persuasion"]
        chosen_plan_obj = res["chosen_plan_obj"]
        user_state = res["user_state"]
        ev_ctx = res["ev_ctx"]
        alloc = allocations_by_id.get(cid, Allocation(selected=False, shadow_price=0.0, slot=None))

        # Check if intervention was allocated
        is_active_nudge = alloc.selected and (persuasion.frame != "none") and (chosen_plan_obj is not None)

        # Safety Gate #2: Re-verify final chosen plan
        safety_rec = res["safety_record"]
        if is_active_nudge and chosen_plan_obj:
            # Check quiet hours (23:00 - 06:00) per Cedar rules
            if hour_of_day >= 23.0 or hour_of_day < 6.0:
                is_active_nudge = False
                safety_rec.vetoed.append("Safety Gate #2: Blocked by quiet hours restriction (23:00 - 06:00)")
                safety_rec.cedar = "DENY"

            # Check journey confidence threshold under plan
            plan_lb = float(chosen_plan_obj.outcomes.get("journey_conf_lb", 1.0))
            if plan_lb < 0.90:
                is_active_nudge = False
                safety_rec.vetoed.append(f"Safety Gate #2: Plan journey confidence LB ({plan_lb:.2f}) < 0.90")
                safety_rec.invariants_ok = False

        if not is_active_nudge:
            # Suppress persuasion if unselected by allocator or Safety #2
            persuasion = Persuasion(
                chosen_plan=None,
                frame="none",
                timing=None,
                uplift_mean=persuasion.uplift_mean,
                uplift_p10=persuasion.uplift_p10,
                propensity=persuasion.propensity,
                explored=persuasion.explored,
            )
            alloc = Allocation(selected=False, shadow_price=alloc.shadow_price, slot=None)
            lang_rec = Language(message=None, facts_used={}, verified=True, source="none")
        else:
            # Render and verify language
            saving_inr = int(round(float(chosen_plan_obj.outcomes.get("cost_saving_inr", 50.0))))
            facts = {
                "start_time": alloc.slot or chosen_plan_obj.start or "23:00",
                "saving_inr": max(10, saving_inr),
                "window": "23:00 - 06:00",
                "journey_conf": int(round(float(chosen_plan_obj.outcomes.get("journey_conf_lb", 0.94)) * 100)),
            }
            lang_rec = render_nudge_message(
                facts=facts,
                frame=persuasion.frame,
                use_llm=render_llm,
            )

        # Update user state tracking
        new_fatigue = user_state.get("fatigue", 0.0)
        nudges_today = user_state.get("nudges_today", 0)
        last_frame = user_state.get("last_frame", "none")

        if is_active_nudge:
            is_repeat = (last_frame == persuasion.frame)
            new_fatigue = update_fatigue_after_nudge(new_fatigue, is_repeat_frame=is_repeat)
            nudges_today += 1
            last_frame = persuasion.frame

        updated_users[user_id] = {
            "fatigue": round(float(new_fatigue), 3),
            "nudges_today": int(nudges_today),
            "last_frame": str(last_frame),
            "opted_out": bool(user_state.get("opted_out", False)),
        }

        # Construct single typed DecisionRecord
        d_id = f"d_{sim_dt.strftime('%Y%m%d%H%M')}_{user_id}"
        rec = DecisionRecord(
            decision_id=d_id,
            run_id=run_id,
            sim_time=sim_time_iso,
            user_id=str(user_id),
            ev=ev_ctx,
            journey=res["journey_view"],
            battery=res["battery_view"],
            station=res["station_view"],
            grid=res["grid_view"],
            plans=res["all_plans"],
            safety=safety_rec,
            persuasion=persuasion,
            allocation=alloc,
            language=lang_rec,
            outcome=Outcome(),
            fail_silent=False,
            error=None,
        )
        final_records.append(rec)

    # Persist updated user states and decision records to store
    if updated_users:
        store.put_users(updated_users)

    if final_records:
        store.put_decisions([r.model_dump() for r in final_records])

    return final_records


def process_outcomes(
    outcomes: List[Dict[str, Any]],
    store: StateStore,
    bandit: Optional[LinTS] = None,
) -> Dict[str, Any]:
    """Ingest realized simulation outcomes, compute causal rewards, and update LinTS posterior.

    Args:
        outcomes: List of outcome dicts (decision_id, adopted, kwh_shifted, savings_inr, opted_out, etc.)
        store: StateStore where decisions and model state are persisted.
        bandit: Optional active LinTS model. If None, loaded from store.

    Returns:
        Summary dictionary with update counts and realized reward metrics.
    """
    if bandit is None:
        model_dict = store.get_model("lints_persuasion")
        bandit = LinTS(seed=42)
        if model_dict and "A" in model_dict:
            bandit.load_state(model_dict)

    updated_records: List[Dict[str, Any]] = []
    phi_batch: List[np.ndarray] = []
    reward_batch: List[float] = []

    for o in outcomes:
        d_id = str(o.get("decision_id"))
        dec_dict = store.get_decision(d_id)
        if not dec_dict:
            continue

        adopted = bool(o.get("adopted", False))
        kwh_shifted = float(o.get("kwh_shifted", 0.0))
        savings_inr = float(o.get("savings_inr", 0.0))
        stress_delta = float(o.get("battery_stress_delta", 0.0))
        opted_out = bool(o.get("opted_out", False))

        # Calculate causal reward
        reward = compute_causal_reward(
            kwh_shifted=kwh_shifted,
            savings_inr=savings_inr,
            grid_value=1.5,
            battery_stress_delta=stress_delta,
            opted_out=opted_out,
        )

        # Update outcome record
        dec_dict["outcome"] = {
            "adopted": adopted,
            "kwh_shifted": round(kwh_shifted, 2),
            "opted_out": opted_out,
            "reward": round(reward, 4),
        }
        updated_records.append(dec_dict)

        # Build feature vector phi for bandit posterior update
        try:
            persuasion_data = dec_dict.get("persuasion", {})
            frame = persuasion_data.get("frame", "none")
            timing = persuasion_data.get("timing")
            chosen_plan_id = persuasion_data.get("chosen_plan")

            chosen_plan_obj: Optional[Plan] = None
            for p_dict in dec_dict.get("plans", []):
                if p_dict.get("plan_id") == chosen_plan_id:
                    chosen_plan_obj = Plan(**p_dict)
                    break

            ev_ctx = dec_dict.get("ev", {})
            sim_dt = datetime.fromisoformat(dec_dict.get("sim_time", "2026-10-10T18:00").replace("Z", "+00:00"))
            hour_of_day = sim_dt.hour + (sim_dt.minute / 60.0)

            context_x = extract_context_features(
                ev_context=ev_ctx,
                user_state={},
                hour_of_day=hour_of_day,
                grid_stress=0.75,
            )

            phi = build_feature_vector(
                context_x=context_x,
                frame=frame,
                timing=timing,
                plan=chosen_plan_obj,
            )
            phi_batch.append(phi)
            reward_batch.append(reward)
        except Exception as ex:
            logger.warning("Could not reconstruct phi for decision %s: %s", d_id, ex)

    # Persist updated decision records
    if updated_records:
        store.put_decisions(updated_records)

    # Update LinTS contextual bandit posterior
    if phi_batch and reward_batch:
        Phi = np.vstack(phi_batch)
        r = np.array(reward_batch, dtype=float)
        exp_ver = bandit.version
        bandit.update(Phi, r)
        store.put_model("lints_persuasion", bandit.get_state(), expected_version=exp_ver)

    mean_rew = float(np.mean(reward_batch)) if reward_batch else 0.0
    return {
        "updated_count": len(updated_records),
        "total_reward": round(float(sum(reward_batch)), 4),
        "mean_reward": round(mean_rew, 4),
        "bandit_version": bandit.version,
    }


def create_pipeline_policy(
    store: Optional[StateStore] = None,
    bandit: Optional[LinTS] = None,
    run_id: str = "b4_gridnudge",
    apply_allocation: bool = True,
) -> Callable[[Any], List[Dict[str, Any]]]:
    """Create a digital twin compatible policy callback for B4 GridNudge.

    Returns:
        Callable policy_fn(world: World) -> List[Dict[str, Any]]
    """
    if store is None:
        store = InMemoryStore()
    if bandit is None:
        bandit = LinTS(seed=42)

    def policy_fn(world: Any) -> List[Dict[str, Any]]:
        # 1. First process any closed outcomes from previous steps
        closed_outcomes = world.pop_outcomes()
        if closed_outcomes:
            process_outcomes(closed_outcomes, store=store, bandit=bandit)

        # 2. Get plugged candidate EVs
        candidates = world.candidates()
        if not candidates:
            return []

        grid_st = world.grid_state()

        # Build request payload
        cand_payload = []
        for c in candidates:
            cand_payload.append({
                "user_id": c["user_id"],
                "ev": {
                    "battery_kwh": c["battery_kwh"],
                    "current_soc": c["soc"],
                    "charger_kw": c["charger_kw"],
                },
                "trip": {
                    "commute_km": 30.0,
                    "departure_step": c.get("departure_step"),
                },
                "context": {
                    "archetype": c["archetype"],
                    "fatigue": c["fatigue"],
                    "last_frame": c.get("last_frame", "none"),
                },
            })

        request = {
            "run_id": run_id,
            "sim_time": world.current_time.isoformat(),
            "grid_forecast": {
                "feeder_load_mw": grid_st.get("feeder_load_mw", 6.0),
                "capacity_mw": 12.0,
                "grid_stress": grid_st.get("grid_stress", 0.5),
            },
            "candidates": cand_payload,
        }

        # Execute decision pipeline
        decisions = decide_batch(
            request=request,
            store=store,
            bandit=bandit,
            render_llm=False,
            apply_allocation=apply_allocation,
        )

        # Convert active decisions to format required by world.apply_decisions()
        applied_decisions: List[Dict[str, Any]] = []
        for d in decisions:
            if d.allocation.selected and d.persuasion.frame != "none" and d.persuasion.chosen_plan:
                # Find chosen plan object
                plan_dict = {"type": "delay"}
                savings = 65.0
                delay_hrs = 3.5
                for p in d.plans:
                    if p.plan_id == d.persuasion.chosen_plan:
                        plan_dict = p.model_dump()
                        savings = float(p.outcomes.get("cost_saving_inr", 65.0))
                        break

                applied_decisions.append({
                    "decision_id": d.decision_id,
                    "user_id": int(d.user_id),
                    "plan": plan_dict,
                    "frame": d.persuasion.frame,
                    "timing": d.persuasion.timing or "at_plug_in",
                    "savings_inr": savings,
                    "delay_hours": delay_hrs,
                })

        return applied_decisions

    return policy_fn
