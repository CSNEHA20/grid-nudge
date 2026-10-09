"""Fatigue state management and Bayesian archetype posterior updating.

Maintains per-user fatigue, daily notification counters, repeat-frame tracking,
and updates driver archetype posterior beliefs using the learner's own likelihood model.
"""

from typing import Any, Dict, List, Optional
import numpy as np

ARCHETYPES = [
    "price_sensitive",
    "eco_motivated",
    "convenience",
    "routine_locked",
    "fatigue_prone",
]

DEFAULT_PRIOR = np.array([0.30, 0.15, 0.20, 0.25, 0.10], dtype=float)

# Learner's own simplified likelihood table P(adopt | archetype, frame)
# (Separated from the digital twin's hidden ground truth per AGENTS.md Section 8)
LEARNER_LIKELIHOOD: Dict[str, Dict[str, float]] = {
    "cost": {
        "price_sensitive": 0.75,
        "eco_motivated": 0.35,
        "convenience": 0.40,
        "routine_locked": 0.15,
        "fatigue_prone": 0.45,
    },
    "green": {
        "price_sensitive": 0.20,
        "eco_motivated": 0.65,
        "convenience": 0.25,
        "routine_locked": 0.10,
        "fatigue_prone": 0.20,
    },
    "battery": {
        "price_sensitive": 0.40,
        "eco_motivated": 0.45,
        "convenience": 0.35,
        "routine_locked": 0.15,
        "fatigue_prone": 0.30,
    },
    "convenience": {
        "price_sensitive": 0.30,
        "eco_motivated": 0.25,
        "convenience": 0.70,
        "routine_locked": 0.20,
        "fatigue_prone": 0.35,
    },
    "reassurance": {
        "price_sensitive": 0.30,
        "eco_motivated": 0.30,
        "convenience": 0.45,
        "routine_locked": 0.20,
        "fatigue_prone": 0.40,
    },
}


def update_archetype_posterior(
    current_posterior: Optional[List[float]],
    frame: str,
    adopted: bool,
) -> List[float]:
    """Update driver archetype posterior probabilities using Bayes' rule.

    Args:
        current_posterior: Current 5-element probability distribution, or None for prior.
        frame: The persuasion frame delivered to the user (e.g. 'cost', 'green').
        adopted: Whether the user adopted the plan (True) or ignored (False).

    Returns:
        Updated normalized 5-element probability distribution list.
    """
    if current_posterior is None or len(current_posterior) != len(ARCHETYPES):
        prior = DEFAULT_PRIOR.copy()
    else:
        prior = np.array(current_posterior, dtype=float)
        prior = prior / max(1e-9, np.sum(prior))

    if frame not in LEARNER_LIKELIHOOD:
        return prior.tolist()

    likelihood_dict = LEARNER_LIKELIHOOD[frame]
    likelihoods = np.array([likelihood_dict[arch] for arch in ARCHETYPES], dtype=float)

    if not adopted:
        likelihoods = 1.0 - likelihoods

    # Unnormalized posterior
    unnorm = prior * likelihoods
    sum_unnorm = np.sum(unnorm)

    if sum_unnorm > 1e-9:
        posterior = unnorm / sum_unnorm
    else:
        posterior = prior

    return [round(float(p), 4) for p in posterior]


def decay_user_fatigue(
    fatigue: float,
    decay_rate: float = 0.70,
) -> float:
    """Decay fatigue score by daily multiplier."""
    return round(float(max(0.0, fatigue * decay_rate)), 3)


def update_fatigue_after_nudge(
    fatigue: float,
    is_repeat_frame: bool = False,
    increment: float = 1.0,
    repeat_penalty: float = 0.5,
) -> float:
    """Increment user fatigue after receiving a nudge, adding penalty for repeating the same frame."""
    penalty = repeat_penalty if is_repeat_frame else 0.0
    return round(float(fatigue + increment + penalty), 3)


def record_user_interaction(
    user_state: Dict[str, Any],
    nudged: bool,
    frame: Optional[str] = None,
    adopted: Optional[bool] = None,
    decay_rate: float = 0.70,
) -> Dict[str, Any]:
    """Update in-memory user state after an interaction round.

    Args:
        user_state: Current state dictionary.
        nudged: True if a notification was actually sent.
        frame: Message frame delivered, if nudged.
        adopted: Observed user adoption, if outcome closed.
        decay_rate: Fatigue daily retention rate.

    Returns:
        Updated user state dictionary.
    """
    state = dict(user_state)

    curr_fatigue = float(state.get("fatigue", 0.0))
    if nudged:
        # Increment fatigue when nudged
        state["fatigue"] = round(curr_fatigue + 1.0, 3)
        state["nudges_today"] = int(state.get("nudges_today", 0)) + 1
        state["last_frame"] = frame
    else:
        # Gentle passive recovery when silent
        state["fatigue"] = decay_user_fatigue(curr_fatigue, decay_rate=0.95)

    if adopted is not None and frame is not None and frame != "none":
        # Update ignore rate history
        total_nudges = int(state.get("total_nudges", 0)) + 1
        total_ignores = int(state.get("total_ignores", 0)) + (0 if adopted else 1)
        state["total_nudges"] = total_nudges
        state["total_ignores"] = total_ignores
        state["ignore_rate"] = round(total_ignores / max(1, total_nudges), 3)

        # Update archetype posterior
        curr_post = state.get("archetype_posterior")
        state["archetype_posterior"] = update_archetype_posterior(curr_post, frame, adopted)

    return state
