"""Tests for M6 Persuasion module: LinTS contextual bandit, uplift, fatigue, and archetype modeling.

Validates the first-class 'none' action, learned silence, paired uplift calculation,
Bayesian archetype updating, and causal reward evaluation.
"""

import numpy as np
import pytest

from gridnudge.contracts import Persuasion, Plan
from gridnudge.persuasion.fatigue import (
    decay_user_fatigue,
    record_user_interaction,
    update_archetype_posterior,
)
from gridnudge.persuasion.features import (
    FEATURE_DIM,
    build_feature_vector,
    extract_context_features,
)
from gridnudge.persuasion.lints import LinTS
from gridnudge.persuasion.uplift import (
    compute_causal_reward,
    enumerate_candidate_actions,
    select_persuasion_action,
)


class TestPersuasionEngine:
    """Tests for contextual bandit action selection and uplift learning."""

    @pytest.fixture
    def safe_plans(self):
        """Sample safe charging plans passed to bandit."""
        return [
            Plan(
                plan_id="plan_default_01",
                type="default",
                start="2026-10-10T19:00:00+05:30",
                kw=7.4,
                where="home",
                outcomes={
                    "cost_inr": 220.0,
                    "journey_conf_lb": 0.96,
                    "grid_value": -0.8,
                    "battery_stress_delta": 0.0,
                    "wait_min": 0.0,
                },
            ),
            Plan(
                plan_id="plan_delay_01",
                type="delay",
                start="2026-10-10T23:00:00+05:30",
                kw=7.4,
                where="home",
                outcomes={
                    "cost_inr": 150.0,
                    "journey_conf_lb": 0.94,
                    "grid_value": 1.4,
                    "battery_stress_delta": -0.05,
                    "wait_min": 0.0,
                },
            ),
        ]

    def test_features_dimension_and_interactions(self, safe_plans):
        """Feature vector phi(x, a) must have fixed deterministic dimension."""
        ev = {"current_soc": 0.35, "commute_km": 40.0}
        user_state = {"fatigue": 0.5, "nudges_today": 1}
        x = extract_context_features(ev, user_state, hour_of_day=19.0, grid_stress=0.88)
        assert len(x) == 15

        phi = build_feature_vector(
            context_x=x,
            frame="cost",
            timing="at_plug_in",
            plan=safe_plans[1],
            default_cost=220.0,
        )
        assert len(phi) == FEATURE_DIM

    def test_first_class_none_action_exists(self, safe_plans):
        """Action enumeration must include first-class 'none' action as action 0."""
        actions = enumerate_candidate_actions(safe_plans)
        assert len(actions) > 1
        assert actions[0]["frame"] == "none"
        assert actions[0]["plan"] is None

    def test_global_holdout_always_receives_none(self, safe_plans):
        """Users in the 5% global holdout group must always receive the 'none' action."""
        bandit = LinTS(seed=42)
        persuasion, _, _ = select_persuasion_action(
            user_id="user_20",  # 20 % 20 == 0 -> holdout
            ev_context={"current_soc": 0.3},
            user_state={},
            safe_plans=safe_plans,
            bandit=bandit,
            hour_of_day=19.0,
            grid_stress=0.85,
        )
        assert isinstance(persuasion, Persuasion)
        assert persuasion.frame == "none"
        assert persuasion.chosen_plan is None
        assert persuasion.propensity == 1.0

    def test_propensity_and_uplift_bounds(self, safe_plans):
        """Propensities must be in (0, 1] and uplift metrics strictly numeric."""
        bandit = LinTS(seed=123)
        persuasion, phi, act = select_persuasion_action(
            user_id="user_21",  # Non-holdout
            ev_context={"current_soc": 0.3, "target_soc": 0.9},
            user_state={"fatigue": 0.0},
            safe_plans=safe_plans,
            bandit=bandit,
            hour_of_day=19.0,
            grid_stress=0.90,
            m_samples=32,
        )
        assert 0.0 < persuasion.propensity <= 1.0
        assert isinstance(persuasion.uplift_mean, float)
        assert isinstance(persuasion.uplift_p10, float)
        assert len(phi) == FEATURE_DIM

    def test_lints_posterior_update_and_serialization(self):
        """LinTS precision matrix A and b update with observed rewards and serialize cleanly."""
        bandit = LinTS(d=FEATURE_DIM, seed=10)
        phi = np.ones((2, FEATURE_DIM))
        rewards = np.array([1.5, 2.0])

        initial_count = bandit.update_count
        bandit.update(phi, rewards)

        assert bandit.update_count == initial_count + 2
        assert bandit.version > 1

        state = bandit.get_state()
        new_bandit = LinTS(d=FEATURE_DIM)
        new_bandit.load_state(state)
        assert new_bandit.update_count == bandit.update_count
        assert np.allclose(new_bandit.b, bandit.b)

    def test_bayesian_archetype_posterior_update(self):
        """Adopting a cost-framed nudge shifts belief toward price_sensitive archetype."""
        prior = [0.30, 0.15, 0.20, 0.25, 0.10]
        # User adopted cost frame
        post = update_archetype_posterior(prior, frame="cost", adopted=True)
        assert len(post) == 5
        assert np.isclose(sum(post), 1.0)
        # Price sensitive prob increases
        assert post[0] > prior[0]

    def test_fatigue_decay_and_interaction_recording(self):
        """Fatigue decays when silent, increases when nudged."""
        decayed = decay_user_fatigue(2.0, decay_rate=0.70)
        assert decayed == 1.4

        state = {"fatigue": 1.0, "nudges_today": 1}
        # Nudge sent
        new_state = record_user_interaction(state, nudged=True, frame="cost")
        assert new_state["fatigue"] == 2.0
        assert new_state["nudges_today"] == 2
        assert new_state["last_frame"] == "cost"

    def test_causal_reward_calculation(self):
        """Reward increases with shifted kWh & savings, penalizes battery stress & opt-out."""
        good_reward = compute_causal_reward(
            kwh_shifted=15.0,
            savings_inr=50.0,
            grid_value=1.5,
            battery_stress_delta=-0.05,
            fatigue_score=0.2,
            opted_out=False,
        )
        bad_reward = compute_causal_reward(
            kwh_shifted=0.0,
            savings_inr=0.0,
            grid_value=-0.5,
            battery_stress_delta=0.10,
            fatigue_score=1.5,
            opted_out=True,
        )
        assert good_reward > bad_reward
