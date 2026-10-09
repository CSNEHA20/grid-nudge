"""Persuasion engine for GridNudge: Contextual bandit, uplift modeling, fatigue tracking, and Bayesian archetype estimation."""

from gridnudge.persuasion.fatigue import (
    ARCHETYPES,
    decay_user_fatigue,
    record_user_interaction,
    update_archetype_posterior,
)
from gridnudge.persuasion.features import (
    ALL_FRAMES,
    ALL_TIMINGS,
    FEATURE_DIM,
    build_feature_vector,
    extract_action_vector,
    extract_context_features,
)
from gridnudge.persuasion.lints import LinTS
from gridnudge.persuasion.uplift import (
    compute_causal_reward,
    enumerate_candidate_actions,
    select_persuasion_action,
)

__all__ = [
    "FEATURE_DIM",
    "ALL_FRAMES",
    "ALL_TIMINGS",
    "ARCHETYPES",
    "extract_context_features",
    "extract_action_vector",
    "build_feature_vector",
    "LinTS",
    "update_archetype_posterior",
    "decay_user_fatigue",
    "record_user_interaction",
    "compute_causal_reward",
    "enumerate_candidate_actions",
    "select_persuasion_action",
]
