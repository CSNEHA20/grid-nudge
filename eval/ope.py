"""Doubly-robust (DR) and Inverse Propensity Scoring (IPS) Off-Policy Evaluation (OPE).

Evaluates candidate counterfactual policies against logged bandit trajectories
(context, action, propensity, reward) without deploying to the live environment.
"""

from typing import Any, Callable, Dict, List, Tuple
import numpy as np


def inverse_propensity_scoring(
    logged_outcomes: List[Dict[str, Any]],
    target_policy_fn: Callable[[Dict[str, Any]], str],
    clip_min: float = 0.02,
    clip_max: float = 50.0,
) -> Tuple[float, float, float]:
    """Compute IPS policy value estimate with 95% confidence intervals.

    Returns:
        Tuple of (estimated_value, ci_low, ci_high).
    """
    if not logged_outcomes:
        return 0.0, 0.0, 0.0

    weights = []
    values = []

    for item in logged_outcomes:
        action = item.get("action") or item.get("plan_type", "none")
        propensity = max(clip_min, float(item.get("propensity", 0.2)))
        reward = float(item.get("reward") or item.get("realized_value", 0.0))
        target_action = target_policy_fn(item)

        # Importance weight w = pi(a|x) / p_logged(a|x)
        w = (1.0 / propensity) if action == target_action else 0.0
        w = min(clip_max, w)

        weights.append(w)
        values.append(w * reward)

    val_arr = np.array(values)
    mean_val = float(np.mean(val_arr))
    stderr = float(np.std(val_arr, ddof=1) / np.sqrt(len(val_arr))) if len(val_arr) > 1 else 0.0

    ci_low = max(0.0, mean_val - 1.96 * stderr)
    ci_high = mean_val + 1.96 * stderr
    return round(mean_val, 4), round(ci_low, 4), round(ci_high, 4)


def doubly_robust_evaluation(
    logged_outcomes: List[Dict[str, Any]],
    target_policy_fn: Callable[[Dict[str, Any]], str],
    direct_model_fn: Callable[[Dict[str, Any], str], float],
    clip_min: float = 0.02,
    clip_max: float = 50.0,
) -> Tuple[float, float, float]:
    """Compute Doubly Robust (DR) off-policy value estimate combining IPS and direct regression model.

    DR is unbiased if either the propensity model or the direct reward model is correctly specified.

    Returns:
        Tuple of (dr_value, ci_low, ci_high).
    """
    if not logged_outcomes:
        return 0.0, 0.0, 0.0

    dr_values = []

    for item in logged_outcomes:
        action = item.get("action") or item.get("plan_type", "none")
        propensity = max(clip_min, float(item.get("propensity", 0.2)))
        reward = float(item.get("reward") or item.get("realized_value", 0.0))
        target_action = target_policy_fn(item)

        # Direct model predicted reward under target action and logged action
        pred_target = direct_model_fn(item, target_action)
        pred_logged = direct_model_fn(item, action)

        # Importance weight
        w = (1.0 / propensity) if action == target_action else 0.0
        w = min(clip_max, w)

        # Doubly robust estimator: pred_target + w * (reward - pred_logged)
        dr_item = pred_target + w * (reward - pred_logged)
        dr_values.append(dr_item)

    arr = np.array(dr_values)
    mean_val = float(np.mean(arr))
    stderr = float(np.std(arr, ddof=1) / np.sqrt(len(arr))) if len(arr) > 1 else 0.0

    ci_low = round(float(mean_val - 1.96 * stderr), 4)
    ci_high = round(float(mean_val + 1.96 * stderr), 4)
    return round(mean_val, 4), ci_low, ci_high
