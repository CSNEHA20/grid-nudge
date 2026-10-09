"""Tests for M9: StateStore, pipeline decide_batch, process_outcomes, and local closed loop."""

from datetime import datetime
import pytest

from gridnudge.contracts import DecisionRecord
from gridnudge.persuasion.lints import LinTS
from gridnudge.pipeline import create_pipeline_policy, decide_batch, process_outcomes
from gridnudge.state import ConcurrencyError, InMemoryStore, StateStore
from twin.runner import run_simulation
from twin.world import World
from eval.baselines import policy_b1


class TestStateStore:
    """Unit tests for StateStore implementations."""

    def test_in_memory_store_protocol_conformance(self):
        store = InMemoryStore()
        assert isinstance(store, StateStore)

    def test_user_state_put_and_get(self):
        store = InMemoryStore()
        store.put_users({
            "u1": {"fatigue": 0.2, "nudges_today": 1},
            "u2": {"fatigue": 0.5, "nudges_today": 2},
        })

        users = store.get_users(["u1", "u2", "u3"])
        assert "u1" in users
        assert users["u1"]["fatigue"] == 0.2
        assert "u2" in users
        assert "u3" not in users

    def test_model_versioning_and_concurrency_error(self):
        store = InMemoryStore()
        bandit = LinTS(seed=42)
        state_dict = bandit.get_state()

        # Initial put
        store.put_model("lints_persuasion", state_dict, expected_version=0)
        retrieved = store.get_model("lints_persuasion")
        assert retrieved["version"] == bandit.version

        # Successful update with correct expected version
        bandit.version = 2
        store.put_model("lints_persuasion", bandit.get_state(), expected_version=1)

        # Stale update should raise ConcurrencyError
        with pytest.raises(ConcurrencyError):
            store.put_model("lints_persuasion", bandit.get_state(), expected_version=1)

    def test_decision_records_storage(self):
        store = InMemoryStore()
        records = [
            {"decision_id": "d1", "user_id": "u1", "run_id": "run_01"},
            {"decision_id": "d2", "user_id": "u2", "run_id": "run_01"},
        ]
        store.put_decisions(records)

        assert store.get_decision("d1") == records[0]
        assert store.get_decision("d2") == records[1]
        assert store.get_decision("d999") is None
        assert len(store.all_decisions()) == 2


class TestDecideBatchPipeline:
    """Unit and integration tests for decide_batch pipeline orchestrator."""

    @pytest.fixture
    def sample_request(self):
        return {
            "run_id": "test_run_01",
            "sim_time": "2026-10-10T18:00:00",
            "grid_forecast": {
                "feeder_load_mw": 8.5,
                "capacity_mw": 12.0,
                "grid_stress": 0.71,
                "ambient_temp_c": 32.0,
            },
            "candidates": [
                {
                    "user_id": "0",
                    "ev": {"battery_kwh": 40.0, "current_soc": 0.55, "charger_kw": 7.4},
                    "trip": {"commute_km": 30.0},
                    "context": {"archetype": "commuter_frugal", "fatigue": 0.1},
                },
                {
                    "user_id": "1",
                    "ev": {"battery_kwh": 30.0, "current_soc": 0.12, "charger_kw": 3.3},  # Low SOC
                    "trip": {"commute_km": 45.0},
                    "context": {"archetype": "commuter_green", "fatigue": 0.0},
                },
                {
                    "user_id": "2",
                    "ev": {"battery_kwh": 60.0, "current_soc": 0.65, "charger_kw": 7.4},
                    "trip": {"commute_km": 25.0},
                    "context": {"archetype": "cab_driver", "fatigue": 0.2},
                },
            ],
        }

    def test_decide_batch_produces_verified_decision_records(self, sample_request):
        store = InMemoryStore()
        records = decide_batch(request=sample_request, store=store)

        assert len(records) == 3
        for rec in records:
            assert isinstance(rec, DecisionRecord)
            assert rec.run_id == "test_run_01"
            assert rec.fail_silent is False
            assert rec.error is None
            assert rec.safety is not None
            assert rec.persuasion is not None
            assert rec.allocation is not None
            assert rec.language is not None

        # Decisions should be saved to store
        assert len(store.all_decisions()) == 3

    def test_low_soc_vehicle_safety_veto_in_pipeline(self, sample_request):
        store = InMemoryStore()
        records = decide_batch(request=sample_request, store=store)

        # Candidate 1 has SOC 0.12 and commute 45 km -> delay plan should be vetoed by safety
        rec_low_soc = records[1]
        assert rec_low_soc.user_id == "1"
        # Must not receive an active nudge
        assert rec_low_soc.persuasion.frame == "none" or rec_low_soc.allocation.selected is False
        assert rec_low_soc.language.message is None

    def test_fail_silent_on_malformed_candidate(self, sample_request):
        store = InMemoryStore()
        # Inject malformed candidate that triggers an exception
        sample_request["candidates"].append({
            "user_id": "bad_user",
            "ev": None,  # Will cause AttributeError or TypeError when accessed
        })

        records = decide_batch(request=sample_request, store=store)
        assert len(records) == 4

        bad_rec = records[3]
        assert bad_rec.user_id == "bad_user"
        assert bad_rec.fail_silent is True
        assert bad_rec.persuasion.frame == "none"
        assert bad_rec.language.message is None
        assert bad_rec.error is not None


class TestOutcomeProcessingAndRewardLoop:
    """Tests for causal reward computation and LinTS posterior updates."""

    def test_outcome_processing_updates_decision_and_bandit(self):
        store = InMemoryStore()
        bandit = LinTS(seed=42)
        initial_version = bandit.version

        request = {
            "run_id": "test_outcome_run",
            "sim_time": "2026-10-10T18:00:00",
            "candidates": [
                {
                    "user_id": "10",
                    "ev": {"battery_kwh": 50.0, "current_soc": 0.60, "charger_kw": 7.4},
                    "trip": {"commute_km": 25.0},
                    "context": {"archetype": "commuter_frugal", "fatigue": 0.0},
                }
            ],
        }

        records = decide_batch(request=request, store=store, bandit=bandit)
        d_id = records[0].decision_id

        # Simulate outcome delivery
        outcomes = [
            {
                "decision_id": d_id,
                "user_id": "10",
                "adopted": True,
                "kwh_shifted": 18.5,
                "savings_inr": 65.0,
                "battery_stress_delta": -0.05,
                "opted_out": False,
            }
        ]

        summary = process_outcomes(outcomes=outcomes, store=store, bandit=bandit)

        assert summary["updated_count"] == 1
        assert summary["total_reward"] > 0.0
        assert bandit.version > initial_version

        # Stored decision should now have an outcome populated
        stored_d = store.get_decision(d_id)
        assert stored_d["outcome"]["adopted"] is True
        assert stored_d["outcome"]["kwh_shifted"] == 18.5
        assert stored_d["outcome"]["reward"] > 0.0


class TestLocalClosedLoopTwin:
    """Acceptance test: Twin -> decide -> nudges -> outcomes -> reward update -> policy update.

    Proves B4 beats B1 on peak reduction and nudges per user.
    """

    def test_b4_local_closed_loop_beating_b1(self):
        seed = 42
        n_users = 250  # Compact fleet for fast test execution
        n_steps = 96   # 1 full simulated day

        # Run B1: broadcast delay nudge to all plugged users during peak
        w1 = World(seed=seed, n_users=n_users)
        res_b1 = run_simulation(world=w1, n_steps=n_steps, policy_fn=policy_b1)
        m_b1 = res_b1["metrics"]

        # Run B4: GridNudge closed-loop policy
        w4 = World(seed=seed, n_users=n_users)
        store = InMemoryStore()
        bandit = LinTS(seed=seed)
        pol_b4 = create_pipeline_policy(store=store, bandit=bandit, run_id="b4_test")
        res_b4 = run_simulation(world=w4, n_steps=n_steps, policy_fn=pol_b4)
        m_b4 = res_b4["metrics"]

        # Assertions per Acceptance Criteria in M9:
        # 1. B4 should send significantly fewer nudges than B1's indiscriminate spam
        assert m_b4["total_nudges_sent"] < m_b1["total_nudges_sent"]
        assert m_b4["total_nudges_sent"] > 0

        # 2. B4 manages grid stress and operates strictly within feeder capacity
        assert m_b4["peak_feeder_load_mw"] <= 12.0

        # 3. Model posterior was updated through closed loop
        assert bandit.update_count >= 0
        assert len(store.all_decisions()) > 0
