"""Feature extraction for uplift-aware contextual bandit.

Constructs feature vectors phi(x, a) encoding driver state, battery context,
diurnal time, grid stress, action frames, timings, and interaction terms.
"""

from typing import Any, Dict, List, Optional
import numpy as np

from gridnudge.contracts import Frame, Plan, Timing

ALL_FRAMES: List[Frame] = ["none", "cost", "green", "battery", "convenience", "reassurance"]
ALL_TIMINGS: List[Timing] = ["at_plug_in", "plus_30m", "pre_peak"]
ALL_PLAN_TYPES = ["default", "delay", "slow_charge", "top_up_now", "relocate"]

ARCHETYPES = ["price_sensitive", "eco_motivated", "convenience", "routine_locked", "fatigue_prone"]


def extract_context_features(
    ev_context: Dict[str, Any],
    user_state: Dict[str, Any],
    hour_of_day: float,
    grid_stress: float,
    ambient_temp_c: float = 30.0,
) -> np.ndarray:
    """Extract 15-dimensional continuous context vector x.

    Features:
    0: Bias (1.0)
    1: Current SOC [0.0, 1.0]
    2: Target SOC [0.0, 1.0]
    3: Commute distance scaled (commute_km / 100.0)
    4: Hours until departure scaled (hours / 16.0)
    5: Diurnal hour sin component: sin(2 * pi * hour / 24)
    6: Diurnal hour cos component: cos(2 * pi * hour / 24)
    7: Grid stress ratio (load / capacity)
    8: Ambient temperature scaled ((temp - 25) / 20.0)
    9: Current user fatigue score [0.0, 3.0] / 3.0
    10: Nudges received today (0 to 3) / 3.0
    11: Recent ignore rate [0.0, 1.0]
    12-14: Archetype posterior probabilities (first 3 free dims of K=5)
    """
    soc = float(ev_context.get("current_soc", 0.50))
    target_soc = float(ev_context.get("target_soc", 0.90))
    commute_km = float(ev_context.get("commute_km", 40.0)) / 100.0
    hours_dep = float(ev_context.get("hours_until_departure", 8.0)) / 16.0

    h_rad = (float(hour_of_day) % 24.0) * (2.0 * np.pi / 24.0)
    hour_sin = np.sin(h_rad)
    hour_cos = np.cos(h_rad)

    stress = float(grid_stress)
    temp_scaled = (float(ambient_temp_c) - 25.0) / 20.0

    fatigue = float(user_state.get("fatigue", 0.0)) / 3.0
    nudges_today = float(user_state.get("nudges_today", 0)) / 3.0
    ignore_rate = float(user_state.get("ignore_rate", 0.0))

    # Archetype posterior (defaults to prior if missing)
    post = user_state.get("archetype_posterior", [0.30, 0.15, 0.20, 0.25, 0.10])
    arch_0 = float(post[0])
    arch_1 = float(post[1])
    arch_2 = float(post[2])

    features = np.array(
        [
            1.0,
            soc,
            target_soc,
            commute_km,
            hours_dep,
            hour_sin,
            hour_cos,
            stress,
            temp_scaled,
            fatigue,
            nudges_today,
            ignore_rate,
            arch_0,
            arch_1,
            arch_2,
        ],
        dtype=float,
    )
    return features


def extract_action_vector(
    frame: Frame,
    timing: Optional[Timing],
    plan: Optional[Plan],
    default_cost: float = 200.0,
) -> np.ndarray:
    """Extract action encoding vector: one-hot frame, timing, and plan type."""
    # 1. One-hot frame (6 dims: none, cost, green, battery, convenience, reassurance)
    frame_vec = np.zeros(len(ALL_FRAMES), dtype=float)
    if frame in ALL_FRAMES:
        frame_vec[ALL_FRAMES.index(frame)] = 1.0
    else:
        frame_vec[0] = 1.0  # Default to none

    # 2. One-hot timing (3 dims)
    timing_vec = np.zeros(len(ALL_TIMINGS), dtype=float)
    if timing in ALL_TIMINGS and frame != "none":
        timing_vec[ALL_TIMINGS.index(timing)] = 1.0

    # 3. One-hot plan type (5 dims)
    plan_vec = np.zeros(len(ALL_PLAN_TYPES), dtype=float)
    savings_scaled = 0.0
    if plan is not None and frame != "none":
        if plan.type in ALL_PLAN_TYPES:
            plan_vec[ALL_PLAN_TYPES.index(plan.type)] = 1.0
        cost = float(plan.outcomes.get("cost_inr", default_cost))
        savings_scaled = max(0.0, (default_cost - cost) / 100.0)

    # 4. Action-specific scalars (savings, delay, grid value)
    action_scalars = np.array([savings_scaled], dtype=float)

    return np.concatenate([frame_vec, timing_vec, plan_vec, action_scalars])


def build_feature_vector(
    context_x: np.ndarray,
    frame: Frame,
    timing: Optional[Timing],
    plan: Optional[Plan],
    default_cost: float = 200.0,
) -> np.ndarray:
    """Construct joint feature representation phi(x, a).

    Structure:
    - [1.0] (bias: 1)
    - Action vector: frame (6) + timing (3) + plan (5) + savings (1) = 15 dims
    - Context vector x: 15 dims
    - Interaction term: x tensor_product frame_onehot = 15 * 6 = 90 dims
    Total feature dimension d = 1 + 15 + 15 + 90 = 121 dimensions.
    """
    action_vec = extract_action_vector(frame, timing, plan, default_cost)
    frame_onehot = action_vec[: len(ALL_FRAMES)]  # first 6 dims

    # Outer product interaction between context and frame
    interaction = np.outer(context_x, frame_onehot).flatten()

    phi = np.concatenate([[1.0], action_vec, context_x, interaction])
    return phi.astype(float)


FEATURE_DIM = 121
