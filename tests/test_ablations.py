"""Tests for Stage A ablations and Oracle benchmark policy (M11 / C6 / A4).

Validates:
- B4a (restricted to delay plans only)
- B4b (without fatigue features)
- Oracle (twin-informed theoretical upper bound policy)
- get_policy_by_name resolution
"""

import pytest

from eval.baselines import (
    create_policy_b4a,
    create_policy_b4b,
    create_policy_oracle,
    get_policy_by_name,
)
from twin.runner import run_simulation
from twin.world import World


class TestAblationsAndOracle:
    """Test suite for policy ablations and Oracle reference policy."""

    def test_policy_resolution_by_name(self):
        """get_policy_by_name must correctly resolve B4a, B4b, and Oracle."""
        assert callable(get_policy_by_name("B4A"))
        assert callable(get_policy_by_name("B4B"))
        assert callable(get_policy_by_name("ORACLE"))
        assert callable(get_policy_by_name("b4a_delay_only"))
        assert callable(get_policy_by_name("oracle_upper_bound"))

    def test_b4a_restricts_to_delay_plans_only(self):
        """B4a must only output 'delay' plans or 'default' (none), never slow_charge or relocate."""
        w = World(seed=42, n_users=100)
        pol_b4a = create_policy_b4a(seed=42)
        res = run_simulation(world=w, n_steps=96, policy_fn=pol_b4a)

        # Inspect all outcomes logged during simulation
        for outcome in w.all_outcomes:
            if outcome.get("is_nudged"):
                assert outcome.get("plan_type") == "delay", (
                    f"B4a emitted non-delay plan: {outcome.get('plan_type')}"
                )

    def test_b4b_runs_without_fatigue_features(self):
        """B4b runs cleanly and issues nudges with disabled fatigue features."""
        w = World(seed=42, n_users=100)
        pol_b4b = create_policy_b4b(seed=42)
        res = run_simulation(world=w, n_steps=96, policy_fn=pol_b4b)

        metrics = res["metrics"]
        assert metrics["total_nudges_sent"] > 0
        assert metrics["peak_feeder_load_mw"] <= 12.0

    def test_oracle_delivers_effective_peak_shaving_safely(self):
        """Oracle policy selects optimal frames for safe candidates and reduces peak."""
        w_b0 = World(seed=42, n_users=200)
        res_b0 = run_simulation(world=w_b0, n_steps=96)
        peak_b0 = res_b0["metrics"]["peak_feeder_load_mw"]

        w_oracle = World(seed=42, n_users=200)
        pol_oracle = create_policy_oracle(seed=42)
        res_oracle = run_simulation(world=w_oracle, n_steps=96, policy_fn=pol_oracle)
        peak_oracle = res_oracle["metrics"]["peak_feeder_load_mw"]

        assert peak_oracle < peak_b0
        assert res_oracle["metrics"]["total_nudges_sent"] > 0
