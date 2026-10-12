"""Unit tests for LinTS dimension safety and graceful state migration.

Validates:
1. LinTS.load_state raises ValueError when stored A or b dimension does not match bandit dimension.
2. decide_batch catches incompatible model dimensions from store and gracefully falls back to fresh bandit.
3. learn_outcomes catches incompatible model dimensions from store and gracefully falls back to fresh bandit.
"""

import numpy as np
import pytest

from gridnudge.persuasion.features import FEATURE_DIM
from gridnudge.persuasion.lints import LinTS
from gridnudge.pipeline import decide_batch, process_outcomes
from gridnudge.state import InMemoryStore


def test_lints_dimension_guard_raises_on_mismatch():
    """LinTS.load_state must raise ValueError when matrix A shape != (d, d)."""
    bandit = LinTS(d=FEATURE_DIM, seed=42)

    # Legacy 121-dimensional state
    stale_dim = 121
    stale_state = {
        "d": stale_dim,
        "lam": 1.0,
        "v": 0.08,
        "gamma": 0.999,
        "A": np.eye(stale_dim).tolist(),
        "b": np.zeros(stale_dim).tolist(),
        "update_count": 10,
        "version": 2,
    }

    with pytest.raises(ValueError, match="does not match"):
        bandit.load_state(stale_state)


def test_lints_dimension_guard_raises_on_b_mismatch():
    """LinTS.load_state must raise ValueError when vector b shape != (d,)."""
    bandit = LinTS(d=FEATURE_DIM, seed=42)

    invalid_state = {
        "d": FEATURE_DIM,
        "lam": 1.0,
        "v": 0.08,
        "gamma": 0.999,
        "A": np.eye(FEATURE_DIM).tolist(),
        "b": np.zeros(FEATURE_DIM - 1).tolist(),
        "update_count": 5,
        "version": 1,
    }

    with pytest.raises(ValueError, match="Stored b vector shape"):
        bandit.load_state(invalid_state)


def test_lints_dimension_guard_raises_on_missing_fields():
    """LinTS.load_state must raise ValueError when A or b is missing."""
    bandit = LinTS(d=FEATURE_DIM, seed=42)

    with pytest.raises(ValueError, match="missing required"):
        bandit.load_state({"d": FEATURE_DIM})


def test_decide_batch_gracefully_recovers_from_stale_model():
    """decide_batch must not crash when store has a stale dimension model, falling back to fresh bandit."""
    store = InMemoryStore()
    stale_dim = 121
    stale_state = {
        "d": stale_dim,
        "lam": 1.0,
        "v": 0.08,
        "gamma": 0.999,
        "A": np.eye(stale_dim).tolist(),
        "b": np.zeros(stale_dim).tolist(),
        "update_count": 50,
        "version": 5,
    }
    store.put_model("lints_persuasion", stale_state, expected_version=0)

    request = {
        "sim_time": "2026-10-10T18:00:00",
        "grid": {"feeder_load_mw": 8.0, "capacity_mw": 12.0},
        "candidates": [
            {
                "user_id": "u_test_dim",
                "ev": {
                    "battery_capacity_kwh": 60.0,
                    "soc": 0.45,
                    "target_soc": 0.85,
                    "home_charger_kw": 7.4,
                },
                "trip": {
                    "next_trip_distance_km": 30.0,
                    "departure_time": "2026-10-11T08:00:00",
                },
            }
        ],
    }

    decisions = decide_batch(request=request, store=store)
    assert len(decisions) == 1
    assert decisions[0].decision_id is not None


def test_process_outcomes_gracefully_recovers_from_stale_model():
    """process_outcomes must not crash when store has a stale dimension model, falling back to fresh bandit."""
    store = InMemoryStore()
    stale_dim = 121
    stale_state = {
        "d": stale_dim,
        "lam": 1.0,
        "v": 0.08,
        "gamma": 0.999,
        "A": np.eye(stale_dim).tolist(),
        "b": np.zeros(stale_dim).tolist(),
        "update_count": 50,
        "version": 5,
    }
    store.put_model("lints_persuasion", stale_state, expected_version=0)

    summary = process_outcomes(outcomes=[], store=store)
    assert summary["updated_count"] == 0
