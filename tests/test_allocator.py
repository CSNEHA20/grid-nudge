"""Tests for M7 Fleet Allocator module.

Validates attention budget limits, shadow price calculation, daily frequency caps,
anti-herding staggering across 15-minute intervals, and feeder rebound peak prevention.
"""

from gridnudge.allocator import (
    allocate_fleet_nudges,
    compute_allocation_priority,
    find_safe_staggered_slot,
)
from gridnudge.contracts import Allocation, Persuasion, Plan


class TestFleetAllocator:
    """Tests for greedy fleet allocator under physical and attention constraints."""

    def make_candidate(
        self,
        user_id: str,
        uplift_p10: float = 0.25,
        grid_value: float = 1.2,
        kw: float = 7.4,
        nudges_today: int = 0,
        frame: str = "cost",
        preferred_start: str = "2026-10-10T23:00:00+05:30",
    ):
        """Helper to construct realistic test candidates."""
        plan = Plan(
            plan_id=f"plan_{user_id}",
            type="delay",
            start=preferred_start,
            kw=kw,
            where="home",
            outcomes={
                "cost_inr": 140.0,
                "journey_conf_lb": 0.94,
                "grid_value": grid_value,
                "battery_stress_delta": -0.04,
                "wait_min": 0.0,
            },
        )
        persuasion = Persuasion(
            chosen_plan=plan.plan_id,
            frame=frame,
            timing="at_plug_in",
            uplift_mean=uplift_p10 + 0.1,
            uplift_p10=uplift_p10,
            propensity=0.7,
            explored=False,
        )
        return {
            "candidate_id": user_id,
            "user_id": user_id,
            "persuasion": persuasion,
            "plan": plan,
            "user_state": {"nudges_today": nudges_today, "opted_out": False},
            "ev_context": {"battery_kwh": 40.0, "charger_kw": kw},
        }

    def test_allocator_respects_attention_budget_cap(self):
        """Number of selected nudges must not exceed the configured attention budget."""
        # 20 eligible candidates, but budget is only 8% of 100 plugged EVs = 8 nudges
        candidates = [self.make_candidate(f"user_{i}", uplift_p10=0.1 + i * 0.02) for i in range(20)]

        allocations = allocate_fleet_nudges(
            candidate_records=candidates,
            total_plugged_count=100,  # 8% of 100 = 8 nudges
            sim_time_iso="2026-10-10T19:00:00+05:30",
            budget_pct=0.08,
        )

        selected_count = sum(1 for a in allocations.values() if a.selected)
        assert selected_count == 8
        assert all(isinstance(a, Allocation) for a in allocations.values())

    def test_allocator_shadow_price_computation(self):
        """Shadow price reflects the marginal value of the last admitted candidate."""
        candidates = [self.make_candidate(f"user_{i}", uplift_p10=0.1 + i * 0.05) for i in range(10)]
        allocations = allocate_fleet_nudges(
            candidate_records=candidates,
            total_plugged_count=50,  # Budget = 4
            sim_time_iso="2026-10-10T19:00:00+05:30",
            budget_pct=0.08,
        )
        selected_allocs = [a for a in allocations.values() if a.selected]
        assert len(selected_allocs) == 4
        # All selected candidates receive the shadow price of the 4th accepted candidate
        assert selected_allocs[0].shadow_price > 0.0
        assert all(a.shadow_price == selected_allocs[0].shadow_price for a in selected_allocs)

    def test_allocator_respects_daily_nudge_cap(self):
        """Users who reached 3 nudges today must be rejected regardless of high priority."""
        capped_candidate = self.make_candidate(
            "user_capped",
            uplift_p10=0.99,  # Very high uplift!
            nudges_today=3,  # Reached daily cap
        )
        fresh_candidate = self.make_candidate(
            "user_fresh",
            uplift_p10=0.20,
            nudges_today=1,
        )
        allocations = allocate_fleet_nudges(
            candidate_records=[capped_candidate, fresh_candidate],
            total_plugged_count=100,
            sim_time_iso="2026-10-10T19:00:00+05:30",
        )
        assert allocations["user_capped"].selected is False
        assert allocations["user_fresh"].selected is True

    def test_anti_herding_staggers_charging_slots(self):
        """Anti-herding staggers assigned charging start slots across consecutive 15-min intervals."""
        # 10 candidates all targeting preferred start 23:00
        candidates = [
            self.make_candidate(f"user_{i}", preferred_start="2026-10-10T23:00:00+05:30")
            for i in range(8)
        ]
        allocations = allocate_fleet_nudges(
            candidate_records=candidates,
            total_plugged_count=200,
            sim_time_iso="2026-10-10T19:00:00+05:30",
            budget_pct=0.10,
        )
        selected_slots = [a.slot for a in allocations.values() if a.selected]
        assert len(selected_slots) == 8
        # Slots should be staggered rather than all identical
        unique_slots = set(selected_slots)
        assert len(unique_slots) > 1

    def test_allocator_prevents_rebound_feeder_peak(self):
        """Candidate load cannot exceed feeder transformer capacity threshold."""
        slot = find_safe_staggered_slot(
            preferred_start_iso="2026-10-10T23:00:00+05:30",
            power_kw=500.0,
            duration_hours=2.0,
            slot_allocations_kw={"2026-10-10T23:00:00+05:30": 6000.0},
            feeder_capacity_mw=12.0,
            base_load_mw=6.0,  # 6.0 MW base + 6.0 MW alloc = 12.0 MW (AT CAPACITY!)
            rebound_peak_threshold=0.98,
        )
        # Should push forward to offset 1 (23:15) where capacity is available
        assert slot is not None
        assert slot != "2026-10-10T23:00:00+05:30"
        assert "23:15" in slot

    def test_priority_score_calculation(self):
        """Priority score is 0.0 for none frame, non-negative otherwise."""
        plan = Plan(
            plan_id="p1",
            type="delay",
            start="2026-10-10T23:00:00+05:30",
            kw=7.4,
            where="home",
            outcomes={"grid_value": 1.5},
        )
        p_active = Persuasion(
            chosen_plan="p1",
            frame="cost",
            timing="at_plug_in",
            uplift_mean=0.3,
            uplift_p10=0.2,
            propensity=0.5,
            explored=False,
        )
        p_none = Persuasion(
            chosen_plan=None,
            frame="none",
            timing=None,
            uplift_mean=0.0,
            uplift_p10=0.0,
            propensity=1.0,
            explored=False,
        )
        assert compute_allocation_priority(p_active, plan) > 0.0
        assert compute_allocation_priority(p_none, None) == 0.0
