"""Uplift estimation, Thompson Sampling action selection, and causal reward calculation.

Implements the persuasion decision engine for GridNudge:
- First-class "none" action for learned silence
- Paired uplift calculation (score(a) - score(none))
- Propensity logging P(a|x) mixed with epsilon-exploration
- Global holdout group (~5% of users)
- Realized causal reward computation
"""

from typing import Any, Dict, List, Tuple
import numpy as np

from gridnudge.contracts import Frame, Persuasion, Plan, Timing
from gridnudge.persuasion.features import (
    build_feature_vector,
    extract_context_features,
)
from gridnudge.persuasion.lints import LinTS


def compute_causal_reward(
    kwh_shifted: float,
    savings_inr: float,
    grid_value: float,
    battery_stress_delta: float,
    extra_wait_min: float = 0.0,
    fatigue_score: float = 0.0,
    opted_out: bool = False,
    w_g: float = 1.0,
    w_u: float = 0.02,
    w_b: float = 0.50,
    w_w: float = 0.02,
    w_f: float = 0.30,
    w_o: float = 5.0,
) -> float:
    """Compute realized causal reward metric.

    Formula (Guidance Section 9.6):
        r = w_g * grid_value * kwh_shifted
          + w_u * savings_inr
          + w_b * (-battery_stress_delta)
          - w_w * extra_wait_min
          - w_f * fatigue_score
          - w_o * (1.0 if opted_out else 0.0)

    Applied to both 'none' and active nudges so uplift is directly comparable.
    """
    opt_out_penalty = w_o if opted_out else 0.0

    r = (
        (w_g * grid_value * kwh_shifted)
        + (w_u * savings_inr)
        + (w_b * (-1.0 * battery_stress_delta))
        - (w_w * max(0.0, extra_wait_min))
        - (w_f * max(0.0, fatigue_score))
        - opt_out_penalty
    )
    return round(float(r), 4)


def enumerate_candidate_actions(
    safe_plans: List[Plan],
    default_cost: float = 200.0,
) -> List[Dict[str, Any]]:
    """Enumerate available persuasion actions: 'none' action + (plan x frame x timing)."""
    actions: List[Dict[str, Any]] = [
        {
            "action_id": "act_none",
            "frame": "none",
            "timing": None,
            "plan": None,
        }
    ]

    candidate_frames: List[Frame] = ["cost", "green", "battery", "convenience", "reassurance"]
    candidate_timings: List[Timing] = ["at_plug_in", "plus_30m", "pre_peak"]

    for plan in safe_plans:
        # For non-default shifting plans, evaluate frame x timing combinations
        if plan.type != "default":
            for frame in candidate_frames:
                for timing in candidate_timings:
                    actions.append(
                        {
                            "action_id": f"act_{plan.plan_id}_{frame}_{timing}",
                            "frame": frame,
                            "timing": timing,
                            "plan": plan,
                        }
                    )
        else:
            # Default plan can receive gentle convenience or reassurance nudges
            for frame in ["convenience", "reassurance"]:
                actions.append(
                    {
                        "action_id": f"act_{plan.plan_id}_{frame}_at_plug_in",
                        "frame": frame,
                        "timing": "at_plug_in",
                        "plan": plan,
                    }
                )

    return actions


def select_persuasion_action(
    user_id: str,
    ev_context: Dict[str, Any],
    user_state: Dict[str, Any],
    safe_plans: List[Plan],
    bandit: LinTS,
    hour_of_day: float,
    grid_stress: float,
    ambient_temp_c: float = 30.0,
    epsilon: float = 0.08,
    m_samples: int = 64,
    global_holdout_rate: float = 0.05,
) -> Tuple[Persuasion, np.ndarray, Dict[str, Any]]:
    """Select persuasion action using Linear Thompson Sampling and estimate uplift.

    Returns:
        Tuple of (Persuasion contract object, chosen feature vector phi, action metadata dict).
    """
    # 1. Global holdout check (~5% of users never nudged)
    try:
        user_num = int("".join(c for c in str(user_id) if c.isdigit()) or "0")
    except Exception:
        user_num = 0

    is_holdout = (user_num % 20 == 0) or user_state.get("holdout", False)

    context_x = extract_context_features(
        ev_context=ev_context,
        user_state=user_state,
        hour_of_day=hour_of_day,
        grid_stress=grid_stress,
        ambient_temp_c=ambient_temp_c,
    )

    actions = enumerate_candidate_actions(safe_plans)
    n_actions = len(actions)

    # 2. Build design matrix Phi for all candidate actions
    default_cost = 200.0
    for p in safe_plans:
        if p.type == "default":
            default_cost = float(p.outcomes.get("cost_inr", 200.0))
            break

    Phi = np.zeros((n_actions, bandit.d), dtype=float)
    for i, act in enumerate(actions):
        Phi[i] = build_feature_vector(
            context_x=context_x,
            frame=act["frame"],
            timing=act["timing"],
            plan=act["plan"],
            default_cost=default_cost,
        )

    # 3. Handle global holdout or empty safe plans
    if is_holdout or not safe_plans:
        persuasion = Persuasion(
            chosen_plan=None,
            frame="none",
            timing=None,
            uplift_mean=0.0,
            uplift_p10=0.0,
            propensity=1.0,
            explored=False,
        )
        return persuasion, Phi[0], actions[0]

    # 4. Draw m parameter vectors from LinTS posterior
    thetas = bandit.sample_theta(m=m_samples)  # Shape (m, d)
    scores = thetas @ Phi.T  # Shape (m, n_actions)

    # 5. Thompson Sampling action choice
    # Use draw 0 as the realization
    ts_chosen_idx = int(np.argmax(scores[0]))

    # Propensity estimation across all m posterior draws
    argmax_counts = np.bincount(np.argmax(scores, axis=1), minlength=n_actions)
    ts_prob = argmax_counts / float(m_samples)
    mixed_propensity = ((1.0 - epsilon) * ts_prob) + (epsilon / float(n_actions))

    # Epsilon exploration realization
    rng = bandit.rng
    if rng.uniform(0.0, 1.0) < epsilon:
        chosen_idx = int(rng.integers(0, n_actions))
        explored = True
    else:
        chosen_idx = ts_chosen_idx
        explored = False

    propensity_val = float(mixed_propensity[chosen_idx])

    # 6. Paired uplift estimation: score(a) - score(none)
    # Action 0 is 'none'
    paired_diff = scores[:, chosen_idx] - scores[:, 0]
    uplift_mean = float(np.mean(paired_diff))
    uplift_p10 = float(np.percentile(paired_diff, 10))

    chosen_act = actions[chosen_idx]
    chosen_plan = chosen_act["plan"]

    # 7. Action assignment:
    # If chosen action is none or no plan is associated, return none action
    if chosen_act["frame"] == "none" or chosen_plan is None:
        persuasion = Persuasion(
            chosen_plan=None,
            frame="none",
            timing=None,
            uplift_mean=round(uplift_mean, 4),
            uplift_p10=round(uplift_p10, 4),
            propensity=float(mixed_propensity[0]),
            explored=explored,
        )
        return persuasion, Phi[0], actions[0]

    persuasion = Persuasion(
        chosen_plan=chosen_plan.plan_id,
        frame=chosen_act["frame"],
        timing=chosen_act["timing"],
        uplift_mean=round(uplift_mean, 4),
        uplift_p10=round(uplift_p10, 4),
        propensity=round(propensity_val, 4),
        explored=explored,
    )

    return persuasion, Phi[chosen_idx], chosen_act
